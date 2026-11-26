# Customer Segmentation & Churn Pattern Analytics in European Banking

Segmentation-driven churn analysis of 10,000 retail customers (France, Spain, Germany),
with a research paper, an executive summary and a live Streamlit dashboard.

## Project structure

```
churn_project/
├── data/European_Bank.csv          # input dataset
├── analytics.py                    # validation, segmentation, churn metrics, KPIs (shared)
├── run_analysis.py                 # builds tables (CSV) and 14 figures
├── build_reports.py                # builds the research paper + executive summary (.docx)
├── app.py                          # Streamlit dashboard
├── requirements.txt                # dashboard dependencies (used for deployment)
├── requirements-analysis.txt       # extra packages for the analysis/report scripts
├── Dockerfile                      # optional container deployment
├── outputs/                        # generated CSV tables and figures/
└── docs/                           # generated Word documents
```

## Run locally

```bash
# 1. create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate

# 2. install everything
pip install -r requirements-analysis.txt

# 3. regenerate tables and figures
python run_analysis.py

# 4. regenerate the Word documents
python build_reports.py

# 5. launch the dashboard (opens http://localhost:8501)
streamlit run app.py
```

## Dashboard modules

| Tab | Content |
|---|---|
| Overall summary | KPI cards (churn rate, high-value churn ratio, engagement drop, balance lost), Geographic Risk Index, churned vs retained profile |
| Geography | churn by country, contribution vs size, country x age heatmap |
| Age & tenure | churn by age, tenure, credit band, balance segment; age x tenure heatmap |
| High-value explorer | adjustable balance threshold, decile chart, salary vs balance, top churned accounts |
| Drill-down | any one or two dimensions, ranked by churn, CSV download |
| Data & method | validation checks, segment definitions, filtered data download |

All sidebar filters update every KPI and chart.

## KPI definitions

- **Overall churn rate** = exited customers / all customers
- **Segment churn rate** = churn % within a segment
- **High-value churn ratio** = churn rate among customers in the top 25% of balances
- **Geographic Risk Index** = country churn rate / overall churn rate (1.00 = average)
- **Engagement Drop Indicator** = inactive churn rate / active churn rate

## Changing segment definitions

Edit the bins and labels at the top of `analytics.py` (age, credit score, tenure) and re-run the scripts.
