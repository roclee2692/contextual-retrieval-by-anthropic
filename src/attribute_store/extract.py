import re
from typing import Dict, Any, List, Optional, Tuple
from src.schema.flood_schema import RULE_RESPONSE_LEVEL

# 设施名称识别
FACILITY_PATTERN = re.compile(
    r'([\u4e00-\u9fa5]{2,10}(?:水库|水闸|堤防|堤坝|泵站|水文站|拦河坝))'
)

# 条款/表号简单识别
CLAUSE_PATTERN = re.compile(r'(\d+\.\d+(?:\.\d+)?)')
TABLE_PATTERN = re.compile(r'(表\s*\d+|表\s*[一二三四五六七八九十]+)')

# 条件关键词（可扩展）
CONDITION_KEYWORDS = [
    "汛期", "非汛期", "枯水期", "设计", "校核", "正常运行", "洪水期",
]

# 比较词 → comparator
COMPARATOR_MAP = [
    (re.compile(r"不低于|不少于|达到|超过|高于|大于"), ">="),
    (re.compile(r"不超过|低于|小于|以下"), "<="),
]

# 字段正则模板（至少 10 条）
FIELD_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("汛限水位", re.compile(r"汛限水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("正常蓄水位", re.compile(r"正常蓄水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("死水位", re.compile(r"死水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("校核洪水位", re.compile(r"校核洪水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("设计洪水位", re.compile(r"设计洪水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("警戒水位", re.compile(r"警戒水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("保证水位", re.compile(r"保证水位[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("总库容", re.compile(r"总库容[:：]?\s*(\d+(?:\.\d+)?)\s*(万m³|亿m³|万方|m³|万立方米|立方米)")),
    ("调洪库容", re.compile(r"调洪库容[:：]?\s*(\d+(?:\.\d+)?)\s*(万m³|亿m³|万方|m³|万立方米|立方米)")),
    ("兴利库容", re.compile(r"兴利库容[:：]?\s*(\d+(?:\.\d+)?)\s*(万m³|亿m³|万方|m³|万立方米|立方米)")),
    ("防洪库容", re.compile(r"防洪库容[:：]?\s*(\d+(?:\.\d+)?)\s*(万m³|亿m³|万方|m³|万立方米|立方米)")),
    ("坝顶高程", re.compile(r"坝顶高程[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("坝高", re.compile(r"坝高[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("坝长", re.compile(r"坝长[:：]?\s*(\d+(?:\.\d+)?)\s*(米|m)")),
    ("流域面积", re.compile(r"流域面积[:：]?\s*(\d+(?:\.\d+)?)\s*(km²|平方公里|km2)")),
    ("设计流量", re.compile(r"设计流量[:：]?\s*(\d+(?:\.\d+)?)\s*(m³/s|立方米每秒|立方米/秒)")),
    ("泄洪流量", re.compile(r"泄洪流量[:：]?\s*(\d+(?:\.\d+)?)\s*(m³/s|立方米每秒|立方米/秒)")),
    ("降雨量", re.compile(r"(日降雨量|降雨量|雨量)[:：]?\s*(\d+(?:\.\d+)?)\s*(mm|毫米)")),
    ("时限", re.compile(r"(\d+)\s*(小时|h|分钟|min|天|日)(内|以内|之内)?")),
]


def _find_facility(text: str, center: int) -> Optional[str]:
    facilities = list({m.group(1) for m in FACILITY_PATTERN.finditer(text)})
    if not facilities:
        return None
    # 取距离 center 最近的设施名
    best = None
    best_dist = 10**9
    for m in FACILITY_PATTERN.finditer(text):
        dist = abs(m.start() - center)
        if dist < best_dist:
            best_dist = dist
            best = m.group(1)
    return best or facilities[0]


def _find_condition(text: str) -> Optional[str]:
    for kw in CONDITION_KEYWORDS:
        if kw in text:
            return kw
    # 响应级别也作为条件
    m = RULE_RESPONSE_LEVEL.search(text)
    if m:
        return m.group(0)
    return None


def _find_comparator(text: str) -> Optional[str]:
    for pat, comp in COMPARATOR_MAP:
        if pat.search(text):
            return comp
    return None


def _find_clause(text: str) -> Optional[str]:
    m = CLAUSE_PATTERN.search(text)
    if m:
        return m.group(1)
    m = TABLE_PATTERN.search(text)
    if m:
        return m.group(1)
    return None


def extract_facts(text: str, source_doc: str, source_page: str) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []

    for field, pat in FIELD_PATTERNS:
        for m in pat.finditer(text):
            # 统一数值/单位抓取
            if field == "降雨量":
                value = m.group(2)
                unit = m.group(3)
            elif field == "时限":
                value = m.group(1)
                unit = m.group(2)
            else:
                value = m.group(1)
                unit = m.group(2)

            try:
                value_num = float(value)
            except Exception:
                value_num = None

            ctx_s = max(0, m.start() - 40)
            ctx_e = min(len(text), m.end() + 40)
            ctx = text[ctx_s:ctx_e]

            entity_name = _find_facility(text, m.start())
            condition = _find_condition(ctx)
            comparator = _find_comparator(ctx)
            clause = _find_clause(ctx)

            facts.append(
                {
                    "entity_name": entity_name,
                    "field": field,
                    "value": value_num,
                    "value_text": f"{value}{unit}",
                    "unit": unit,
                    "comparator": comparator,
                    "condition": condition,
                    "source_doc": source_doc,
                    "source_page": source_page,
                    "source_clause": clause,
                    "evidence_text": ctx,
                    "confidence": 0.8,
                }
            )

    return facts
