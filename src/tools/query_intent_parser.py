"""
Query 意图对齐层 (Query Intent Alignment Layer)
================================================
目标：把模糊的自然语言问题 → 结构化槽位 + 扩写查询
策略：规则优先（高精度） + 词表归一（来自 entity_fusion）+ LLM 仅做槽位补全

意图分类对应测试集三类：
  A-数值属性  — 提问具体数值（水位/库容/高程/流量/面积/坝长…）
  B-实体关系  — 提问"谁/哪个/哪条/哪年"（人、单位、地点、时间）
  C-流程条件  — 提问"如何/步骤/程序/情况/措施/条件"
"""

import re
import sys
import os
from typing import Optional, Dict, List, Tuple, Any

# ── 导入实体融合词表 ──────────────────────────────────────────
# 把 src/ 加入 sys.path 以便跨目录 import
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from src.contextual_retrieval.entity_fusion import (
    DEPARTMENT_ALIASES,
    RESPONSE_LEVEL_ALIASES,
    ACTION_ALIASES,
    normalize_entity,
)

# ============================================================
# 1. 关键词词表（槽位特征词）
# ============================================================

# A 类 — 数值属性关键词（查询目标是什么数值）
NUMERIC_ATTRIBUTE_KEYWORDS: Dict[str, str] = {
    # 水位
    "汛限水位": "water_level",
    "汛限": "water_level",
    "警戒水位": "water_level",
    "保证水位": "water_level",
    "校核洪水位": "water_level",
    "设计洪水位": "water_level",
    "死水位": "water_level",
    "正常蓄水位": "water_level",
    "水位": "water_level",
    # 库容
    "总库容": "capacity",
    "调洪库容": "capacity",
    "兴利库容": "capacity",
    "死库容": "capacity",
    "库容": "capacity",
    # 高程/尺寸
    "坝顶高程": "elevation",
    "坝高": "elevation",
    "高程": "elevation",
    "坝长": "dimension",
    "坝顶宽度": "dimension",
    "溢洪道宽": "dimension",
    # 流量
    "设计流量": "flow_rate",
    "泄洪流量": "flow_rate",
    "流量": "flow_rate",
    # 面积
    "流域面积": "area",
    "集水面积": "area",
    "面积": "area",
    # 雨量
    "日降雨量": "rainfall",
    "降雨量": "rainfall",
    # 坝
    "坝型": "dam_type",
}

# B 类 — 关系查询触发词
RELATION_TRIGGER_WORDS: List[str] = [
    "谁", "是谁", "负责人是谁", "谁负责",
    "哪个单位", "哪个部门", "哪条河", "哪条",
    "哪些区域", "哪些",
    "位于哪", "属于哪", "归哪",
    "建于哪", "建于哪一年", "几年", "哪一年",
    "隶属", "主管部门",
    "下游", "上游",
]

# C 类 — 流程/条件查询触发词
PROCESS_TRIGGER_WORDS: List[str] = [
    "什么情况下", "如何", "怎么", "怎样",
    "步骤", "程序", "流程", "措施", "要求",
    "包括哪些", "由哪些",
    "条件", "什么时候",
    "需要启动", "需要开始", "应该如何", "应如何",
    "处理", "应对",
    "达到多少时", "达到什么", "达到.*时",  # 触发条件句式
    "时需要", "时应",                        # "达到...时需要"模式
]

# C 类特判正则：触发条件句式（"达到X时需要…"）
C_TRIGGER_PATTERN = re.compile(r"达到.{0,10}时[需应要]")

# A 类 — 数值属性查询的后缀模式
A_QUERY_SUFFIX = re.compile(r"(多少|几|是多少|是几)[？?]?$")

# 水利设施名模式（从测试题归纳，可扩展）
FACILITY_PATTERNS = [
    re.compile(r"[\u4e00-\u9fa5]+水库"),   # XX水库
    re.compile(r"[\u4e00-\u9fa5]+水闸"),   # XX水闸
    re.compile(r"[\u4e00-\u9fa5]+泵站"),   # XX泵站
    re.compile(r"[\u4e00-\u9fa5]+堤"),     # XX堤
    re.compile(r"[\u4e00-\u9fa5]+坝"),     # XX坝
    re.compile(r"[\u4e00-\u9fa5]+闸"),     # XX闸
]

# 响应级别模式（兼容罗马数字 + 汉字 + 阿拉伯数字，需含"级"）
# 注意：应急响应 必须排在 响应 之前（长匹配优先）
RESPONSE_LEVEL_PATTERN = re.compile(
    r"(I{1,3}V?|IV|[一二三四1-4])[级](?:应急响应|响应)?"
    r"|(?:蓝色|黄色|橙色|红色)(?:预警|警报)"
)

# ============================================================
# 2. 意图解析主类
# ============================================================

class QueryIntentParser:
    """
    将自然语言查询解析为结构化意图 + 扩写查询串。

    使用方法::

        parser = QueryIntentParser()
        result = parser.parse("杨家横水库的汛限水位是多少？")
        # result["query_type"]  → "A"
        # result["facility"]    → "杨家横水库"
        # result["attribute"]   → "water_level"
        # result["rewritten"]   → ["杨家横水库汛限水位", "杨家横水库水位指标 汛限水位数值"]
    """

    # ── 2.1 入口 ──────────────────────────────────────────────

    def parse(self, query: str) -> Dict[str, Any]:
        """
        解析查询，返回结构化槽位字典。

        返回字段说明
        -----------
        query_type  : str           A / B / C
        response_level : str|None   归一化后的响应级别
        facility    : list[str]     提及的水利设施列表
        subject     : list[str]     提及的组织/部门（归一化）
        attribute   : str|None      A类目标属性 (water_level/capacity/…)
        action_type : str|None      C类目标动作
        keywords    : list[str]     规则提取的核心词（用于扩写）
        rewritten   : list[str]     扩写查询列表（原始 + 归一化 + 扩写）
        raw_query   : str           原始查询
        """
        slots: Dict[str, Any] = {
            "raw_query": query,
            "query_type": None,
            "response_level": None,
            "facility": [],
            "subject": [],
            "attribute": None,
            "action_type": None,
            "keywords": [],
            "rewritten": [],
        }

        # Step 1: 实体槽位提取
        self._extract_facility(query, slots)
        self._extract_subject(query, slots)
        self._extract_response_level(query, slots)
        self._extract_attribute(query, slots)
        self._extract_action(query, slots)

        # Step 2: 意图分类（规则投票）
        slots["query_type"] = self._classify_intent(query, slots)

        # Step 3: 关键词汇总
        slots["keywords"] = self._collect_keywords(query, slots)

        # Step 4: 查询扩写
        slots["rewritten"] = self._rewrite(query, slots)

        return slots

    # ── 2.2 槽位提取 ─────────────────────────────────────────

    def _extract_facility(self, query: str, slots: dict) -> None:
        """提取水利设施名"""
        found = []
        for pat in FACILITY_PATTERNS:
            for m in pat.finditer(query):
                name = m.group(0)
                if name not in found:
                    found.append(name)
        slots["facility"] = found

    def _extract_subject(self, query: str, slots: dict) -> None:
        """提取并归一化组织/部门"""
        found = []
        # 按别名词表最长匹配
        sorted_aliases = sorted(DEPARTMENT_ALIASES.keys(), key=len, reverse=True)
        remaining = query
        for alias in sorted_aliases:
            if alias in remaining:
                norm = DEPARTMENT_ALIASES[alias]
                if norm not in found:
                    found.append(norm)
                remaining = remaining.replace(alias, "")
        slots["subject"] = found

    def _extract_response_level(self, query: str, slots: dict) -> None:
        """提取响应级别并归一化"""
        m = RESPONSE_LEVEL_PATTERN.search(query)
        if m:
            raw = m.group(0)
            # 尝试词表精确匹配
            norm = RESPONSE_LEVEL_ALIASES.get(raw)
            if not norm:
                # 尝试模糊归一
                norm = normalize_entity(raw)
            slots["response_level"] = norm or raw

    def _extract_attribute(self, query: str, slots: dict) -> None:
        """提取查询目标属性（A类）"""
        # 从长到短匹配，优先精确匹配
        for kw in sorted(NUMERIC_ATTRIBUTE_KEYWORDS.keys(), key=len, reverse=True):
            if kw in query:
                slots["attribute"] = NUMERIC_ATTRIBUTE_KEYWORDS[kw]
                slots["keywords"].append(kw)
                break

    def _extract_action(self, query: str, slots: dict) -> None:
        """提取流程动作类型（C类）"""
        sorted_verbs = sorted(ACTION_ALIASES.keys(), key=len, reverse=True)
        for verb in sorted_verbs:
            if verb in query:
                norm = ACTION_ALIASES[verb]
                slots["action_type"] = norm
                break

    # ── 2.3 意图分类（规则投票） ─────────────────────────────

    def _classify_intent(self, query: str, slots: dict) -> str:
        """
        基于规则投票决定意图类型：
          score_A, score_B, score_C 各自累加，取最高分
        """
        score_a, score_b, score_c = 0, 0, 0

        # A 类信号
        if A_QUERY_SUFFIX.search(query):
            score_a += 3
        if slots["attribute"]:
            score_a += 2

        # B 类信号
        for w in RELATION_TRIGGER_WORDS:
            if w in query:
                score_b += 2
                break

        # C 类信号
        for w in PROCESS_TRIGGER_WORDS:
            if w in query:
                score_c += 2
                break
        if C_TRIGGER_PATTERN.search(query):   # "达到X时需要…" 强触发条件
            score_c += 3
        if slots["response_level"]:
            score_c += 1   # 响应级别往往跟流程相关
        if slots["action_type"]:
            score_c += 1

        # 特殊规则：包括"哪些…组成/包括" → C
        if re.search(r"由哪些|包括哪些|组成|成员", query):
            score_c += 1

        # 决策
        scores = {"A": score_a, "B": score_b, "C": score_c}
        best = max(scores, key=lambda k: scores[k])
        # 同分时优先级 C > B > A（流程题最难判，优先保留）
        if scores["C"] == scores["B"] == scores["A"]:
            return "C"
        return best

    # ── 2.4 关键词汇总 ────────────────────────────────────────

    def _collect_keywords(self, query: str, slots: dict) -> List[str]:
        """汇总所有已提取的核心词，去重"""
        keywords = list(slots.get("keywords", []))  # 已有的（如 attribute 对应的词）

        # 加入设施名
        keywords.extend(slots["facility"])

        # 加入归一化主体（原始 + 归一化都加）
        keywords.extend(slots["subject"])

        # 加入响应级别
        if slots["response_level"]:
            keywords.append(slots["response_level"])

        # 加入动作
        if slots["action_type"]:
            keywords.append(slots["action_type"])

        # 去重保序
        seen, result = set(), []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)
        return result

    # ── 2.5 查询扩写 ─────────────────────────────────────────

    def _rewrite(self, query: str, slots: dict) -> List[str]:
        """
        生成 3 路扩写查询：
          [0] 原始查询（原样保留）
          [1] 归一化查询（用标准名替换别名）
          [2] 扩写查询（补充上下文语境词）
        """
        variants = [query]

        # 归一化查询 —— 把所有别名替换为标准名
        norm_q = query
        # 响应级别归一化
        if slots["response_level"]:
            m = RESPONSE_LEVEL_PATTERN.search(norm_q)
            if m:
                norm_q = norm_q[:m.start()] + slots["response_level"] + norm_q[m.end():]
        # 主体归一化（把已知别名替换为标准名）
        for alias, std in DEPARTMENT_ALIASES.items():
            if alias in norm_q and alias != std:
                norm_q = norm_q.replace(alias, std)
        if norm_q != query:
            variants.append(norm_q)

        # 扩写查询 —— 补充语境关键词
        expanded = self._build_expanded_query(norm_q, slots)
        if expanded and expanded not in variants:
            variants.append(expanded)

        return variants

    def _build_expanded_query(self, norm_q: str, slots: dict) -> Optional[str]:
        """根据意图类型构造扩写句子"""
        qt = slots["query_type"]
        facility = " ".join(slots["facility"]) if slots["facility"] else ""
        subject = " ".join(slots["subject"]) if slots["subject"] else ""
        level = slots["response_level"] or ""
        attr = slots["attribute"] or ""
        action = slots["action_type"] or ""

        if qt == "A":
            # 扩写：设施名 + 属性词 + 数值/技术指标
            attr_cn = _ATTR_CN.get(attr, "")
            parts = [p for p in [facility, attr_cn, "技术指标 数值 防洪预案"] if p]
            return " ".join(parts) if parts else None

        elif qt == "B":
            # 扩写：明确化关系方向
            if "谁" in norm_q or "负责人" in norm_q:
                parts = [p for p in [facility or subject, "负责人 职责 分工"] if p]
            elif "哪" in norm_q:
                parts = [p for p in [facility or subject, "单位 部门 管理 隶属"] if p]
            else:
                parts = [p for p in [facility, subject, "关系 隶属 管辖"] if p]
            return " ".join(parts) if parts else None

        elif qt == "C":
            # 扩写：场景词 + 响应级别 + 流程/步骤
            parts = [p for p in [level, subject, action, "响应程序 处置步骤 应急措施"] if p]
            return " ".join(parts) if parts else None

        return None

    # ── 2.6 批量解析 ─────────────────────────────────────────

    def parse_batch(self, queries: List[str]) -> List[Dict[str, Any]]:
        """批量解析，返回同等长度的槽位列表"""
        return [self.parse(q) for q in queries]


# ── 中文属性名映射（用于扩写） ─────────────────────────────────
_ATTR_CN: Dict[str, str] = {
    "water_level": "水位",
    "capacity": "库容",
    "elevation": "高程",
    "dimension": "坝长 坝宽",
    "flow_rate": "流量",
    "area": "面积",
    "rainfall": "降雨量",
    "dam_type": "坝型",
}


# ============================================================
# 3. LLM 辅助槽位补全（当规则无法确定 subject/action 时调用）
# ============================================================

def build_slot_fill_prompt(query: str, missing_slots: List[str]) -> str:
    """
    生成给 LLM 的槽位补全 Prompt。
    只让 LLM 填充规则无法确定的槽位，不让其自由生成。

    Parameters
    ----------
    query : str
        原始用户查询
    missing_slots : list[str]
        需要 LLM 补全的槽位名列表，如 ['subject', 'action_type']

    Returns
    -------
    str
        格式化好的 Prompt 字符串
    """
    slot_desc = {
        "subject": "主体组织或部门名称（如：水利局、防汛指挥部、乡镇政府）",
        "action_type": "动作类型（如：上报、巡查、泄洪、转移、储备）",
        "facility": "水利设施名称（如：杨家横水库、常庄水库）",
        "attribute": "查询的数值属性（如：汛限水位、总库容、坝顶高程）",
    }
    needed = {k: slot_desc[k] for k in missing_slots if k in slot_desc}
    if not needed:
        return ""

    slot_lines = "\n".join(
        f"  - {k}：{v}" for k, v in needed.items()
    )
    prompt = f"""你是防洪预案信息抽取助手。请从以下查询中提取指定槽位的值。
若查询中未提及某槽位，请填 null。

查询："{query}"

需要提取的槽位：
{slot_lines}

请以 JSON 格式回复，只输出 JSON，不要解释：
{{
{chr(10).join(f'  "{k}": null' for k in needed)}
}}"""
    return prompt


# ============================================================
# 4. 与现有检索链路集成的辅助函数
# ============================================================

def enrich_query_for_retrieval(query: str, parser: Optional["QueryIntentParser"] = None) -> List[str]:
    """
    对单条查询做意图解析 + 扩写，返回用于检索的查询列表。
    可以直接替换检索器的 query 参数（传入 list 取并集）。

    Parameters
    ----------
    query : str
        原始用户查询
    parser : QueryIntentParser, optional
        可复用已创建的 parser 实例；None 则新建

    Returns
    -------
    list[str]
        去重的扩写查询列表（第一个始终是原始查询）
    """
    if parser is None:
        parser = QueryIntentParser()
    result = parser.parse(query)
    return result["rewritten"]


def format_intent_summary(intent: Dict[str, Any]) -> str:
    """
    格式化意图解析结果为可读字符串（调试用）。
    """
    lines = [
        f"[意图类型]  {intent['query_type']}",
        f"[原始查询]  {intent['raw_query']}",
    ]
    if intent["facility"]:
        lines.append(f"[设施]      {', '.join(intent['facility'])}")
    if intent["subject"]:
        lines.append(f"[主体]      {', '.join(intent['subject'])}")
    if intent["response_level"]:
        lines.append(f"[响应级别]  {intent['response_level']}")
    if intent["attribute"]:
        lines.append(f"[属性]      {intent['attribute']} ({_ATTR_CN.get(intent['attribute'], '')})")
    if intent["action_type"]:
        lines.append(f"[动作]      {intent['action_type']}")
    if intent["keywords"]:
        lines.append(f"[关键词]    {', '.join(intent['keywords'])}")
    lines.append(f"[扩写查询]")
    for i, rw in enumerate(intent["rewritten"], 1):
        lines.append(f"  [{i}] {rw}")
    return "\n".join(lines)


# ============================================================
# 5. 快速测试
# ============================================================

if __name__ == "__main__":
    import json

    parser = QueryIntentParser()

    test_queries = [
        # A 类
        "杨家横水库的汛限水位是多少？",
        "常庄水库的总库容是多少？",
        "杨家横水库大坝的坝顶高程是多少？",
        "杨家横水库溢洪道的设计流量是多少？",
        # B 类
        "杨家横水库的大坝安全责任人是谁？",
        "常庄水库防汛指挥部的指挥长是谁？",
        "杨家横水库由哪个单位管理？",
        "防汛物资由哪个部门负责储备？",
        # C 类
        "什么情况下需要启动III级应急响应？",
        "水库水位达到多少时需要开始泄洪？",
        "堤防巡查的具体步骤是什么？",
        "发现险情后应该如何报告？",
        "防汛值班制度的具体要求是什么？",
    ]

    print("=" * 65)
    print("QueryIntentParser 测试结果")
    print("=" * 65)

    type_counter = {"A": 0, "B": 0, "C": 0}
    for q in test_queries:
        intent = parser.parse(q)
        type_counter[intent["query_type"]] += 1
        print()
        print(format_intent_summary(intent))
        print("-" * 55)

    print()
    print(f"分类统计: A={type_counter['A']} B={type_counter['B']} C={type_counter['C']}")
    print("测试完成。")
