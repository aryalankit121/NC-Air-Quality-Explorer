"""North Carolina Air Quality Explorer | EPA daily county AQI, 2025."""
from pathlib import Path
import calendar

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="NC Air Quality Explorer", page_icon="🌿", layout="wide")

COLORS = {
    "Good": "#249B80",
    "Moderate": "#E8B84A",
    "Unhealthy for Sensitive Groups": "#ED8849",
    "Unhealthy": "#D95D5D",
    "Very Unhealthy": "#A46DC0",
    "Hazardous": "#784B70",
}
MONTHS = list(calendar.month_abbr)[1:]

st.markdown("""
<style>
.block-container {max-width: 1320px; padding-top: 1.8rem; padding-bottom: 3rem;}
[data-testid="stMetric"] {border: 1px solid rgba(120,150,140,.25); border-radius: 14px; padding: 16px; background: rgba(40,130,100,.10);}
[data-testid="stMetricLabel"] {font-weight: 600;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap: .65rem;}
.section-note {font-size: .94rem; opacity: .84; margin-bottom: 1rem;}
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_data():
    root = Path(__file__).resolve().parent
    # Prefer the filename required by the assignment; accept the notebook export too.
    candidates = [root / "dashboard_data.csv", root / "nc_aqi_dashboard_2025.csv"]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        raise FileNotFoundError("Add dashboard_data.csv beside app.py in your GitHub repository.")
    data = pd.read_csv(path, parse_dates=["Date"])
    required = {"Date", "County", "AQI", "AQI_Category", "Defining_Pollutant", "Sites_Reporting"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Required columns missing: {', '.join(sorted(missing))}")
    data = data.dropna(subset=["Date", "County", "AQI", "AQI_Category", "Defining_Pollutant"]).copy()
    data["AQI"] = pd.to_numeric(data["AQI"], errors="coerce")
    data = data.dropna(subset=["AQI"])
    data["Month"] = data["Date"].dt.month
    return data


try:
    df = load_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not load the dashboard data: {error}")
    st.stop()

if df.empty:
    st.error("The dashboard dataset has no usable records.")
    st.stop()

all_counties = sorted(df["County"].unique().tolist())
all_pollutants = sorted(df["Defining_Pollutant"].unique().tolist())
all_categories = [c for c in COLORS if c in df["AQI_Category"].unique()]
min_date, max_date = df["Date"].min().date(), df["Date"].max().date()

with st.sidebar:
    st.header("Explore the data")
    st.caption("Adjust filters to update every metric and chart.")
    county_mode = st.radio("Geographic selection", ["All reporting counties", "Choose counties"], horizontal=False)
    if county_mode == "Choose counties":
        counties = st.multiselect("Select counties", all_counties, default=["Mecklenburg", "Wake", "Catawba"] if all(x in all_counties for x in ["Mecklenburg", "Wake", "Catawba"]) else all_counties[:3])
    else:
        counties = all_counties
        st.caption(f"Using all {len(all_counties)} reporting counties")

    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    selected_pollutants = st.multiselect("Defining pollutants", all_pollutants, default=all_pollutants,
        help="Filters to days when a pollutant defined the reported AQI; not its concentration.")
    selected_categories = st.multiselect("AQI categories", all_categories, default=all_categories,
        help="Choose which AQI health categories to include in all calculations.")
    st.divider()
    st.subheader("Chart settings")
    min_days = st.slider("Minimum reported days for county ranking", 1, 365, 300,
        help="Only affects chart 1. Short date ranges may require lowering this value.")
    top_n = st.slider("Counties shown in comparison charts", 3, 20, 12)
    st.caption("Source: EPA AirData, Daily AQI by County (2025).")

st.title("🌿 North Carolina Air Quality Explorer")
st.markdown("**Where does air quality differ—and when?** Explore reported EPA county-level AQI through geographic, seasonal, and health-category comparisons.")
st.caption("Designed for North Carolina residents, students, environmental organizations, and local decision-makers. Only counties with EPA reports appear; AQI is not a measure of individual exposure.")

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date in the sidebar.")
    st.stop()
start_date, end_date = date_range
if not counties or not selected_pollutants or not selected_categories:
    st.info("Select at least one county, pollutant, and AQI category to explore the data.")
    st.stop()

filtered = df.loc[
    df["County"].isin(counties)
    & df["Date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
    & df["Defining_Pollutant"].isin(selected_pollutants)
    & df["AQI_Category"].isin(selected_categories)
].copy()

if filtered.empty:
    st.warning("No county-day records match your filters. Widen the date range or include more counties, pollutants, or categories.")
    st.stop()

reported = len(filtered)
above_100 = int(filtered["AQI"].gt(100).sum())
metrics = st.columns(4)
metrics[0].metric("Average reported AQI", f"{filtered['AQI'].mean():.1f}", help="Mean across selected county-day records; not a population-weighted average.")
metrics[1].metric("Reported county-days", f"{reported:,}", help="One county's AQI on one reported date counts as one county-day.")
metrics[2].metric("Counties represented", f"{filtered['County'].nunique()}")
metrics[3].metric("County-days AQI > 100", f"{above_100:,}", help=f"{above_100 / reported:.2%} of selected county-days")
st.caption(f"**Current view:** {start_date:%b %d, %Y} – {end_date:%b %d, %Y} · {filtered['County'].nunique()} counties · {len(selected_pollutants)} defining pollutants · {len(selected_categories)} AQI categories. All findings below reflect these filters.")

# Consistent, readable chart theme without forcing a light/dark page theme.
chart_layout = dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(size=13), margin=dict(l=10, r=20, t=45, b=40))

st.divider()
st.subheader("01  /  County comparison — typical vs. higher-end AQI")
st.markdown("Compare each county's **mean AQI** with its **90th percentile (P90)**. A wider gap suggests higher-end reported days are farther above the county's average. The ranking includes only counties meeting the minimum-days threshold.")
county_stats = (filtered.groupby("County")["AQI"].agg(Mean="mean", P90=lambda x: x.quantile(.9), Days="size")
                .sort_values("Mean", ascending=False))
eligible = county_stats[county_stats["Days"] >= min_days].head(top_n)
if eligible.empty:
    st.info("No counties meet the minimum reported-days threshold with these filters. Lower the threshold to display chart 1.")
else:
    ranked = eligible.sort_values("Mean")
    fig = go.Figure()
    for county, row in ranked.iterrows():
        fig.add_trace(go.Scatter(x=[row.Mean, row.P90], y=[county, county], mode="lines",
            line=dict(color="#93A8A2", width=4), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=ranked.Mean, y=ranked.index, mode="markers", name="Mean AQI",
        marker=dict(color="#24B4A5", size=12), customdata=ranked.Days,
        hovertemplate="%{y}<br>Mean AQI: %{x:.1f}<br>Reported days: %{customdata}<extra></extra>"))
    fig.add_trace(go.Scatter(x=ranked.P90, y=ranked.index, mode="markers", name="90th percentile",
        marker=dict(color="#F4A340", size=12, symbol="diamond"), customdata=ranked.Days,
        hovertemplate="%{y}<br>P90 AQI: %{x:.1f}<br>Reported days: %{customdata}<extra></extra>"))
    fig.update_layout(**chart_layout, height=max(390, 34 * len(ranked) + 135),
        xaxis_title="AQI (higher = more polluted)", yaxis_title=None,
        legend=dict(orientation="h", y=1.12))
    fig.update_xaxes(showgrid=True, gridcolor="rgba(150,150,150,.15)")
    st.plotly_chart(fig, use_container_width=True)
    leader = eligible.iloc[0]
    st.markdown(f"**What stands out:** Among the eligible counties in this selection, **{eligible.index[0]}** has the highest mean AQI (**{leader.Mean:.1f}**) across **{int(leader.Days)} reported days**. The P90 marker highlights the higher end of its reported values—not an EPA health threshold.")

st.divider()
st.subheader("02  /  Seasonal patterns — county × month heatmap")
st.markdown("Each tile represents the **average reported AQI** for one county in one month. Hover to see the number of reports behind the average; empty cells indicate no matching records.")
# Select most frequently reporting counties, not only counties meeting chart 1's threshold.
heat_counties = county_stats.sort_values(["Days", "Mean"], ascending=[False, False]).head(top_n).index.tolist()
monthly = (filtered[filtered["County"].isin(heat_counties)]
           .groupby(["County", "Month"])["AQI"].agg(Mean="mean", Days="size").reset_index())
heat = monthly.pivot(index="County", columns="Month", values="Mean").reindex(index=heat_counties, columns=range(1, 13))
heat_days = monthly.pivot(index="County", columns="Month", values="Days").reindex(index=heat_counties, columns=range(1, 13))
fig2 = go.Figure(go.Heatmap(z=heat.to_numpy(), x=MONTHS, y=heat.index.tolist(),
    customdata=heat_days.to_numpy(), colorscale=[[0, "#D5F1E0"], [.35, "#9CD2B3"], [.65, "#F0C46B"], [1, "#D45C47"]],
    colorbar=dict(title="Mean AQI"), hoverongaps=False,
    hovertemplate="%{y} · %{x}<br>Mean AQI: %{z:.1f}<br>Reported days: %{customdata}<extra></extra>"))
fig2.update_layout(**chart_layout, height=max(390, 33 * len(heat_counties) + 115), xaxis_title="Month", yaxis_title=None)
fig2.update_yaxes(autorange="reversed")
st.plotly_chart(fig2, use_container_width=True)
monthly_mean = filtered.groupby("Month")["AQI"].mean()
peak_month = int(monthly_mean.idxmax())
st.markdown(f"**What stands out:** **{calendar.month_name[peak_month]}** has the highest mean AQI (**{monthly_mean.max():.1f}**) among the selected records. This is a descriptive comparison: county reporting coverage and selected filters affect the averages.")

st.divider()
st.subheader("03  /  AQI categories — how the monthly mix changes")
st.markdown("These **100% stacked bars** show the share of reported county-days in each health category. Hover over a segment to see its exact count. Months with no matching reports are left blank.")
category_counts = pd.crosstab(filtered["Month"], filtered["AQI_Category"]).reindex(index=range(1, 13), columns=list(COLORS), fill_value=0)
monthly_totals = category_counts.sum(axis=1)
category_pct = category_counts.div(monthly_totals.replace(0, np.nan), axis=0).mul(100)
fig3 = go.Figure()
for category, color in COLORS.items():
    if category_counts[category].sum() == 0:
        continue
    fig3.add_trace(go.Bar(x=MONTHS, y=category_pct[category], name=category, marker_color=color,
        customdata=category_counts[category],
        hovertemplate=f"%{{x}} · {category}<br>Share: %{{y:.1f}}%<br>County-days: %{{customdata}}<extra></extra>"))
for month, count in filtered.assign(Above100=filtered.AQI.gt(100)).groupby("Month")["Above100"].sum().items():
    if count:
        fig3.add_annotation(x=MONTHS[month - 1], y=104, text=f"{int(count)} >100", showarrow=False,
                            font=dict(color="#F1A36A", size=11))
fig3.update_layout(**chart_layout, barmode="stack", height=470,
    yaxis=dict(title="Share of reported county-days (%)", range=[0, 110]), xaxis_title="Month",
    legend=dict(orientation="h", y=-.23))
st.plotly_chart(fig3, use_container_width=True)
most_common = filtered["AQI_Category"].value_counts()
st.markdown(f"**What stands out:** **{most_common.index[0]}** is the most common category (**{most_common.iloc[0] / reported:.1%}** of selected county-days). **{above_100}** selected county-days had AQI above 100. These are county reports, not unique dates statewide.")

with st.expander("About the data, limitations, and filtered records"):
    st.markdown("""
**Source:** [EPA AirData — Daily AQI by County, 2025](https://aqs.epa.gov/aqsweb/airdata/download_files.html).

**Coverage:** Only 34 North Carolina counties have records in this dataset, not all 100. Reporting frequency differs by county. Each row is one reported county-day, not one unique statewide day.

**Interpretation:** AQI is an index, not pollutant concentration. A *defining pollutant* is the pollutant driving that day's reported AQI; selecting one does not mean other pollutants were absent. P90 is a descriptive statistic, not an EPA category threshold. Filtering by AQI category changes the population of records used for all metrics and charts.

**Limits:** County-day averages are not population-weighted, and this dashboard cannot establish the causes of pollution or individual health outcomes. Comparing counties with unequal monitoring coverage requires care.
    """)
    st.dataframe(filtered[["Date", "County", "AQI", "AQI_Category", "Defining_Pollutant", "Sites_Reporting"]].sort_values(["Date", "County"]),
                 use_container_width=True, hide_index=True)
    st.download_button("Download selected records as CSV", data=filtered.to_csv(index=False).encode("utf-8"),
                       file_name="nc_aqi_filtered.csv", mime="text/csv")

st.caption("Educational dashboard · EPA AirData 2025 · North Carolina counties with available reports")
