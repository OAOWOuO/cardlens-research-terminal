# CardLens Research Terminal (MGMT690 Project 2)

A Streamlit-based research terminal for the Mastercard case.
Features:
- Case-grounded Q&A (RAG with citations from local docs)
- Fundamentals, Valuation, Technicals, News
- Final recommendation (Buy/Hold/Avoid) with horizon outlook

## Quickstart
1) `cp .env.example .env` and add your API key(s)
2) `poetry install`
3) `poetry run streamlit run app/Home.py`

## Data Sources
- Case materials in `data/raw/` (PDF/TXT/MD). Q&A must cite these.
- Market data via yfinance (prices, basic fundamentals).
- News via a public RSS or a free endpoint (no paid keys required unless available).

## Security
Never commit `.env`. Keep secrets local or in Streamlit Cloud secrets.
