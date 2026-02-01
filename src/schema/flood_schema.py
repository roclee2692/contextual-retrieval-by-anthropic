from typing import List, Dict, Any

class FloodSchema:
    """
    防洪预案知识图谱模式定义
    模拟 OpenSPG 的 Schema 定义风格，用于生成 OneKE 的抽取指令
    """
    
    # 定义实体类型 (Entity Types)
    ENTITIES = {
        "Reservoir": "水库",
        "River": "河流",
        "Dike": "堤防",
        "Station": "水文站",
        "Person": "人员",
        "Organization": "组织机构",
        "Plan": "预案",
        "Task": "任务",
        "City": "城市/行政区"
    }
    
    # 定义关系类型 (Relation Types / Predicates)
    RELATIONS = [
        # 属性关系 (Attribute Relations)
        "汛限水位", "校核洪水位", "设计洪水位", "警戒水位", "保证水位", # 水位相关
        "总库容", "调洪库容", "死库容", # 库容相关
        "地理位置", "流域面积", "长度", 
        "联系电话", "职务",
        
        # 拓扑与管理关系
        "位于", "属于", "管理", "负责人", 
        "下游是有", "上游是有", "流经",
        
        # 业务逻辑关系
        "触发条件", "响应措施", "发布单位", "包含任务"
    ]

    @classmethod
    def get_oneke_instruction(cls) -> str:
        """
        生成适用于 OneKE 模型的 System Instruction
        经过测试，最简单的格式效果最好
        """
        return "抽取实体关系：\n"

    @classmethod
    def parse_oneke_response(cls, text: str) -> List[tuple]:
        """
        解析 OneKE 的输出格式
        OneKE 实际输出格式：
        {"抽取 entity关系": [{"subject": "X", "object": "Y"}, ...]}
        或直接 [{"subject": "X", "object": "Y"}, ...]
        """
        triplets = []
        import json
        import re
        
        text = text.strip()
        if not text:
            return triplets
        
        # ======== 核心解析: 找所有 {"subject": "X", "object": "Y"} 结构 ========
        # 这是 OneKE 最常见的输出格式（无 predicate）
        pattern_no_pred = r'\{\s*"subject"\s*:\s*"([^"]+)"\s*,\s*"object"\s*:\s*"([^"]+)"\s*\}'
        matches = re.findall(pattern_no_pred, text)
        for match in matches:
            subject, obj = match
            triplets.append((subject.strip(), "related_to", obj.strip()))
        
        # ======== 备用: 匹配有 predicate 的情况 ========
        pattern_full = r'\{\s*"subject"\s*:\s*"([^"]+)"\s*,\s*"predicate"\s*:\s*"([^"]+)"\s*,\s*"object"\s*:\s*"([^"]+)"\s*\}'
        matches = re.findall(pattern_full, text)
        for match in matches:
            subject, predicate, obj = match
            triplets.append((subject.strip(), predicate.strip(), obj.strip()))
        
        # ======== 备用: 中文键名 主体/关系/客体 ========
        pattern_cn = r'\{\s*"主体"\s*:\s*"([^"]+)"\s*,\s*"关系"\s*:\s*"([^"]+)"\s*,\s*"客体"\s*:\s*"([^"]+)"\s*\}'
        matches = re.findall(pattern_cn, text)
        for match in matches:
            subject, relation, obj = match
            triplets.append((subject.strip(), relation.strip(), obj.strip()))
        
        # 去重
        triplets = list(set(triplets))
        
        return triplets

    @classmethod
    def get_prompt_template(cls) -> str:
        """
        返回 LlamaIndex 可用的 Prompt Template 字符串
        """
        attributes = '", "'.join(cls.RELATIONS)
        entities = '", "'.join(cls.ENTITIES.values())
        
        return (
            "你是一个基于 Schema 的知识抽取专家 (OneKE 模式)。\n"
            "我们定义了以下【关系列表】(Predicates)：\n"
            f'["{attributes}"]\n\n'
            "我们定义了以下【实体类型】(Entity Types)：\n"
            f'["{entities}"]\n\n'
            "任务：从下面的文本中提取符合上述定义的三元组。\n"
            "规则 1: 严格匹配定义的关系名称，不要自己发明关系（如 'WaterLevel' 请映射到 '水位' 或具体如 '汛限水位'）。\n"
            "规则 2: 如果关系是数值属性（如水位、库容），尾实体应包含单位。\n"
            "规则 3: 输出格式必须是：(头实体, 关系, 尾实体)\n"
            "规则 4: 每行一个三元组，不要包含其他解释文字。\n\n"
            "文本内容：\n"
            "{text}\n\n"
            "提取结果：\n"
        )
