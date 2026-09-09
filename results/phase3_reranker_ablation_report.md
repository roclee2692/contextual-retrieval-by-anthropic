# Phase 3 Reranker Ablation Report — Legacy Results and Evaluation Limits

**Recorded:** 2026-02-03 12:46:14
**Status:** **DEPRECATED AS A PERFORMANCE COMPARISON.** The raw records below are retained for reproducibility, but they do not establish Reranker effectiveness or statistical significance.

## Evaluation protocol

This repository contains two distinct evaluation protocols:

| Protocol | Dataset / decision rule | Reported values | Valid use |
|---|---|---|---|
| Main Phase 3 experiment | 30 questions; **Top-1 Retrieval Accuracy** from a keyword-hit judgement | Baseline 76.7% (23/30); CR 80.0% (24/30) | The repository's primary Baseline-vs-CR result |
| Early Reranker ablation | 30 questions; **Top-3 Keyword Hit Rate** after concatenating retrieved results | 96.7% / 86.7% | Legacy diagnostic only; not comparable with Top-1 Retrieval Accuracy |

The early ablation also reported original retriever scores (for example, 0.5145) beside Cross-Encoder scores (for example, 0.9552). These values are produced by different scoring functions and numerical scales. Their difference is **not** a retrieval-performance gain, and a paired t-test of those raw scores is invalid evidence for a Reranker effect. Accordingly, historical t/p-value claims are preserved only as deprecated records below and are not conclusions of this report.

## Legacy 2×2 record (not a cross-protocol comparison)

|  | Without Reranker | With Reranker | Legacy Top-3 Keyword Hit Rate difference |
|--|---:|---:|---:|
| Baseline | 96.7% (29/30) | 96.7% (29/30) | +0.0 percentage points |
| CR | 86.7% (26/30) | 96.7% (29/30) | +10.0 percentage points |

These are **legacy Top-3 Keyword Hit Rate** values. They must not be called “Retrieval Accuracy,” compared against the 76.7%/80.0% main Top-1 result, or used to rank Baseline, CR, and Reranker configurations.

## Legacy score record (not a performance metric)

| Method | Score function | Mean reported score | Legacy Top-3 Keyword Hit Rate |
|---|---|---:|---:|
| Baseline | Retriever score | 0.5145 | 96.7% |
| Baseline + Reranker | Cross-Encoder score | 0.9552 | 96.7% |
| CR Enhanced | Retriever score | 0.5188 | 86.7% |
| CR + Reranker | Cross-Encoder score | 0.9580 | 96.7% |

**Do not compute or report a percentage improvement from 0.5145 to 0.9552.** The values are not on a common scale. The historical `p=0.0000` / paired-t-test entries that compared these columns are deprecated and intentionally omitted as inferential results.

## Main Phase 3 result (separate protocol)

For the primary, Top-1 protocol, the recorded results are:

| Method | Top-1 Retrieval Accuracy | Correct count |
|---|---:|---:|
| Baseline | 76.7% | 23/30 |
| CR Enhanced | 80.0% | 24/30 |

This table is not an ablation baseline for the legacy Top-3 Reranker results. It is shown only to prevent accidental mixing of protocols.

## What can and cannot be concluded

- The legacy run shows that a Cross-Encoder was applied to the same candidate lists; it does **not** quantify a reliable performance benefit.
- No claim that Reranker is “most effective,” “significantly improves,” or “corrects errors” is supported by these records.
- A valid reranking evaluation must hold the test set, candidate pool, relevance labels, and cutoff constant; compare pre- and post-rerank results using common metrics such as Accuracy@1, Recall@K, MRR, and nDCG@K; and perform any statistical test on one of those common per-query metrics.
