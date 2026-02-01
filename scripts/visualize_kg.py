"""
知识图谱可视化工具
将食堂知识图谱可视化为网络图
"""
import os
import sys
from llama_index.core import StorageContext, load_index_from_storage, Settings
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib import font_manager
import warnings
warnings.filterwarnings('ignore')

# 禁用 LLM 和 Embedding，因为可视化只需要读取结构
Settings.llm = None
Settings.embed_model = None

def visualize_knowledge_graph():
    """可视化知识图谱"""

    SAVE_DIR = "./src/db/knowledge_graph"

    if not os.path.exists(SAVE_DIR):
        print("❌ 知识图谱不存在")
        print("请先运行: python create_knowledge_graph.py")
        return

    print("="*80)
    print("  知识图谱可视化")
    print("="*80)

    # 加载图谱
    print("\n[1/3] 加载知识图谱...")
    storage_context = StorageContext.from_defaults(persist_dir=SAVE_DIR)
    kg_index = load_index_from_storage(storage_context)
    print("✓ 加载成功")

    # 获取 NetworkX 图
    print("\n[2/3] 提取图结构...")
    try:
        G = kg_index.get_networkx_graph()
        print(f"✓ 节点数: {G.number_of_nodes()}")
        print(f"✓ 边数: {G.number_of_edges()}")
    except Exception as e:
        print(f"❌ 提取失败: {e}")
        return

    # 可视化
    print("\n[3/3] 生成可视化...")

    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    plt.rcParams['axes.unicode_minus'] = False

    # 创建图形
    plt.figure(figsize=(20, 14))

    # 使用 Spring 布局
    pos = nx.spring_layout(G, k=0.5, iterations=50)

    # 绘制节点
    nx.draw_networkx_nodes(
        G, pos,
        node_color='lightblue',
        node_size=800,
        alpha=0.9
    )

    # 绘制边
    nx.draw_networkx_edges(
        G, pos,
        edge_color='gray',
        arrows=True,
        arrowsize=20,
        width=1.5,
        alpha=0.6
    )

    # 绘制节点标签
    nx.draw_networkx_labels(
        G, pos,
        font_size=8,
        font_family='sans-serif'
    )

    # 绘制边标签（关系）
    edge_labels = nx.get_edge_attributes(G, 'label')
    if edge_labels:
        nx.draw_networkx_edge_labels(
            G, pos,
            edge_labels=edge_labels,
            font_size=6
        )

    plt.title("龙子湖食堂知识图谱", fontsize=16, pad=20)
    plt.axis('off')
    plt.tight_layout()

    # 保存图片
    output_file = "./knowledge_graph.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ 图谱已保存到: {output_file}")

    # 显示
    plt.show()

    # 打印统计信息
    print("\n" + "="*80)
    print("图谱统计")
    print("="*80)
    print(f"节点数（实体）: {G.number_of_nodes()}")
    print(f"边数（关系）: {G.number_of_edges()}")

    # 打印部分节点
    print("\n前10个节点:")
    for i, node in enumerate(list(G.nodes())[:10], 1):
        print(f"  {i}. {node}")

    # 打印部分边
    print("\n前10个关系:")
    for i, (u, v, data) in enumerate(list(G.edges(data=True))[:10], 1):
        label = data.get('label', '未知关系')
        print(f"  {i}. ({u}) --[{label}]--> ({v})")


def export_triples():
    """导出三元组到文本文件"""

    SAVE_DIR = "./src/db/knowledge_graph"

    if not os.path.exists(SAVE_DIR):
        print("❌ 知识图谱不存在")
        return

    print("\n导出三元组...")

    storage_context = StorageContext.from_defaults(persist_dir=SAVE_DIR)
    kg_index = load_index_from_storage(storage_context)

    G = kg_index.get_networkx_graph()

    output_file = "./knowledge_graph_triples.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("龙子湖食堂知识图谱 - 三元组列表\n")
        f.write("="*80 + "\n\n")

        for i, (u, v, data) in enumerate(G.edges(data=True), 1):
            label = data.get('label', '关系')
            f.write(f"{i}. ({u}) --[{label}]--> ({v})\n")

    print(f"✓ 三元组已导出到: {output_file}")
    print(f"共 {G.number_of_edges()} 个三元组")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "export":
        export_triples()
    else:
        visualize_knowledge_graph()

        # 询问是否导出
        user_input = input("\n是否导出三元组到文本文件？(y/n): ")
        if user_input.lower() == 'y':
            export_triples()

