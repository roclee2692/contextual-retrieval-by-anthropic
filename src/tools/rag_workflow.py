import os
from llama_index.core.response_synthesizers import CompactAndRefine
from llama_index.core.workflow import (
    Context,
    Workflow,
    StartEvent,
    StopEvent,
    step,
)

from llama_index.core import PromptTemplate
from llama_index.core.workflow import Event
from llama_index.core.schema import NodeWithScore
from llama_index.llms.ollama import Ollama
from src.db.read_db import SemanticBM25Retriever
from src.tools.query_intent_parser import QueryIntentParser, format_intent_summary

# 全局 intent parser（单例复用）
_INTENT_PARSER = QueryIntentParser()

class RetrieverEvent(Event):
    """Result of running retrieval"""

    nodes: list[NodeWithScore]

# prompt template（防洪预案专用中文模板）
template = (
    "以下是从防洪预案文档中检索到的相关内容：\n"
    "---------------------\n"
    "{context_str}"
    "\n---------------------\n"
    "请根据以上内容，用中文简洁准确地回答以下问题：{query_str}\n"
    "如果文档中没有相关信息，请如实说明。\n"
)

qa_template = PromptTemplate(template)

# RAG using workflow
class RAGWorkflow(Workflow):

    @step
    async def ingest(self, ctx: Context, ev: StartEvent) -> StopEvent | None:

        collection_name = ev.get("collection_name")
        if not collection_name:
            return None

        retriever = SemanticBM25Retriever(collection_name=collection_name)

        return StopEvent(result=retriever)

    @step
    async def retrieve(
        self, ctx: Context, ev: StartEvent
    ) -> RetrieverEvent | None:

        query = ev.get("query")
        retriever = ev.get("retriever")

        if not query:
            return None

        # ── 意图解析 + 查询扩写 ──────────────────────────────
        intent = _INTENT_PARSER.parse(query)
        rewritten_queries = intent["rewritten"]

        print(f"[意图解析] 类型={intent['query_type']}  "
              f"设施={intent['facility']}  "
              f"属性={intent['attribute'] or intent['action_type'] or '-'}")
        print(f"[扩写查询] {rewritten_queries}")

        await ctx.set("query", query)
        await ctx.set("intent", intent)

        if retriever is None:
            print("Index is empty, load some documents before querying!")
            return None

        # ── 多路检索（原始查询 + 扩写查询，合并去重） ────────
        seen_ids: set = set()
        merged_nodes: list[NodeWithScore] = []

        for rq in rewritten_queries:
            nodes = await retriever.aretrieve(rq)
            for node in nodes:
                node_id = node.node.node_id
                if node_id not in seen_ids:
                    seen_ids.add(node_id)
                    merged_nodes.append(node)

        # 按得分降序排列
        merged_nodes.sort(key=lambda n: n.score or 0.0, reverse=True)
        print(f"[检索合并] {len(merged_nodes)} 个去重节点（来自 {len(rewritten_queries)} 路查询）")

        return RetrieverEvent(nodes=merged_nodes)

    @step
    async def synthesize(self, ctx: Context, ev: RetrieverEvent) -> StopEvent:

        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        llm = Ollama(
            model="gemma3:12b",
            base_url=ollama_base_url,
            request_timeout=120.0
        )
        summarizer = CompactAndRefine(llm=llm, streaming=True, verbose=True, text_qa_template=qa_template)
        query = await ctx.get("query", default=None)

        response = await summarizer.asynthesize(query, nodes=ev.nodes)

        return StopEvent(result=response)

