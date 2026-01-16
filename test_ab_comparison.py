"""
A/B 对比测试：上下文检索 vs 普通检索
测试 20 个关于龙子湖食堂的问题
"""
import os
import time
import json
from dotenv import load_dotenv
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

load_dotenv()

# 配置 Ollama 连接到 WSL
# 如果 WSL 的 IP 是 localhost，端口是 11434
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# 20 个测试问题
TEST_QUESTIONS = [
    "龙子湖校区有几个食堂？",
    "哪个食堂最便宜？",
    "哪个食堂的菜品种类最多？",
    "食堂的营业时间是什么时候？",
    "早餐有什么推荐的？",
    "哪里可以吃到面食？",
    "哪个食堂的环境最好？",
    "有清真餐厅吗？",
    "晚上宵夜哪里可以吃？",
    "哪个食堂离教学楼最近？",
    "食堂可以用支付宝吗？",
    "哪里有麻辣烫？",
    "食堂的米饭多少钱？",
    "哪个食堂人最少？",
    "有没有水果店？",
    "食堂二楼有什么特色？",
    "周末食堂开门吗？",
    "哪里可以吃到炒菜？",
    "食堂有WiFi吗？",
    "学生推荐去哪个食堂？"
]

class ABTester:
    def __init__(self):
        # 初始化 LLM (连接到 WSL 的 Ollama)
        self.llm = Ollama(
            model="gemma3:12b",
            base_url=OLLAMA_BASE_URL,
            request_timeout=120.0
        )

        # 初始化 Embedding 模型
        self.embed_model = HuggingFaceEmbedding(
            model_name="BAAI/bge-small-zh-v1.5"
        )

        # 设置全局配置
        Settings.llm = self.llm
        Settings.embed_model = self.embed_model

        self.data_dir = os.getenv("DATA_DIR", "./data")

    def load_documents(self):
        """加载文档"""
        reader = SimpleDirectoryReader(input_dir=self.data_dir)
        documents = reader.load_data()
        return documents

    def create_normal_index(self, documents):
        """创建普通的 RAG 索引（不加上下文）"""
        print("\n=== 创建普通 RAG 索引 ===")
        splitter = TokenTextSplitter(
            chunk_size=512,
            chunk_overlap=20,
            separator=" "
        )
        nodes = splitter.get_nodes_from_documents(documents)
        print(f"文档被分割成 {len(nodes)} 个chunks")

        index = VectorStoreIndex(nodes)
        return index

    def create_contextual_index(self, documents):
        """创建上下文增强的 RAG 索引"""
        print("\n=== 创建上下文增强 RAG 索引 ===")

        # 获取完整文档内容
        full_content = ""
        for doc in documents:
            full_content += doc.text

        splitter = TokenTextSplitter(
            chunk_size=512,
            chunk_overlap=20,
            separator=" "
        )
        nodes = splitter.get_nodes_from_documents(documents)
        print(f"文档被分割成 {len(nodes)} 个chunks")

        # 为每个 chunk 添加上下文
        template = """
<document> 
{WHOLE_DOCUMENT} 
</document> 
这是我们要在整个文档中定位的文本块:
<chunk> 
{CHUNK_CONTENT} 
</chunk> 
请给出一个简短的上下文说明，将这个文本块置于整个文档中，以便改进该文本块的搜索检索效果。
只回答简短的上下文说明，不要其他内容。
"""

        print("正在为每个 chunk 生成上下文...")
        for idx, node in enumerate(nodes):
            content = node.text
            prompt = template.format(
                WHOLE_DOCUMENT=full_content[:4000],  # 限制长度避免超token
                CHUNK_CONTENT=content
            )

            try:
                response = self.llm.complete(prompt)
                contextual_text = response.text + "\n\n" + content
                nodes[idx].text = contextual_text
                print(f"处理进度: {idx+1}/{len(nodes)}", end="\r")
            except Exception as e:
                print(f"\n警告: chunk {idx} 上下文生成失败: {e}")
                # 如果失败，保持原文本

        print(f"\n上下文生成完成！")

        index = VectorStoreIndex(nodes)
        return index

    def test_query(self, index, query, method_name):
        """测试单个查询"""
        query_engine = index.as_query_engine(similarity_top_k=3)

        start_time = time.time()
        response = query_engine.query(query)
        end_time = time.time()

        return {
            "method": method_name,
            "query": query,
            "response": str(response),
            "time": end_time - start_time
        }

    def run_comparison(self, questions=None):
        """运行 A/B 对比测试"""
        if questions is None:
            questions = TEST_QUESTIONS

        print("=== 开始 A/B 对比测试 ===\n")

        # 加载文档
        documents = self.load_documents()
        print(f"加载了 {len(documents)} 个文档")

        # 创建两个索引
        normal_index = self.create_normal_index(documents)
        contextual_index = self.create_contextual_index(documents)

        # 存储结果
        results = []

        print("\n=== 开始测试查询 ===\n")
        for i, question in enumerate(questions, 1):
            print(f"\n[{i}/{len(questions)}] 问题: {question}")

            # 测试普通方法
            print("  - 测试普通 RAG...")
            normal_result = self.test_query(normal_index, question, "普通RAG")

            # 测试上下文方法
            print("  - 测试上下文 RAG...")
            contextual_result = self.test_query(contextual_index, question, "上下文RAG")

            results.append({
                "question": question,
                "normal": normal_result,
                "contextual": contextual_result
            })

            # 打印简要对比
            print(f"  普通 RAG 耗时: {normal_result['time']:.2f}s")
            print(f"  上下文 RAG 耗时: {contextual_result['time']:.2f}s")

        # 保存结果
        self.save_results(results)

        # 打印总结
        self.print_summary(results)

        return results

    def save_results(self, results):
        """保存测试结果到文件"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"ab_test_results_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存到: {filename}")

        # 同时生成可读性更好的文本报告
        txt_filename = f"ab_test_report_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("上下文检索 vs 普通检索 A/B 对比测试报告\n")
            f.write("=" * 80 + "\n\n")

            for i, result in enumerate(results, 1):
                f.write(f"\n问题 {i}: {result['question']}\n")
                f.write("-" * 80 + "\n")
                f.write(f"\n【普通 RAG 回答】 (耗时: {result['normal']['time']:.2f}s)\n")
                f.write(result['normal']['response'] + "\n")
                f.write(f"\n【上下文 RAG 回答】 (耗时: {result['contextual']['time']:.2f}s)\n")
                f.write(result['contextual']['response'] + "\n")
                f.write("\n" + "=" * 80 + "\n")

        print(f"报告已保存到: {txt_filename}")

    def print_summary(self, results):
        """打印测试总结"""
        print("\n" + "=" * 80)
        print("测试总结")
        print("=" * 80)

        normal_times = [r['normal']['time'] for r in results]
        contextual_times = [r['contextual']['time'] for r in results]

        print(f"\n总问题数: {len(results)}")
        print(f"\n普通 RAG:")
        print(f"  - 平均响应时间: {sum(normal_times)/len(normal_times):.2f}s")
        print(f"  - 最快: {min(normal_times):.2f}s")
        print(f"  - 最慢: {max(normal_times):.2f}s")

        print(f"\n上下文 RAG:")
        print(f"  - 平均响应时间: {sum(contextual_times)/len(contextual_times):.2f}s")
        print(f"  - 最快: {min(contextual_times):.2f}s")
        print(f"  - 最慢: {max(contextual_times):.2f}s")


if __name__ == "__main__":
    print("=" * 80)
    print("龙子湖食堂 RAG 系统 A/B 对比测试")
    print("=" * 80)
    print(f"\nOllama 服务地址: {OLLAMA_BASE_URL}")
    print("请确保 WSL 上的 Ollama 服务已启动: ollama serve")
    print("\n按 Enter 继续...")
    input()

    tester = ABTester()
    results = tester.run_comparison()

    print("\n测试完成！")

