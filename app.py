"""North Carolina Air Quality Explorer — EPA daily county AQI, 2025."""
from pathlib import Path
import calendar

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="NC Air Quality Explorer", page_icon="🌿", layout="wide")

COLORS = {
    "Good": "#209875", "Moderate": "#E7B746",
    "Unhealthy for Sensitive Groups": "#E97843", "Unhealthy": "#D54D4D",
    "Very Unhealthy": "#9954A1", "Hazardous": "#6C334B",
}
CATEGORY_ORDER = list(COLORS)
MONTHS = list(calendar.month_abbr)[1:]

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1300px;}
[data-testid="stMetric"] {background: #F3F8F6; border: 1px solid #DDECE5; border-radius: 12px; padding: 14px;}
@media (prefers-color-scheme: dark) {
  [data-testid="stMetric"] {background: #17332B; border-color: #315B4E;}
}
</style>
""", unsafe_allow_html=True)

@st.cache_data

def load_data():
    file = Path(__file__).parent / "nc_aqi_dashboard_2025.csv"
    data = pd.read_csv(file, parse_dates=["Date"])
    required = {"Date", "County", "AQI", "AQI_Category", "Defining_Pollutant", "Sites_Reporting"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Dashboard CSV missing columns: {sorted(missing)}")
    data["Month"] = data["Date"].dt.month
    return data

try:
    df = load_data()
except (FileNotFoundError, ValueError) as exc:
    st.error(f"Unable to load nc_aqi_dashboard_2025.csv: {exc}")
    st.stop()

st.title("🌿 North Carolina Air Quality Explorer")
st.markdown("**Where does reported air quality differ—and when?** Explore EPA daily county AQI reports from 2025 through geographic, seasonal, and health-category views.")
st.caption("For North Carolina residents, environmental groups, students, and local decision-makers. Only counties with EPA reports are represented; these data do not measure everyone's personal exposure.")

with st.sidebar:
    st.header("Explore the data")
    all_counties = sorted(df["County"].unique().tolist())
    counties = st.multiselect("Counties", all_counties, default=all_counties,
                              help="Select one or more of the reporting counties.")
    min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
    date_range = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    pollutants = sorted(df["Defining_Pollutant"].dropna().unique().tolist())
    selected_pollutants = st.multiselect("Defining pollutant", pollutants, default=pollutants,
                                         help="The pollutant that defined the reported AQI, not its measured concentration.")
    st.divider()
    min_days = st.slider("Minimum reported days for county ranking", min_value=1, max_value=365,
                         value=300, step=1, help="Counties below this threshold are excluded only from the dumbbell ranking, not other charts or metrics.")
    top_n = st.slider("Counties in comparison charts", 3, 20, 12)
    st.caption("Filters apply to all metrics and charts. The minimum-days threshold applies only to the county ranking.")

if not counties or not selected_pollutants:
    st.info("Choose at least one county and one defining pollutant in the sidebar.")
    st.stop()
if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Choose both the start and end dates to continue.")
    st.stop()
start_date, end_date = date_range
if start_date > end_date:
    st.warning("Start date must be before end date.")
    st.stop()

filtered = df.loc[
    df["County"].isin(counties)
    & df["Date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
    & df["Defining_Pollutant"].isin(selected_pollutants)
].copy()
if filtered.empty:
    st.warning("No EPA county-day records match these filters. Try expanding your selection.")
    st.stop()

reported_days = len(filtered)  # Each row is one reported county-day.
above_100 = int((filtered["AQI"] > 100).sum())
metric_cols = st.columns(4)
metric_cols[0].metric("Average reported AQI", f"{filtered['AQI'].mean():.1f}")
metric_cols[1].metric("Reported county-days", f"{reported_days:,}")
metric_cols[2].metric("County coverage", f"{filtered['County'].nunique()} counties")
metric_cols[3].metric("County-days AQI > 100", f"{above_100:,}", help=f"{above_100/reported_days:.2%} of selected reported county-days")
st.caption(f"Viewing **{start_date:%b %d, %Y}–{end_date:%b %d, %Y}** · {filtered['County'].nunique()} reporting counties · {len(selected_pollutants)} selected defining pollutants. A 'county-day' is one county's reported AQI on one date.")

st.divider()
st.subheader("01 / Counties — typical vs. higher-end AQI")
st.markdown("The **mean** describes typical reported AQI; the **90th percentile (P90)** reveals the higher end of a county's reported-day distribution. Only counties meeting the selected minimum-days threshold appear in this ranking.")

county_stats = (filtered.groupby("County")["AQI"]
                .agg(Mean="mean", P90=lambda s: s.quantile(.9), Days="count")
                .sort_values("Mean", ascending=False))
eligible = county_stats.loc[county_stats["Days"] >= min_days].head(top_n)
if eligible.empty:
    st.info("No counties meet the minimum reporting-days threshold for this filtered selection. Lower the threshold in the sidebar to see a ranking.")
else:
    ranked = eligible.sort_values("Mean")
    fig1 = go.Figure()
    for county, vals in ranked.iterrows():
        fig1.add_trace(go.Scatter(x=[vals["Mean"], vals["P90"]], y=[county, county], mode="lines",
                                  line=dict(color="#A8B9B4", width=4), showlegend=False, hoverinfo="skip"))
    fig1.add_trace(go.Scatter(x=ranked["Mean"], y=ranked.index, mode="markers", name="Mean AQI",
                              marker=dict(size=12, color="#198F86"), customdata=ranked["Days"],
                              hovertemplate="%{y}<br>Mean AQI: %{x:.1f}<br>Reported days: %{customdata}<extra></extra>"))
    fig1.add_trace(go.Scatter(x=ranked["P90"], y=ranked.index, mode="markers", name="90th percentile",
                              marker=dict(size=12, color="#E89A3D", symbol="diamond"), customdata=ranked["Days"],
                              hovertemplate="%{y}<br>P90 AQI: %{x:.1f}<br>Reported days: %{customdata}<extra></extra>"))
    fig1.update_layout(height=max(370, 32 * len(ranked) + 130), xaxis_title="AQI (higher = more polluted)",
                       yaxis_title=None, legend=dict(orientation="h", y=1.12), margin=dict(l=10, r=15, t=65, b=25),
                       hovermode="closest")
    st.plotly_chart(fig1, use_container_width=True)
    leader = eligible.iloc[0]
    st.caption(f"**What stands out:** Among eligible selected counties, **{eligible.index[0]}** has the highest mean AQI ({leader['Mean']:.1f}) across {int(leader['Days'])} reported days. Compare the gap to P90 to see how higher-end days differ from the mean. This is not a ranking of all 100 NC counties.")

st.divider()
st.subheader("02 / Seasons — county × month heatmap")
st.markdown("Each tile shows **mean reported AQI for a county during a month**. Blank tiles mean there are no records for that county-month under the current filters.")
# Use leading counties by count so heatmap remains useful when ranking threshold is restrictive.
heat_counties = (eligible.index.tolist() if not eligible.empty else
                 county_stats.head(top_n).index.tolist())
monthly = (filtered.loc[filtered["County"].isin(heat_counties)]
           .groupby(["County", "Month"])["AQI"].agg(Mean="mean", Days="count").reset_index())
heat = monthly.pivot(index="County", columns="Month", values="Mean").reindex(index=heat_counties, columns=range(1, 13))
heat_days = monthly.pivot(index="County", columns="Month", values="Days").reindex(index=heat_counties, columns=range(1, 13))
fig2 = go.Figure(go.Heatmap(z=heat.values, x=MONTHS, y=heat.index.tolist(),
                            colorscale=[[0, "#E5F4E9"], [0.35, "#A6D9B2"], [0.65, "#F2C46A"], [1, "#D65D45"]],
                            customdata=heat_days.values, colorbar=dict(title="Mean AQI"),
                            hovertemplate="%{y} · %{x}<br>Mean AQI: %{z:.1f}<br>Reported days: %{customdata}<extra></extra>",
                            hoverongaps=False))
fig2.update_layout(height=max(370, 30 * len(heat_counties) + 130), xaxis_title="Month", yaxis_title=None,
                   margin=dict(l=10, r=15, t=15, b=20))
fig2.update_yaxes(autorange="reversed")
st.plotly_chart(fig2, use_container_width=True)
if monthly.empty:
    st.caption("No monthly values available for this selection.")
else:
    month_summary = filtered.groupby("Month")["AQI"].mean()
    high_month = int(month_summary.idxmax())
    st.caption(f"**What stands out:** Across the selected records, **{calendar.month_name[high_month]}** has the highest monthly mean AQI ({month_summary.max():.1f}). Monthly averages depend on which counties and days reported data.")

st.divider()
st.subheader("03 / Health categories — how the mix changes by month")
st.markdown("Each month's bar totals **100% of reported county-days** for that month, making Good and Moderate shares easier to compare. The annotations count records with AQI above 100.")
category_counts = pd.crosstab(filtered["Month"], filtered["AQI_Category"]).reindex(index=range(1, 13), columns=CATEGORY_ORDER, fill_value=0)
monthly_totals = category_counts.sum(axis=1)
category_pct = category_counts.div(monthly_totals.replace(0, np.nan), axis=0).mul(100).fillna(0)
fig3 = go.Figure()
for category in CATEGORY_ORDER:
    if category_counts[category].sum() == 0:
        continue
    fig3.add_trace(go.Bar(x=MONTHS, y=category_pct[category], name=category,
                          marker_color=COLORS[category], customdata=category_counts[category],
                          hovertemplate=f"%{{x}} · {category}<br>%{{y:.1f}}%<br>%{{customdata}} county-days<extra></extra>"))
monthly_high = filtered.assign(Above100=filtered["AQI"] > 100).groupby("Month")["Above100"].sum()
for month, count in monthly_high.items():
    if count > 0:
        fig3.add_annotation(x=MONTHS[int(month)-1], y=101, text=f"{int(count)} >100", showarrow=False,
                            font=dict(size=11, color="#A84B37"))
fig3.update_layout(barmode="stack", height=430, yaxis=dict(title="Share of reported county-days (%)", range=[0, 110]),
                   xaxis_title="Month", legend=dict(orientation="h", y=-0.23), margin=dict(l=10, r=10, t=25, b=65))
st.plotly_chart(fig3, use_container_width=True)
category_summary = filtered["AQI_Category"].value_counts()
st.caption(f"**What stands out:** **{category_summary.idxmax()}** is the most common AQI category in the selected records ({category_summary.max()/len(filtered):.1%}). There are **{above_100}** county-days above AQI 100. These are reports, not unique days statewide.")

with st.expander("Data details, limitations, and selected records"):
    st.markdown("""
    **Source:** [EPA AirData — Download Files](https://aqs.epa.gov/aqsweb/airdata/download_files.html), *Daily AQI by County, 2025*.

    **Scope:** The underlying dataset includes 34 North Carolina counties with at least one report; it does **not** cover all 100 counties. Counties have unequal numbers of reported days. A county-day is one reported AQI for a county on a date.

    **Interpretation:** AQI is an index, not pollutant concentration. The defining pollutant is the pollutant driving the daily reported AQI, not a measure of pollutant emissions. The 90th percentile is descriptive, not an EPA threshold. Filtering by defining pollutant restricts the analysis to the county-days when that pollutant defined AQI, not all days that pollutant was present.

    **Metrics:** Average AQI and percentages are calculated from the currently filtered county-day records. Results may shift when different counties report on different dates. This dashboard is descriptive and does not establish health outcomes or pollution causes.
    """)
    st.dataframe(filtered[["Date", "County", "AQI", "AQI_Category", "Defining_Pollutant", "Sites_Reporting"]].sort_values(["Date", "County"]),
                 use_container_width=True, hide_index=True)
    st.download_button("Download filtered records", data=filtered.to_csv(index=False).encode("utf-8"),
                       file_name="nc_aqi_filtered.csv", mime="text/csv")

st.caption("Built from the EPA 2025 Daily AQI by County dataset · Educational analysis · Data source: U.S. EPA")
