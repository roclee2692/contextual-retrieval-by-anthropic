"""
测试 Ollama 连接
确保 WSL 中的 Ollama 服务可以从 Windows 访问
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

def test_ollama_connection():
    """测试 Ollama 服务连接"""
    print("=" * 70)
    print("测试 Ollama 连接")
    print("=" * 70)
    print(f"目标地址: {OLLAMA_BASE_URL}")
    print()

    # 测试 1: 检查服务是否运行
    print("[1] 检查 Ollama 服务...")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama 服务运行正常")
            models = response.json().get("models", [])
            print(f"   已下载的模型数: {len(models)}")
            if models:
                print("   模型列表:")
                for model in models:
                    print(f"     - {model['name']}")
        else:
            print(f"⚠️  服务响应异常 (状态码: {response.status_code})")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 Ollama 服务")
        print("\n请检查:")
        print("  1. WSL 中是否运行了 'ollama serve'")
        print("  2. .env 中的 OLLAMA_BASE_URL 是否正确")
        print("  3. 如果无法使用 localhost，获取 WSL IP:")
        print("     在 WSL 中运行: hostname -I")
        print("     然后更新 .env: OLLAMA_BASE_URL=\"http://WSL_IP:11434\"")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

    # 测试 2: 检查特定模型
    print("\n[2] 检查 gemma3:12b 模型...")
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]

        if "gemma3:12b" in model_names:
            print("✅ gemma3:12b 模型已安装")
        else:
            print("⚠️  未找到 gemma3:12b 模型")
            print("\n请在 WSL 中运行:")
            print("  ollama pull gemma3:12b")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

    # 测试 3: 简单推理测试
    print("\n[3] 测试模型推理...")
    try:
        test_prompt = "你好，请用一句话介绍你自己。"
        print(f"   提示词: {test_prompt}")

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "gemma3:12b",
                "prompt": test_prompt,
                "stream": False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result.get("response", "")
            print(f"   回复: {answer[:100]}..." if len(answer) > 100 else f"   回复: {answer}")
            print("✅ 模型推理成功")
        else:
            print(f"⚠️  推理失败 (状态码: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

    # 测试 4: 聊天 API 测试 (/api/chat)
    print("\n[4] 测试聊天 API (/api/chat)...")
    try:
        test_message = "你好，这是一次测试。"
        print(f"   消息: {test_message}")

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": "gemma3:12b",
                "messages": [{"role": "user", "content": test_message}],
                "stream": False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            message = result.get("message", {}).get("content", "")
            print(f"   回复: {message[:100]}..." if len(message) > 100 else f"   回复: {message}")
            print("✅ 聊天 API 测试成功")
        else:
            print(f"⚠️  聊天 API 失败 (状态码: {response.status_code})")
            print(f"   返回内容: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        return False

    print("\n" + "=" * 70)
    print("✅ 所有测试通过！Ollama 配置正确。")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_ollama_connection()

    if success:
        print("\n下一步:")
        print("  1. 创建数据库: python create_save_db.py")
        print("  2. 启动服务: python app.py")
        print("  3. 运行测试: python test_ab_simple.py")
    else:
        print("\n❌ 测试失败，请先解决上述问题。")
