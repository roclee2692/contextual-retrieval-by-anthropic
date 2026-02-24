"""
防洪预案知识图谱 Schema v2
设计原则（来自导师建议）：
  - 流程显式建模为节点，保证子图不稀疏
  - 节点分5类：事件、主体、动作、阈值/时限、物资/设施
  - 关系5类闭环：触发、执行、负责、时限、依据
  - 抽取策略：规则高召回 + LLM仅做槽位补全（不做自由三元组生成）
"""
import re
import json
from typing import List, Dict, Any, Optional, Tuple


# ============================================================
# 节点类型定义（5大类，保证每个"险情/响应"天然连成一圈）
# ============================================================

NODE_TYPES: Dict[str, Dict] = {

    # ── 1. 事件/响应级别 ──────────────────────────────────────
    "ResponseEvent": {
        "label": "响应事件",
        "description": "防洪预案启动的响应级别或险情事件",
        "examples": ["IV级响应", "III级响应", "洪水预警", "水库漫坝险情"],
        "key_properties": ["level", "trigger_condition", "effective_time"],
    },

    # ── 2. 主体（部门/岗位） ──────────────────────────────────
    "Organization": {
        "label": "组织机构",
        "description": "负责执行响应任务的部门、单位或岗位",
        "examples": ["防汛指挥部", "水利局", "乡镇政府", "应急管理局"],
        "key_properties": ["name", "level", "contact"],
    },
    "Role": {
        "label": "职责角色",
        "description": "具体职责岗位，如指挥员、联络员",
        "examples": ["防汛指挥长", "技术负责人", "现场联络员"],
        "key_properties": ["name", "affiliated_org"],
    },

    # ── 3. 动作 ──────────────────────────────────────────────
    "Action": {
        "label": "响应动作",
        "description": "防洪响应中需执行的具体操作",
        "examples": ["上报", "巡查", "开闸泄洪", "人员转移", "启动响应"],
        "key_properties": ["action_type", "target", "deadline_hours"],
    },

    # ── 4. 阈值/时限/水位（数值约束） ────────────────────────
    "Threshold": {
        "label": "阈值约束",
        "description": "触发响应的数值条件（水位、流量、雨量、时限）",
        "examples": ["警戒水位113.5米", "2小时内", "降雨量50mm/h"],
        "key_properties": ["value", "unit", "threshold_type", "comparison"],
        # threshold_type: water_level / rainfall / flow / time_limit / stock
        # comparison: gte(≥) / lte(≤) / gt(>) / lt(<) / eq(=)
    },

    # ── 5. 设施/物资 ─────────────────────────────────────────
    "Facility": {
        "label": "水利设施",
        "description": "水库、堤防、闸门、水文站等物理设施",
        "examples": ["某水库", "某闸门", "某堤防段", "某水文站"],
        "key_properties": ["name", "location", "capacity", "alert_level"],
    },
    "Material": {
        "label": "物资",
        "description": "防洪应急所需的物资装备",
        "examples": ["沙袋", "救生艇", "应急发电机", "编织袋"],
        "key_properties": ["name", "quantity", "unit", "storage_location"],
    },
}


# ============================================================
# 关系类型定义（5类闭环，每个"响应事件"节点天然能连出一圈）
# ============================================================

RELATION_TYPES: Dict[str, Dict] = {

    # triggered_by: 什么条件触发了什么响应
    "triggered_by": {
        "label": "触发",
        "domain": ["ResponseEvent", "Action"],
        "range": ["Threshold", "ResponseEvent"],
        "examples": [
            ("IV级响应", "triggered_by", "水位达113.5米"),
            ("开闸泄洪", "triggered_by", "III级响应"),
        ],
    },

    # execute: 谁执行了什么动作
    "execute": {
        "label": "执行",
        "domain": ["Organization", "Role"],
        "range": ["Action"],
        "examples": [
            ("防汛指挥部", "execute", "发布预警"),
            ("乡镇政府", "execute", "人员转移"),
        ],
    },

    # responsible: 谁负责什么事件/设施
    "responsible": {
        "label": "负责",
        "domain": ["Organization", "Role"],
        "range": ["ResponseEvent", "Facility", "Action"],
        "examples": [
            ("水利局", "responsible", "某水库"),
            ("防汛指挥部", "responsible", "IV级响应"),
        ],
    },

    # deadline: 动作/响应的时限约束
    "deadline": {
        "label": "时限",
        "domain": ["Action", "ResponseEvent"],
        "range": ["Threshold"],
        "examples": [
            ("上报", "deadline", "2小时内"),
            ("人员转移", "deadline", "6小时内"),
        ],
    },

    # reference: 依据什么文件/规程/标准
    "reference": {
        "label": "依据",
        "domain": ["ResponseEvent", "Action", "Organization"],
        "range": ["Facility", "Material", "ResponseEvent"],
        "examples": [
            ("IV级响应", "reference", "某防洪预案"),
            ("开闸泄洪", "reference", "调度规程"),
        ],
    },

    # ── 保留的基础属性关系（用于设施数值属性）────────────────
    "has_threshold": {
        "label": "水位/库容属性",
        "domain": ["Facility"],
        "range": ["Threshold"],
        "examples": [
            ("某水库", "has_threshold", "汛限水位113.0米"),
        ],
    },
    "located_at": {
        "label": "位于",
        "domain": ["Facility", "Organization"],
        "range": ["Organization"],  # 行政区也归为Organization
        "examples": [("某水库", "located_at", "某县")],
    },
}


# ============================================================
# 规则抽取模式（高召回，先规则，后LLM校验槽位）
# ============================================================

# 数值+单位模式（覆盖水位/库容/雨量/时限）
RULE_NUMERIC = re.compile(
    r'(\d+(?:\.\d+)?)\s*'
    r'(小时|h|分钟|min|天|日|'
    r'米|m(?!\w)|mm|毫米|cm|厘米|'
    r'%|万m³|亿m³|m³|万方|亿方|'
    r'mm/h|mm/d|mm/24h|'
    r'方|吨|人|户|公里|km|万元|亿元)',
    re.IGNORECASE
)

# 触发词模式
RULE_TRIGGER = re.compile(
    r'(达到|超过|低于|不足|不低于|不少于|超出|'
    r'应当|必须|应该|需要|应立即|'
    r'启动|发布|报告|上报|负责|'
    r'当.{1,30}时|一旦|如果|若)',
    re.IGNORECASE
)

# 时限模式（精确匹配）
RULE_DEADLINE = re.compile(
    r'(\d+)\s*小时(?:内|以内|之内)?'
    r'|(\d+)\s*分钟(?:内|以内)?'
    r'|(\d+)\s*天(?:内|以内)?'
    r'|(\d+)\s*h(?:内|以内)?',
    re.IGNORECASE
)

# 响应级别模式（必须包含"级"才算，避免误匹配单个字母）
RULE_RESPONSE_LEVEL = re.compile(
    r'(?:I{1,3}V?|IV|[一二三四1-4])\s*级\s*(?:响应|预案|预警)'
    r'|[ⅠⅡⅢⅣ]\s*级\s*(?:响应|预案|预警)?'
    r'|(?:蓝色|黄色|橙色|红色)\s*(?:预警|响应)',
    re.IGNORECASE
)


# ============================================================
# 主 Schema 类
# ============================================================

class FloodSchema:
    """
    防洪预案知识图谱模式 v2
    闭环设计：每个"险情/响应级别"节点能天然连出完整子图
    """

    NODE_TYPES = NODE_TYPES
    RELATION_TYPES = RELATION_TYPES

    # 向后兼容旧代码
    ENTITIES = {k: v["label"] for k, v in NODE_TYPES.items()}
    RELATIONS = list(RELATION_TYPES.keys())

    @classmethod
    def get_oneke_instruction(cls) -> str:
        """OneKE 抽取指令（保持简洁，效果最好）"""
        return "抽取实体关系：\n"

    @classmethod
    def get_slot_fill_prompt(cls, text: str, slot_type: str) -> str:
        """
        LLM 槽位补全 Prompt（只让LLM填空，不让它自由生成三元组）
        slot_type: "subject" | "object" | "classify"
        """
        if slot_type == "classify":
            return (
                f"请判断下面这句话中的抽取记录属于哪类关系。\n"
                f"候选关系：{list(RELATION_TYPES.keys())}\n"
                f"文本：{text}\n"
                f"只回答关系名称，不要解释。\n"
                f"答："
            )
        elif slot_type == "subject":
            return (
                f"下面这句话缺少动作的执行主体（部门或职责角色）。\n"
                f"文本：{text}\n"
                f"只回答主体名称，不要解释。如果无法判断，回答'未知'。\n"
                f"答："
            )
        else:
            return (
                f"下面这句话缺少动作的对象。\n"
                f"文本：{text}\n"
                f"只回答对象名称，不要解释。如果无法判断，回答'未知'。\n"
                f"答："
            )

    @classmethod
    def get_prompt_template(cls) -> str:
        """LlamaIndex KnowledgeGraphIndex 用的抽取 Prompt"""
        node_labels = "、".join(v["label"] for v in NODE_TYPES.values())
        rel_labels = "、".join(
            f'{v["label"]}({k})' for k, v in RELATION_TYPES.items()
        )
        return (
            "你是防洪预案知识图谱抽取专家。\n\n"
            f"【节点类型】：{node_labels}\n\n"
            f"【关系类型】：{rel_labels}\n\n"
            "抽取规则：\n"
            "1. 优先抽取含数值/时限/触发条件的三元组（这是核心证据）\n"
            "2. 关系必须使用上述定义的英文关系名（如 triggered_by、execute）\n"
            "3. 数值尾实体必须带单位（如 '113.5米'，不要只写 '113.5'）\n"
            "4. 每行输出一个三元组，格式：(头实体, 关系名, 尾实体)\n"
            "5. 不要输出无法归类的关系，宁可少抽不要乱抽\n\n"
            "文本：\n{text}\n\n"
            "三元组：\n"
        )

    @classmethod
    def parse_oneke_response(cls, text: str) -> List[Tuple[str, str, str]]:
        """
        解析 LLM 输出，支持多种格式
        优先级：有谓词的 JSON > 无谓词的 JSON > (s,p,o) 文本格式
        """
        triplets = []
        text = text.strip()
        if not text:
            return triplets

        # ── 格式1: {"subject": "X", "predicate": "Y", "object": "Z"} ──
        p1 = re.findall(
            r'\{\s*"subject"\s*:\s*"([^"]+)"\s*,\s*"predicate"\s*:\s*"([^"]+)"\s*,\s*"object"\s*:\s*"([^"]+)"\s*\}',
            text
        )
        for s, p, o in p1:
            triplets.append((s.strip(), p.strip(), o.strip()))

        # ── 格式2: {"subject": "X", "object": "Z"} (无谓词，标记为unknown) ──
        if not triplets:
            p2 = re.findall(
                r'\{\s*"subject"\s*:\s*"([^"]+)"\s*,\s*"object"\s*:\s*"([^"]+)"\s*\}',
                text
            )
            for s, o in p2:
                triplets.append((s.strip(), "related_to", o.strip()))

        # ── 格式3: (头实体, 关系, 尾实体) 文本格式 ──
        if not triplets:
            p3 = re.findall(r'\(([^,()]+),\s*([^,()]+),\s*([^,()]+)\)', text)
            for s, p, o in p3:
                triplets.append((s.strip(), p.strip(), o.strip()))

        # ── 格式4: 中文键名 ──
        if not triplets:
            p4 = re.findall(
                r'\{\s*"主体"\s*:\s*"([^"]+)"\s*,\s*"关系"\s*:\s*"([^"]+)"\s*,\s*"客体"\s*:\s*"([^"]+)"\s*\}',
                text
            )
            for s, r, o in p4:
                triplets.append((s.strip(), r.strip(), o.strip()))

        return list(set(triplets))

    @classmethod
    def extract_rule_based(cls, text: str) -> Dict[str, Any]:
        """
        规则抽取：高召回抽取数值/时限/触发词
        输出结构化槽位，供 LLM 校验/补全用
        """
        results: Dict[str, Any] = {
            "numeric_slots": [],
            "deadline_slots": [],
            "trigger_keywords": [],
            "response_levels": [],
        }

        # 数值槽位
        for m in RULE_NUMERIC.finditer(text):
            ctx_s = max(0, m.start() - 25)
            ctx_e = min(len(text), m.end() + 25)
            results["numeric_slots"].append({
                "value": m.group(1),
                "unit": m.group(2),
                "raw": m.group(0),
                "context": text[ctx_s:ctx_e],
            })

        # 时限槽位（换算成小时）
        for m in RULE_DEADLINE.finditer(text):
            raw = m.group(0)
            if m.group(1):
                hours = float(m.group(1))
            elif m.group(2):
                hours = round(float(m.group(2)) / 60, 2)
            elif m.group(3):
                hours = float(m.group(3)) * 24
            else:
                hours = float(m.group(4))
            results["deadline_slots"].append({"hours": hours, "raw": raw})

        # 触发词
        results["trigger_keywords"] = list({
            m.group(0) for m in RULE_TRIGGER.finditer(text)
        })

        # 响应级别
        results["response_levels"] = list({
            m.group(0).strip() for m in RULE_RESPONSE_LEVEL.finditer(text)
        })

        return results

    @classmethod
    def get_node_type(cls, entity: str) -> Optional[str]:
        """
        简单启发式：根据实体名猜测节点类型
        """
        e = entity.strip()
        if re.search(r'(?:[IiⅠⅡⅢⅣ一二三四1-4]\s*级\s*)?(?:响应|预警)', e):
            return "ResponseEvent"
        if re.search(r'水库|闸|堤|站|河|坝', e):
            return "Facility"
        if re.search(r'指挥部|水利局|政府|应急|办公室|乡|镇|村', e):
            return "Organization"
        if re.search(r'上报|巡查|转移|开闸|关闸|发布|通知|撤离|检查', e):
            return "Action"
        if re.search(r'\d+\s*(米|m|mm|小时|h|万|%)', e):
            return "Threshold"
        if re.search(r'沙袋|救生|发电|编织袋|物资|装备', e):
            return "Material"
        return None

    @classmethod
    def validate_triplet(
        cls, subj: str, pred: str, obj: str
    ) -> Tuple[bool, str]:
        """
        校验三元组是否符合 Schema 约束
        返回 (是否有效, 错误原因)
        """
        if pred not in RELATION_TYPES:
            return False, f"未知关系类型: {pred}"

        rel_def = RELATION_TYPES[pred]
        subj_type = cls.get_node_type(subj)
        obj_type = cls.get_node_type(obj)

        if subj_type and subj_type not in rel_def["domain"]:
            return False, (
                f"主语类型 {subj_type} 不符合 {pred} 的 domain "
                f"{rel_def['domain']}"
            )
        if obj_type and obj_type not in rel_def["range"]:
            return False, (
                f"宾语类型 {obj_type} 不符合 {pred} 的 range "
                f"{rel_def['range']}"
            )
        return True, ""
