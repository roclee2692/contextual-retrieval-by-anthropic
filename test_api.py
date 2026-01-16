"""
测试 FastAPI 服务
使用 curl 方式测试 API 接口
"""
import requests
import json

API_URL = "http://127.0.0.1:8000/rag-chat"

# 测试问题
test_questions = [
    "龙子湖校区有几个食堂？",
    "哪个食堂最便宜？",
    "早餐有什么推荐的？",
    "哪里可以吃到面食？",
    "食堂的营业时间是什么时候？"
]

def test_api(question):
    """测试单个问题"""
    print(f"\n问题: {question}")
    print("-" * 60)

    data = {"query": question}

    try:
        response = requests.post(
            API_URL,
            json=data,
            stream=True,
            timeout=120
        )

        print("回答: ", end="")
        for line in response.iter_lines():
            if line:
                text = line.decode('utf-8')
                print(text, end="", flush=True)
        print("\n")

    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("FastAPI RAG 服务测试")
    print("=" * 60)
    print(f"API 地址: {API_URL}")
    print("\n请确保已启动:")
    print("1. WSL 中: ollama serve")
    print("2. Windows 中: python app.py")
    print("\n按 Enter 开始测试...")
    input()

    for i, question in enumerate(test_questions, 1):
        print(f"\n[测试 {i}/{len(test_questions)}]")
        test_api(question)
        print("=" * 60)

    print("\n测试完成！")

