"""
实体融合模块 - 词表+规则归一化
目标：让知识图谱中相同语义的实体指向同一个ID，消除子图断连

适用场景：
  - 部门别名归一（防指 / 防汛指挥部 / 区防汛指挥部办公室 → 防汛指挥部）
  - 响应级别归一（Ⅳ级 / 四级 / 4级 / IV级响应 → IV级响应）
  - 水库/闸/站命名归一（全角半角、简称、带"水库"后缀）
  - 动作/触发词归一（上报 / 报告 / 报送 → 上报）
"""

import re
from typing import List, Tuple, Dict, Optional


# ============================================================
# 1. 归一化词表
# ============================================================

# 部门/机构别名归一
# 格式: {别名: 标准名}
DEPARTMENT_ALIASES: Dict[str, str] = {
    # 防汛指挥部
    "防指": "防汛指挥部",
    "区防指": "防汛指挥部",
    "市防指": "防汛指挥部",
    "县防指": "防汛指挥部",
    "省防指": "防汛指挥部",
    "防汛抗旱指挥部": "防汛指挥部",
    "区防汛指挥部": "防汛指挥部",
    "市防汛指挥部": "防汛指挥部",
    "防汛指挥部办公室": "防汛指挥部",
    "区防汛指挥部办公室": "防汛指挥部",
    "防汛办": "防汛指挥部",
    "防办": "防汛指挥部",

    # 水利局/水务局
    "水利局": "水利局",
    "水务局": "水利局",
    "区水利局": "水利局",
    "市水利局": "水利局",

    # 政府
    "区政府": "地方政府",
    "市政府": "地方政府",
    "县政府": "地方政府",
    "镇政府": "地方政府",
    "乡政府": "地方政府",

    # 应急管理
    "应急局": "应急管理局",
    "应急管理局": "应急管理局",
    "区应急局": "应急管理局",
    "市应急局": "应急管理局",
}

# 响应级别归一
RESPONSE_LEVEL_ALIASES: Dict[str, str] = {
    # IV级（最低）
    "Ⅳ级": "IV级响应",
    "四级": "IV级响应",
    "4级": "IV级响应",
    "iv级": "IV级响应",
    "IV级": "IV级响应",
    "Ⅳ级响应": "IV级响应",
    "四级响应": "IV级响应",
    "4级响应": "IV级响应",
    "IV级应急响应": "IV级响应",
    "四级应急响应": "IV级响应",
    "蓝色预警": "IV级响应",

    # III级
    "Ⅲ级": "III级响应",
    "三级": "III级响应",
    "3级": "III级响应",
    "iii级": "III级响应",
    "III级": "III级响应",
    "Ⅲ级响应": "III级响应",
    "三级响应": "III级响应",
    "3级响应": "III级响应",
    "III级应急响应": "III级响应",
    "三级应急响应": "III级响应",
    "黄色预警": "III级响应",

    # II级
    "Ⅱ级": "II级响应",
    "二级": "II级响应",
    "2级": "II级响应",
    "ii级": "II级响应",
    "II级": "II级响应",
    "Ⅱ级响应": "II级响应",
    "二级响应": "II级响应",
    "2级响应": "II级响应",
    "II级应急响应": "II级响应",
    "二级应急响应": "II级响应",
    "橙色预警": "II级响应",

    # I级（最高）
    "Ⅰ级": "I级响应",
    "一级": "I级响应",
    "1级": "I级响应",
    "i级": "I级响应",
    "I级": "I级响应",
    "Ⅰ级响应": "I级响应",
    "一级响应": "I级响应",
    "1级响应": "I级响应",
    "I级应急响应": "I级响应",
    "一级应急响应": "I级响应",
    "红色预警": "I级响应",
}

# 动作/触发词归一
ACTION_ALIASES: Dict[str, str] = {
    # 上报
    "报告": "上报",
    "报送": "上报",
    "上报": "上报",
    "汇报": "上报",
    "呈报": "上报",

    # 启动
    "启动": "启动响应",
    "开启": "启动响应",
    "激活": "启动响应",
    "启动响应": "启动响应",
    "进入应急状态": "启动响应",

    # 巡查
    "巡查": "巡查",
    "巡逻": "巡查",
    "现场检查": "巡查",
    "检查": "巡查",

    # 转移
    "转移": "人员转移",
    "撤离": "人员转移",
    "疏散": "人员转移",
    "人员转移": "人员转移",
    "紧急转移": "人员转移",
}

# 合并所有词表
ALL_ALIASES: Dict[str, str] = {
    **DEPARTMENT_ALIASES,
    **RESPONSE_LEVEL_ALIASES,
    **ACTION_ALIASES,
}


# ============================================================
# 2. 正则模式：抽取数值/单位/时限
# ============================================================

# 匹配数值+单位（水位、库容、时限等）
PATTERN_NUMERIC = re.compile(
    r'(\d+(\.\d+)?)\s*(小时|h|小时内|分钟|分钟内|天|日|'
    r'米|m|mm|毫米|cm|厘米|'
    r'%|万方|万m³|m³|亿m³|亿方|'
    r'方|吨|人|户|公里|km)'
)

# 匹配触发条件关键词
PATTERN_TRIGGER = re.compile(
    r'(达到|超过|低于|不足|应当|必须|'
    r'启动|报告|上报|负责|由.{1,10}发布|'
    r'当.{1,20}时|一旦|如果)'
)

# 匹配时限表达式（如"2小时内"、"24小时以内"）
PATTERN_DEADLINE = re.compile(
    r'(\d+)\s*小时(内|以内|之内)?|(\d+)\s*分钟(内|以内)?|(\d+)\s*天(内|以内)?'
)


# ============================================================
# 3. 核心归一化函数
# ============================================================

def normalize_entity(entity: str) -> str:
    """
    对单个实体字符串进行归一化：
    1. 全角转半角
    2. 去除多余空白
    3. 查词表映射
    """
    # 全角转半角
    entity = _full_to_half(entity.strip())
    # 去除路径/文件名污染（如 "洪预案\\常庄水库" 或 "/data/.../常庄水库.pdf"）
    entity = _strip_path_prefix(entity)
    entity = _strip_file_ext(entity)

    # 查词表（先精确匹配）
    if entity in ALL_ALIASES:
        return ALL_ALIASES[entity]

    # 模糊匹配：检查是否包含别名（处理"启动Ⅳ级响应"这类带前缀的）
    # 做两轮，处理替换后新出现的别名（如"区防指办公室"→"防汛指挥部办公室"→"防汛指挥部"）
    for _ in range(2):
        for alias, standard in sorted(ALL_ALIASES.items(), key=lambda x: -len(x[0])):
            if alias in entity and alias != entity:
                entity = entity.replace(alias, standard)
                break

    # 精确匹配再查一次（两轮模糊替换后可能命中新词条）
    if entity in ALL_ALIASES:
        entity = ALL_ALIASES[entity]

    # 修复替换后可能出现的重复后缀（如"IV级响应响应" -> "IV级响应"）
    entity = re.sub(r'(响应){2,}', '响应', entity)
    entity = re.sub(r'(转移){2,}', '转移', entity)

    return entity


def normalize_triplets(
    triplets: List[Tuple[str, str, str]]
) -> List[Tuple[str, str, str]]:
    """
    对三元组列表进行批量实体融合归一化
    输入: [(subject, predicate, object), ...]
    输出: 归一化后的三元组列表（去重）
    """
    normalized = []
    seen = set()

    for subj, pred, obj in triplets:
        # 只归一化实体，不处理谓词，避免把关系名误映射为实体
        n_subj = normalize_entity(subj)
        n_pred = pred
        n_obj = normalize_entity(obj)

        key = (n_subj, n_pred, n_obj)
        if key not in seen:
            seen.add(key)
            normalized.append(key)

    return normalized


def extract_numeric_slots(text: str) -> List[Dict]:
    """
    从文本中抽取结构化数值槽位
    返回: [{"value": "2", "unit": "小时", "context": "..."}]
    """
    slots = []
    for match in PATTERN_NUMERIC.finditer(text):
        start = max(0, match.start() - 20)
        end = min(len(text), match.end() + 20)
        slots.append({
            "value": match.group(1),
            "unit": match.group(3),
            "raw": match.group(0),
            "context": text[start:end]
        })
    return slots


def extract_deadline_slots(text: str) -> List[Dict]:
    """
    专门抽取时限表达式
    返回: [{"hours": 2, "raw": "2小时内"}]
    """
    slots = []
    for match in PATTERN_DEADLINE.finditer(text):
        raw = match.group(0)
        if match.group(1):
            slots.append({"hours": int(match.group(1)), "raw": raw})
        elif match.group(3):
            mins = int(match.group(3))
            slots.append({"hours": round(mins / 60, 2), "raw": raw})
        elif match.group(5):
            days = int(match.group(5))
            slots.append({"hours": days * 24, "raw": raw})
    return slots


def has_trigger_keyword(text: str) -> bool:
    """判断文本是否包含触发条件关键词"""
    return bool(PATTERN_TRIGGER.search(text))


# ============================================================
# 4. 工具函数
# ============================================================

def _full_to_half(text: str) -> str:
    """全角字符转半角（处理中文文档中的全角数字/字母）"""
    result = []
    for char in text:
        code = ord(char)
        # 全角空格
        if code == 0x3000:
            result.append(' ')
        # 全角字符范围
        elif 0xFF01 <= code <= 0xFF5E:
            result.append(chr(code - 0xFEE0))
        else:
            result.append(char)
    return ''.join(result)


def _strip_path_prefix(text: str) -> str:
    """去除路径前缀，仅保留最后的文件/节点名片段"""
    if "/" in text or "\\" in text:
        parts = re.split(r"[\\/]+", text)
        parts = [p for p in parts if p]
        if parts:
            return parts[-1]
    return text


def _strip_file_ext(text: str) -> str:
    """去除常见文件后缀"""
    return re.sub(r"\.(pdf|docx?|txt|md|html?)$", "", text, flags=re.IGNORECASE)


def get_fusion_stats(
    original: List[Tuple],
    fused: List[Tuple]
) -> Dict:
    """统计融合效果"""
    original_entities = set()
    fused_entities = set()

    for s, p, o in original:
        original_entities.add(s)
        original_entities.add(o)
    for s, p, o in fused:
        fused_entities.add(s)
        fused_entities.add(o)

    return {
        "original_triplets": len(original),
        "fused_triplets": len(fused),
        "dedup_removed": len(original) - len(fused),
        "original_entities": len(original_entities),
        "fused_entities": len(fused_entities),
        "entity_reduction": len(original_entities) - len(fused_entities),
    }


# ============================================================
# 5. 测试
# ============================================================

if __name__ == "__main__":
    # 测试用例
    test_triplets = [
        ("防指", "发布", "Ⅳ级响应"),
        ("防汛指挥部", "发布", "四级响应"),        # 同一语义，应融合
        ("区防指办公室", "通知", "水利局"),
        ("防汛抗旱指挥部", "发布", "IV级响应"),    # 同一语义
        ("市防指", "启动", "Ⅱ级"),
        ("应急局", "负责", "人员转移"),
        ("区应急局", "负责", "撤离"),              # 同一语义
        ("某水库", "汛限水位", "113.00米"),
        ("某水库", "汛限水位", "１１３．００米"),   # 全角，应归一
    ]

    print("原始三元组：")
    for t in test_triplets:
        print(f"  {t}")

    fused = normalize_triplets(test_triplets)
    stats = get_fusion_stats(test_triplets, fused)

    print(f"\n融合后三元组（去重后 {stats['fused_triplets']} 条）：")
    for t in fused:
        print(f"  {t}")

    print(f"\n融合效果统计：")
    print(f"  三元组: {stats['original_triplets']} → {stats['fused_triplets']} "
          f"(减少 {stats['dedup_removed']} 条)")
    print(f"  实体数: {stats['original_entities']} → {stats['fused_entities']} "
          f"(减少 {stats['entity_reduction']} 个)")

    print("\n数值槽位抽取测试：")
    test_text = "当水库水位达到113.5米时，应在2小时内向防指报告，并启动IV级响应。"
    slots = extract_numeric_slots(test_text)
    deadlines = extract_deadline_slots(test_text)
    print(f"  文本: {test_text}")
    print(f"  数值槽位: {slots}")
    print(f"  时限槽位: {deadlines}")
    print(f"  含触发词: {has_trigger_keyword(test_text)}")
