"""
查询路由器：A 类走属性层，B 类走 KG，C 类走段落检索
"""
import re
from typing import Dict
from src.tools.query_intent_parser import QueryIntentParser

_INTENT_PARSER = QueryIntentParser()

# 强关系/拓扑关键词：倾向 KG
KG_REL_KEYWORDS = [
    "上游", "下游", "包含", "组成", "隶属", "负责", "管理", "主管",
    "触发", "启动", "依赖", "依据", "位于", "属于",
]

# 数值/阈值/条件比较关键词：倾向属性层
ATTR_KEYWORDS = [
    "多少", "数值", "水位", "库容", "高程", "流量", "雨量", "面积",
    "阈值", "达到", "超过", "不低于", "不超过",
]


def route_query(query: str) -> Dict[str, str]:
    intent = _INTENT_PARSER.parse(query)
    qtype = intent.get("query_type")

    # 强制 A 类走属性层
    if qtype == "A":
        return {"route": "attribute", "reason": "A-数值属性"}

    # B 类：如果是拓扑/关系类关键词，走 KG
    if qtype == "B":
        if any(kw in query for kw in KG_REL_KEYWORDS):
            return {"route": "kg", "reason": "B-实体关系"}
        # 默认 B 类也可走 KG
        return {"route": "kg", "reason": "B-实体关系"}

    # C 类默认走段落检索
    if qtype == "C":
        return {"route": "vector", "reason": "C-流程条件"}

    # 兜底：根据关键词判断
    if any(kw in query for kw in ATTR_KEYWORDS):
        return {"route": "attribute", "reason": "关键词匹配"}
    if any(kw in query for kw in KG_REL_KEYWORDS):
        return {"route": "kg", "reason": "关键词匹配"}
    return {"route": "vector", "reason": "兜底"}
