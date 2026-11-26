"""Streamlit dashboard - Customer Segmentation & Churn Pattern Analytics (European Banking).

Run locally:  streamlit run app.py
"""
import altair as alt
import pandas as pd
import streamlit as st

import analytics as a

st.set_page_config(page_title="European Banking Churn Analytics", page_icon="🏦", layout="wide")

RED, BLUE = "#c53030", "#2b6cb0"


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
@st.cache_data
def get_data() -> pd.DataFrame:
    return a.load_clean()


full = get_data()

# --------------------------------------------------------------------------- #
# Sidebar filters (drive every KPI and chart)
# --------------------------------------------------------------------------- #
st.sidebar.title("Segment filters")
geos = st.sidebar.multiselect("Country", sorted(full["Geography"].unique()),
                              default=sorted(full["Geography"].unique()))
genders = st.sidebar.multiselect("Gender", sorted(full["Gender"].unique()),
                                 default=sorted(full["Gender"].unique()))
ages = st.sidebar.multiselect("Age group", a.AGE_LABELS, default=a.AGE_LABELS)
credits = st.sidebar.multiselect("Credit score band", a.CREDIT_LABELS, default=a.CREDIT_LABELS)
tenures = st.sidebar.multiselect("Tenure group", a.TENURE_LABELS, default=a.TENURE_LABELS)
balances = st.sidebar.multiselect("Balance segment", a.BALANCE_LABELS, default=a.BALANCE_LABELS)
activity = st.sidebar.radio("Engagement", ["All", "Active only", "Inactive only"])
products = st.sidebar.multiselect("Number of products", sorted(full["NumOfProducts"].unique()),
                                  default=sorted(full["NumOfProducts"].unique()))

df = full[
    full["Geography"].isin(geos)
    & full["Gender"].isin(genders)
    & full["AgeGroup"].isin(ages)
    & full["CreditBand"].isin(credits)
    & full["TenureGroup"].isin(tenures)
    & full["BalanceSegment"].isin(balances)
    & full["NumOfProducts"].isin(products)
]
if activity == "Active only":
    df = df[df["IsActiveMember"] == 1]
elif activity == "Inactive only":
    df = df[df["IsActiveMember"] == 0]

st.sidebar.markdown("---")
st.sidebar.caption(f"{len(df):,} of {len(full):,} customers selected")

st.title("🏦 Customer Segmentation & Churn Analytics")
st.caption("European retail banking - France, Spain, Germany | Dataset: 10,000 customers (2025)")

if len(df) == 0:
    st.warning("No customers match the current filters. Widen the filters in the sidebar.")
    st.stop()

k = a.kpis(df, reference=full)


def rate_chart(table: pd.DataFrame, col: str, title: str, overall: float):
    """Bar chart of churn rate by segment with an overall reference line."""
    t = table.copy()
    t[col] = t[col].astype(str)
    order = t[col].tolist()
    bars = alt.Chart(t).mark_bar().encode(
        x=alt.X(f"{col}:N", sort=order, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ChurnRate:Q", title="Churn rate", axis=alt.Axis(format="%")),
        color=alt.condition(alt.datum.ChurnRate > overall, alt.value(RED), alt.value(BLUE)),
        tooltip=[alt.Tooltip(f"{col}:N"), alt.Tooltip("Customers:Q", format=","),
                 alt.Tooltip("Churned:Q", format=","), alt.Tooltip("ChurnRate:Q", format=".1%"),
                 alt.Tooltip("ShareOfChurn:Q", title="Share of all churn", format=".1%")],
    )
    labels = bars.mark_text(dy=-6).encode(text=alt.Text("ChurnRate:Q", format=".1%"),
                                          color=alt.value("#333"))
    rule = alt.Chart(pd.DataFrame({"y": [overall]})).mark_rule(strokeDash=[5, 4], color="black").encode(y="y:Q")
    return (bars + labels + rule).properties(title=title, height=280)


tab_sum, tab_geo, tab_age, tab_hv, tab_drill, tab_data = st.tabs(
    ["Overall summary", "Geography", "Age & tenure", "High-value explorer", "Drill-down", "Data & method"])

# --------------------------------------------------------------------------- #
# Tab 1: Overall summary + KPIs
# --------------------------------------------------------------------------- #
with tab_sum:
    full_rate = a.overall_churn(full)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Overall churn rate", f"{k['overall_churn']:.1%}",
              f"{(k['overall_churn'] - full_rate) * 100:+.1f} pts vs all customers", delta_color="inverse")
    c2.metric("High-value churn ratio", f"{k['high_value_churn']:.1%}"
              if k["high_value_customers"] else "n/a",
              help="Churn among customers in the top 25% of balances (dataset-wide threshold).")
    c3.metric("Engagement drop indicator", f"{k['engagement_drop']:.2f}x"
              if pd.notna(k["engagement_drop"]) else "n/a",
              help="Churn rate of inactive members divided by churn rate of active members.")
    c4.metric("Balance walked out", f"EUR {k['balance_lost'] / 1e6:,.1f}M",
              f"{k['balance_lost_share']:.1%} of balances", delta_color="off")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Customers in view", f"{k['customers']:,}")
    c6.metric("Churned customers", f"{k['churned']:,}")
    c7.metric("Inactive churn rate", f"{k['inactive_churn']:.1%}" if pd.notna(k["inactive_churn"]) else "n/a")
    c8.metric("Active churn rate", f"{k['active_churn']:.1%}" if pd.notna(k["active_churn"]) else "n/a")

    st.subheader("Geographic Risk Index")
    st.caption("Country churn rate divided by the overall churn rate of all customers. 1.00 = average; above 1 = elevated risk.")
    gcols = st.columns(len(k["geo_risk_index"]))
    for col, (geo, v) in zip(gcols, k["geo_risk_index"].items()):
        col.metric(geo, f"{v:.2f}", "Above average" if v > 1 else "Below average", delta_color="inverse"
                   if v > 1 else "normal")

    left, right = st.columns(2)
    with left:
        st.altair_chart(rate_chart(a.segment_churn(df, "NumOfProducts"), "NumOfProducts",
                                   "Churn by number of products", k["overall_churn"]), use_container_width=True)
    with right:
        st.altair_chart(rate_chart(a.segment_churn(df, "Gender"), "Gender",
                                   "Churn by gender", k["overall_churn"]), use_container_width=True)

    st.subheader("Churned vs retained - average profile")
    prof = a.churned_vs_retained(df).round(2) if df["Exited"].nunique() == 2 else None
    if prof is not None:
        st.dataframe(prof, use_container_width=True)
    else:
        st.info("The current filter contains only one customer status, so no comparison is possible.")

# --------------------------------------------------------------------------- #
# Tab 2: Geography
# --------------------------------------------------------------------------- #
with tab_geo:
    geo_tbl = a.segment_churn(df, "Geography")
    st.altair_chart(rate_chart(geo_tbl, "Geography", "Churn rate by country", k["overall_churn"]),
                    use_container_width=True)

    st.subheader("Churn contribution vs segment size")
    contrib = geo_tbl.melt(id_vars="Geography", value_vars=["ShareOfCustomers", "ShareOfChurn"],
                           var_name="Measure", value_name="Share")
    contrib["Measure"] = contrib["Measure"].map({"ShareOfCustomers": "Share of customers",
                                                 "ShareOfChurn": "Share of churners"})
    st.altair_chart(alt.Chart(contrib).mark_bar().encode(
        x=alt.X("Geography:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset="Measure:N",
        y=alt.Y("Share:Q", axis=alt.Axis(format="%")),
        color=alt.Color("Measure:N", scale=alt.Scale(range=["#a0aec0", RED])),
        tooltip=["Geography", "Measure", alt.Tooltip("Share:Q", format=".1%")]).properties(height=280),
        use_container_width=True)

    st.subheader("Country x age group (churn rate)")
    m = a.geography_age_matrix(df).reset_index().melt(id_vars="Geography", var_name="AgeGroup", value_name="ChurnRate")
    m["AgeGroup"] = m["AgeGroup"].astype(str)
    heat = alt.Chart(m).mark_rect().encode(
        x=alt.X("AgeGroup:N", sort=a.AGE_LABELS, title=None),
        y=alt.Y("Geography:N", title=None),
        color=alt.Color("ChurnRate:Q", scale=alt.Scale(scheme="reds"), legend=alt.Legend(format="%")),
        tooltip=["Geography", "AgeGroup", alt.Tooltip("ChurnRate:Q", format=".1%")])
    txt = heat.mark_text().encode(text=alt.Text("ChurnRate:Q", format=".0%"),
                                  color=alt.condition(alt.datum.ChurnRate > 0.35, alt.value("white"), alt.value("black")))
    st.altair_chart((heat + txt).properties(height=200), use_container_width=True)
    st.caption("Note: no customer in Germany has a zero balance, while about 48% of French and Spanish customers do. "
               "Compare countries with the Balance segment filter before drawing conclusions.")

# --------------------------------------------------------------------------- #
# Tab 3: Age & tenure
# --------------------------------------------------------------------------- #
with tab_age:
    c1, c2 = st.columns(2)
    with c1:
        st.altair_chart(rate_chart(a.segment_churn(df, "AgeGroup"), "AgeGroup", "Churn by age group",
                                   k["overall_churn"]), use_container_width=True)
    with c2:
        st.altair_chart(rate_chart(a.segment_churn(df, "TenureGroup"), "TenureGroup", "Churn by tenure group",
                                   k["overall_churn"]), use_container_width=True)
    c3, c4 = st.columns(2)
    with c3:
        st.altair_chart(rate_chart(a.segment_churn(df, "CreditBand"), "CreditBand", "Churn by credit score band",
                                   k["overall_churn"]), use_container_width=True)
    with c4:
        st.altair_chart(rate_chart(a.segment_churn(df, "BalanceSegment"), "BalanceSegment",
                                   "Churn by balance segment", k["overall_churn"]), use_container_width=True)

    st.subheader("Age x tenure (churn rate)")
    at = df.pivot_table(index="AgeGroup", columns="TenureGroup", values="Exited", aggfunc="mean",
                        observed=True).reset_index().melt(id_vars="AgeGroup", var_name="TenureGroup", value_name="ChurnRate")
    at["AgeGroup"] = at["AgeGroup"].astype(str)
    at["TenureGroup"] = at["TenureGroup"].astype(str)
    h2 = alt.Chart(at).mark_rect().encode(
        x=alt.X("TenureGroup:N", sort=a.TENURE_LABELS, title=None),
        y=alt.Y("AgeGroup:N", sort=a.AGE_LABELS, title=None),
        color=alt.Color("ChurnRate:Q", scale=alt.Scale(scheme="reds"), legend=alt.Legend(format="%")),
        tooltip=["AgeGroup", "TenureGroup", alt.Tooltip("ChurnRate:Q", format=".1%")])
    t2 = h2.mark_text().encode(text=alt.Text("ChurnRate:Q", format=".0%"),
                               color=alt.condition(alt.datum.ChurnRate > 0.35, alt.value("white"), alt.value("black")))
    st.altair_chart((h2 + t2).properties(height=240), use_container_width=True)

# --------------------------------------------------------------------------- #
# Tab 4: High-value explorer
# --------------------------------------------------------------------------- #
with tab_hv:
    q75 = full["Balance"].quantile(0.75)
    st.caption(f"High-value customers = balance of at least EUR {q75:,.0f} (top 25% of all customers).")
    thr = st.slider("Custom balance threshold (EUR)", 0, int(full["Balance"].max()), int(q75), step=5000)
    hv = df[df["Balance"] >= thr]
    rest = df[df["Balance"] < thr]
    if len(hv) == 0:
        st.info("No customers in the current view above this threshold.")
    else:
        h1, h2_, h3, h4 = st.columns(4)
        h1.metric("Customers above threshold", f"{len(hv):,}")
        h2_.metric("Churn rate (above)", f"{a.overall_churn(hv):.1%}")
        h3.metric("Churn rate (below)", f"{a.overall_churn(rest):.1%}" if len(rest) else "n/a")
        h4.metric("Balance at risk", f"EUR {hv.loc[hv['Exited'] == 1, 'Balance'].sum() / 1e6:,.1f}M")

        c1, c2 = st.columns(2)
        with c1:
            deciles = df.copy()
            deciles["BalanceBand"] = pd.qcut(deciles["Balance"].rank(method="first"), 10,
                                             labels=[f"D{i}" for i in range(1, 11)])
            d = deciles.groupby("BalanceBand", observed=True)["Exited"].mean().reset_index(name="ChurnRate")
            st.altair_chart(alt.Chart(d).mark_bar(color=BLUE).encode(
                x=alt.X("BalanceBand:N", sort=list(d["BalanceBand"]), title="Balance decile (D1 = lowest)"),
                y=alt.Y("ChurnRate:Q", axis=alt.Axis(format="%"), title="Churn rate"),
                tooltip=["BalanceBand", alt.Tooltip("ChurnRate:Q", format=".1%")]).properties(
                    title="Churn by balance decile", height=280), use_container_width=True)
        with c2:
            sample = df.sample(min(len(df), 2500), random_state=1)
            st.altair_chart(alt.Chart(sample).mark_circle(size=18, opacity=0.5).encode(
                x=alt.X("EstimatedSalary:Q", title="Estimated salary"),
                y=alt.Y("Balance:Q"),
                color=alt.Color("Status:N", scale=alt.Scale(domain=["Retained", "Churned"], range=[BLUE, RED])),
                tooltip=["Geography", "Age", "Balance", "EstimatedSalary", "Status"]).properties(
                    title="Salary vs balance (sample of up to 2,500)", height=280), use_container_width=True)

        st.subheader("High-value summary")
        summ = a.high_value_summary(df)
        summ_disp = summ.copy()
        summ_disp["ChurnRate"] = summ_disp["ChurnRate"].map("{:.1%}".format)
        for c in ["BalanceAtRisk", "AvgBalanceChurned", "AvgSalaryChurned"]:
            summ_disp[c] = summ_disp[c].map("{:,.0f}".format)
        st.dataframe(summ_disp, use_container_width=True, hide_index=True)

        st.subheader("Highest-balance customers who churned")
        top = (hv[hv["Exited"] == 1].sort_values("Balance", ascending=False)
               [["CustomerId", "Geography", "Gender", "Age", "Tenure", "Balance", "EstimatedSalary",
                 "NumOfProducts", "IsActiveMember"]].head(50))
        st.dataframe(top, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------- #
# Tab 5: Drill-down
# --------------------------------------------------------------------------- #
with tab_drill:
    st.write("Pick one or two dimensions to see churn for every combination (minimum group size applies).")
    dims = {v: k_ for k_, v in a.SEGMENT_COLUMNS.items()}
    d1, d2, d3 = st.columns(3)
    first = d1.selectbox("Dimension 1", list(dims), index=0)
    second = d2.selectbox("Dimension 2 (optional)", ["None"] + list(dims), index=2)
    min_n = d3.number_input("Minimum customers per group", 1, 1000, 50)
    cols = [dims[first]] + ([dims[second]] if second != "None" and second != first else [])
    res = a.top_risk_segments(df, cols, min_size=int(min_n))
    if res.empty:
        st.info("No groups meet the minimum size in the current view.")
    else:
        disp = res.copy()
        disp["ChurnRate"] = (disp["ChurnRate"] * 100).round(1)
        st.dataframe(disp.rename(columns={"ChurnRate": "Churn rate (%)"}), use_container_width=True, hide_index=True)
        st.download_button("Download this table (CSV)", res.to_csv(index=False).encode(),
                           "churn_drilldown.csv", "text/csv")

# --------------------------------------------------------------------------- #
# Tab 6: Data & method
# --------------------------------------------------------------------------- #
with tab_data:
    st.subheader("Data validation")
    st.dataframe(a.validate(a.load_raw()), use_container_width=True, hide_index=True)
    st.subheader("Segment definitions")
    st.markdown(
        "- **Age:** <30, 30-45, 46-60, 60+\n"
        "- **Credit score:** Low (<580), Medium (580-699), High (700+)\n"
        "- **Tenure:** New (0-2 yrs), Mid-term (3-6 yrs), Long-term (7+ yrs)\n"
        "- **Balance:** Zero, Low (at or below median of non-zero balances), High (above it)\n"
        "- **High-value:** top 25% of balances across all customers\n"
        "- **Geographic Risk Index:** country churn rate / overall churn rate\n"
        "- **Engagement Drop Indicator:** inactive churn rate / active churn rate")
    st.download_button("Download filtered data (CSV)",
                       df.drop(columns=["BalanceToSalary"]).to_csv(index=False).encode(),
                       "filtered_customers.csv", "text/csv")
