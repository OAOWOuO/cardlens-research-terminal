# MGMT690 Project 2 — CardLens Research Terminal
## Methodology & Originality Report

---

## 1. What I Built

**CardLens Research Terminal** is a Streamlit-based intelligent equity research workbench for the Mastercard (MA) case. It integrates case-document grounding, market data, and multi-signal analysis into a single terminal UI.

### Features Implemented

| Feature | Description |
|---------|-------------|
| **Case Q&A (RAG)** | Chat interface that answers questions using only local case documents, citing the source file and page |
| **Fundamentals** | yfinance-sourced metrics (margins, ROE, FCF, P/E) + quality checklist |
| **Valuation** | PE-band comparison + transparent DCF-lite with editable assumptions |
| **Technicals** | Interactive Plotly chart with candlestick, SMA 50/200, RSI, MACD, and trend signal |
| **News** | Latest headlines via yfinance, with RSS fallback |
| **Sources** | Document library browser with chunk count, index timestamp, and per-file preview |
| **Recommendation** | Rules-based final decision (Buy/Hold/Avoid) merging all 3 signals + RAG catalysts/risks |
| **CI/CD** | GitHub Actions pipeline running Ruff lint + Pytest on every push |

### Configuration Controls (Sidebar)
- **Ticker**: Free text (default: MA)
- **Horizon**: 1W / 1M / 3M / 6M — affects scenario ranges in Recommendation
- **Risk Profile**: Conservative / Balanced / Aggressive — affects margin-of-safety threshold

---

## 2. Documents Used (data/raw/)

Place your Mastercard case materials here before running. Accepted formats:
- PDF (ingested page-by-page via pdfplumber)
- TXT / MD (ingested as single text block)

Expected files for MGMT690 Project 2:
- Mastercard HBS case PDF
- Any supplementary readings, analyst reports, or lecture notes

All documents in `data/raw/` are automatically detected and ingested when you click **Rebuild Document Index**.

---

## 3. How RAG Works

### Step 1 — Ingestion (`src/ingest.py`)
- PDF pages extracted with `pdfplumber`
- Text chunked into ~900-token windows with 150-token overlap (using `tiktoken` cl100k_base encoding)
- Each chunk stored in `data/processed/chunks.jsonl` with metadata: `filename`, `page`, `chunk_id`, `text`

### Step 2 — Embeddings (`src/embeddings.py`)
- Each chunk embedded via OpenAI `text-embedding-3-small`
- Batched in groups of 100 for API efficiency
- Saved as `data/index/embeddings.npz` (numpy array) + `data/index/meta.json` (metadata)

### Step 3 — Retrieval (`src/retrieval.py`)
- Query embedded with same model
- Cosine similarity computed via `sklearn.metrics.pairwise.cosine_similarity`
- Top-k chunks returned with citation tags: `[Source: filename p.N]`

### Step 4 — Grounded QA (`src/qa.py`)
- Retrieved chunks assembled into context
- LLM (gpt-4o-mini) instructed with strict system prompt:
  - "Answer ONLY using the provided excerpts"
  - "If insufficient, say 'Not found in provided case materials'"
  - "Always cite sources"
- Returns `answer`, `citations` list, `excerpts` (with scores)

---

## 4. How the Recommendation is Produced

Three independent signal scores are computed:

### Fundamentals Score
| Check | Pass Condition | Score |
|-------|---------------|-------|
| Operating margin | > 20% | +1 |
| ROE | > 15% | +1 |
| Free Cash Flow | > 0 | +1 |

### Valuation Score
| Check | Condition | Score |
|-------|-----------|-------|
| Margin of safety vs base PE (28x) | ≥ risk threshold | +2 |
| Margin of safety | ≥ 0 but < threshold | +1 |
| Overvalued vs PE | < 0 | -1 |
| Trailing P/E | < 25x | +1 / > 40x | -1 |

Risk thresholds: Conservative = 20%, Balanced = 10%, Aggressive = 5%

### Technicals Score
| Check | Pass Condition | Score |
|-------|---------------|-------|
| Price vs SMA50 | Above | +1 |
| Price vs SMA200 | Above | +1 |
| RSI | 40–65 = constructive | +1 / ≥70 | -1 |

### Decision Rules
| Total Score | Decision | Confidence |
|-------------|----------|-----------|
| ≥ 4 | BUY | High |
| 2–3 | BUY | Medium |
| 0–1 | HOLD | Medium |
| -1 to -2 | HOLD | Low |
| ≤ -3 | AVOID | Medium |

### Horizon Scenario Ranges
Pre-defined per horizon (1W/1M/3M/6M), labeled as illustrative scenarios — **not predictions**.

### Case-Grounded Context
When the document index is built, the Recommendation page runs two RAG queries:
- "What are the key growth catalysts for {ticker}?"
- "What are the key risks for {ticker}?"

Answers and citations from case documents appear alongside the quantitative signals.

---

## 5. Limitations and Next Steps

### Limitations
- **yfinance data quality**: Some metrics may be missing or delayed. Always cross-reference.
- **DCF sensitivity**: Intrinsic value is highly sensitive to discount rate and terminal growth assumptions. Treat as a range, not a precise number.
- **RAG coverage**: Quality of answers depends entirely on the documents provided. Sparse documents → "Not found" responses.
- **Technicals**: Simple heuristics only. No volume analysis, no pattern recognition.
- **No backtesting**: Signal rules are not calibrated against historical accuracy.

### Next Steps
1. Add a Portfolio scenario builder (position sizing by risk profile)
2. Integrate SEC EDGAR for official filings (10-K, 10-Q)
3. Add peer comparison (V, AXP, DFS) in Fundamentals
4. Implement LLM-generated executive summary from all signals
5. Add export to PDF report for submission

---

*Built for MGMT690 Project 2 · CardLens Research Terminal · Mastercard Case*
