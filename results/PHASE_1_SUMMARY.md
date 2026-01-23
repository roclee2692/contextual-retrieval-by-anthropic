# Phase 1: Contextual Retrieval Summary

## Overview
We executed a comparison between a Baseline RAG approach (BM25 + Vector Search on raw chunks) and Anthropic's Contextual Retrieval approach (augmenting chunks with LLM-generated context) on a dataset of Flood Prevention Plans ("防洪预案").

## Methodology
1.  **Data Processing**: Converted original Word/PDF documents to text.
2.  **Baseline Index**: Created a standard Vector Store (ChromaDB) + BM25 index using 512-token chunks.
3.  **Contextual Index**: 
    - Used `gemma3:12b` via Ollama to generate a "situating context" for each chunk.
    - Prepended this context to the text before indexing.
4.  **Retrieval**: Performed hybrid retrieval (Vector + BM25) for a set of domain-specific questions.

## Results Comparison

| Query Category | Query | Baseline Observation | Contextual Observation | Improvement |
| :--- | :--- | :--- | :--- | :--- |
| **Specific Data** | 杨家横水库的汛限水位是多少？ | Retrieved general rainfall data (287.90mm) and some unrelated historical data. | Retrieved chunk explicitly labeled "Flood control procedures and indicators". Context helped identify the correct *type* of section. | ⚠️ Partial. Specific value might still be hard to extract if not in top chunk, but semantic relevance improved. |
| **definitions** | 堤防巡查的标准是什么？ | Retrieved "Prohibitions" (what NOT to do), e.g., dumping sewage, driving heavy vehicles. | Retrieved "Daily inspection record form" containing specific frequency (twice a week) and routing. | ✅ **Significant**. Context clarified "Inspection Standards" vs "Dam Damage Prohibitions". |
| **Procedures** | 防洪抢险有哪些措施？ | Retrieved general definition of "Super-standard flood". | Retrieved "Flood prevention and emergency response procedures" with focus on preparation and measure implementation. | ✅ **Good**. Better alignment with the procedural nature of the question. |

## Key Findings
- **Context disambiguates short chunks**: Short snippets like list items ("1. ...", "2. ...") are often meaningless on their own. The generated context ("This is a list of contact numbers for flood control...") makes them retrievable.
- **Improved Semantic Matching**: As seen in the "Inspection Standards" case, the baseline often matches keywords ("patrol/check") in wrong contexts (prohibitions), while Contextual Retrieval aligns with the *intent* (standard operating procedures).

## Next Steps
- Proceed to **Phase 2: Knowledge Graph**.
- Build a graph structure to capture relationships (e.g., `Person` manages `Reservoir`, `Plan` covers `Area`) to answer multi-hop questions that single-chunk retrieval misses.
