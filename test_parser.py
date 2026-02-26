from src.tools.query_intent_parser import QueryIntentParser

parser = QueryIntentParser()

test_queries = [
    "什么情况下需要启动III级应急响应？",  
    "水库水位达到多少时需要开始泄洪？",
    "堤防巡查的具体步骤是什么？",
]

for q in test_queries:
    result = parser.parse(q)
    print(f"Q: {q}")
    print(f"  Type: {result['query_type']}")
    print(f"  Variants: {result['rewritten']}")
    print()
