"""Shared analytics logic for the Customer Segmentation & Churn project.

Used by both run_analysis.py (report + figures) and app.py (Streamlit dashboard)
so that every number in the paper matches the dashboard.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "European_Bank.csv"

AGE_BINS = [0, 29, 45, 60, 200]
AGE_LABELS = ["<30", "30-45", "46-60", "60+"]

CREDIT_BINS = [0, 579, 699, 1000]
CREDIT_LABELS = ["Low (<580)", "Medium (580-699)", "High (700+)"]

TENURE_BINS = [-1, 2, 6, 100]
TENURE_LABELS = ["New (0-2 yrs)", "Mid-term (3-6 yrs)", "Long-term (7+ yrs)"]

BALANCE_LABELS = ["Zero balance", "Low balance", "High balance"]

SEGMENT_COLUMNS = {
    "Geography": "Geography",
    "AgeGroup": "Age group",
    "CreditBand": "Credit score band",
    "TenureGroup": "Tenure group",
    "BalanceSegment": "Balance segment",
    "Gender": "Gender",
    "NumOfProducts": "Number of products",
    "IsActiveMember": "Active member",
}


# --------------------------------------------------------------------------- #
# 1. Ingestion & validation
# --------------------------------------------------------------------------- #
def load_raw(path: Path | str = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Return a table of validation checks (check, result, passed)."""
    checks = []

    def add(name, result, passed):
        checks.append({"Check": name, "Result": result, "Passed": bool(passed)})

    add("Row count", f"{len(df):,}", len(df) > 0)
    add("Missing values", int(df.isna().sum().sum()), df.isna().sum().sum() == 0)
    add("Duplicate CustomerId", int(df["CustomerId"].duplicated().sum()),
        df["CustomerId"].duplicated().sum() == 0)
    for col in ["HasCrCard", "IsActiveMember", "Exited"]:
        vals = sorted(df[col].unique().tolist())
        add(f"{col} is binary (0/1)", str(vals), set(vals) <= {0, 1})
    add("NumOfProducts range", f"{df['NumOfProducts'].min()}-{df['NumOfProducts'].max()}",
        df["NumOfProducts"].min() >= 1)
    add("Geography values", ", ".join(sorted(df["Geography"].unique())),
        set(df["Geography"].unique()) <= {"France", "Spain", "Germany"})
    add("Negative balances", int((df["Balance"] < 0).sum()), (df["Balance"] < 0).sum() == 0)
    add("Age range", f"{df['Age'].min()}-{df['Age'].max()}", df["Age"].between(18, 100).all())
    add("Tenure range", f"{df['Tenure'].min()}-{df['Tenure'].max()}", df["Tenure"].between(0, 60).all())
    add("Churn labelled", f"{df['Exited'].mean():.2%} churn", df["Exited"].isin([0, 1]).all())
    return pd.DataFrame(checks)


# --------------------------------------------------------------------------- #
# 2. Cleaning & segmentation
# --------------------------------------------------------------------------- #
def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Drop non-analytical fields and create derived segmentation fields."""
    out = df.drop(columns=[c for c in ["Surname", "Year"] if c in df.columns]).copy()

    out["AgeGroup"] = pd.cut(out["Age"], AGE_BINS, labels=AGE_LABELS)
    out["CreditBand"] = pd.cut(out["CreditScore"], CREDIT_BINS, labels=CREDIT_LABELS)
    out["TenureGroup"] = pd.cut(out["Tenure"], TENURE_BINS, labels=TENURE_LABELS)

    # Balance: zero / low / high (split non-zero balances at their median)
    nonzero_median = out.loc[out["Balance"] > 0, "Balance"].median()
    seg = np.where(out["Balance"] == 0, BALANCE_LABELS[0],
                   np.where(out["Balance"] <= nonzero_median, BALANCE_LABELS[1], BALANCE_LABELS[2]))
    out["BalanceSegment"] = pd.Categorical(seg, categories=BALANCE_LABELS, ordered=True)

    # High-value customer = top quartile of balance across ALL customers
    q75 = out["Balance"].quantile(0.75)
    out["HighValue"] = (out["Balance"] >= q75).astype(int)

    out["Status"] = np.where(out["Exited"] == 1, "Churned", "Retained")
    out["ActiveLabel"] = np.where(out["IsActiveMember"] == 1, "Active", "Inactive")
    out["SalaryBand"] = pd.qcut(out["EstimatedSalary"], 4,
                                labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"])
    out["BalanceToSalary"] = out["Balance"] / out["EstimatedSalary"]
    return out


def load_clean() -> pd.DataFrame:
    return prepare(load_raw())


# --------------------------------------------------------------------------- #
# 3. Churn metrics
# --------------------------------------------------------------------------- #
def overall_churn(df: pd.DataFrame) -> float:
    return float(df["Exited"].mean()) if len(df) else float("nan")


def segment_churn(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Customers, churners, churn rate, share of customers and share of all churn."""
    g = (df.groupby(col, observed=True)["Exited"]
         .agg(Customers="count", Churned="sum").reset_index())
    g["ChurnRate"] = g["Churned"] / g["Customers"]
    g["ShareOfCustomers"] = g["Customers"] / g["Customers"].sum()
    g["ShareOfChurn"] = g["Churned"] / max(g["Churned"].sum(), 1)
    g["RelativeRisk"] = g["ChurnRate"] / overall_churn(df) if overall_churn(df) else np.nan
    return g


def churned_vs_retained(df: pd.DataFrame) -> pd.DataFrame:
    cols = ["CreditScore", "Age", "Tenure", "Balance", "NumOfProducts",
            "EstimatedSalary", "IsActiveMember", "HasCrCard"]
    return df.groupby("Status")[cols].mean().T[["Retained", "Churned"]]


def geography_age_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="Geography", columns="AgeGroup", values="Exited",
                          aggfunc="mean", observed=True)


def active_geo_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="Geography", columns="ActiveLabel", values="Exited",
                          aggfunc="mean", observed=True)


# --------------------------------------------------------------------------- #
# 4. KPIs
# --------------------------------------------------------------------------- #
def kpis(df: pd.DataFrame, reference: pd.DataFrame | None = None) -> dict:
    """Compute the five required KPIs.

    reference: full dataset used for the Geographic Risk Index denominator.
    """
    ref = reference if reference is not None else df
    out: dict = {}
    out["customers"] = len(df)
    out["churned"] = int(df["Exited"].sum())
    out["overall_churn"] = overall_churn(df)

    hv = df[df["HighValue"] == 1]
    out["high_value_customers"] = len(hv)
    out["high_value_churn"] = overall_churn(hv)

    inactive = df[df["IsActiveMember"] == 0]
    active = df[df["IsActiveMember"] == 1]
    out["inactive_churn"] = overall_churn(inactive)
    out["active_churn"] = overall_churn(active)
    # Engagement Drop Indicator: how many times more likely inactive members churn
    out["engagement_drop"] = (out["inactive_churn"] / out["active_churn"]
                              if out["active_churn"] and not np.isnan(out["active_churn"]) else float("nan"))

    # Geographic Risk Index = region churn rate / overall churn rate (1.0 = average)
    ref_rate = overall_churn(ref)
    gri = {}
    for geo, sub in df.groupby("Geography", observed=True):
        gri[geo] = overall_churn(sub) / ref_rate if ref_rate else float("nan")
    out["geo_risk_index"] = gri

    out["balance_lost"] = float(df.loc[df["Exited"] == 1, "Balance"].sum())
    out["balance_total"] = float(df["Balance"].sum())
    out["balance_lost_share"] = out["balance_lost"] / out["balance_total"] if out["balance_total"] else float("nan")
    return out


def high_value_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Revenue-at-risk summary for high-value customers."""
    rows = []
    for name, sub in [("All customers", df), ("High-value (top 25% balance)", df[df["HighValue"] == 1]),
                      ("Other customers", df[df["HighValue"] == 0])]:
        rows.append({
            "Group": name,
            "Customers": len(sub),
            "ChurnRate": overall_churn(sub),
            "BalanceAtRisk": float(sub.loc[sub["Exited"] == 1, "Balance"].sum()),
            "AvgBalanceChurned": float(sub.loc[sub["Exited"] == 1, "Balance"].mean()) if sub["Exited"].sum() else 0.0,
            "AvgSalaryChurned": float(sub.loc[sub["Exited"] == 1, "EstimatedSalary"].mean()) if sub["Exited"].sum() else 0.0,
        })
    return pd.DataFrame(rows)


def top_risk_segments(df: pd.DataFrame, cols: list[str], min_size: int = 100) -> pd.DataFrame:
    """Churn rate for combinations of segment columns, ranked high to low."""
    g = (df.groupby(cols, observed=True)["Exited"].agg(Customers="count", Churned="sum").reset_index())
    g["ChurnRate"] = g["Churned"] / g["Customers"]
    g = g[g["Customers"] >= min_size].sort_values("ChurnRate", ascending=False)
    return g.reset_index(drop=True)
