# 🌿 North Carolina Air Quality Explorer (2025)

An interactive Streamlit dashboard exploring reported daily Air Quality Index (AQI) patterns across North Carolina counties in 2025.

**Published Streamlit application:** https://nc-air-quality-explorer.streamlit.app/

## Project and audience

The dashboard is designed for North Carolina residents, students, environmental groups, and local decision-makers who want to explore differences in reported air quality without having to work directly with the raw EPA files. It provides interactive geographic, seasonal, and AQI-category views.

## Dataset and source

- **Source:** U.S. Environmental Protection Agency (EPA), [AirData Daily AQI by County (2025)](https://aqs.epa.gov/aqsweb/airdata/download_files.html)
- **Documentation:** [EPA AirData reports](https://www.epa.gov/outdoor-air-quality-data/about-airdata-reports)
- **Original file:** `daily_aqi_by_county_2025.csv` (national file; not included in this repository)
- **Dashboard file:** `dashboard_data.csv`, prepared in the Deliverable 2 pandas notebook
- **Scope:** 10,536 reported county-day records from 34 reporting North Carolina counties, covering January–December 2025
- **Fields used:** date, county, AQI, AQI category, defining pollutant, reporting-site count, and derived date/AQI fields

The dashboard CSV is the cleaned and reduced output of the analysis notebook. Only this necessary dataset is deployed. The data are publicly released government environmental observations; no personal records are used.

## Research questions and visualizations

1. **Which reporting counties have higher typical AQI, and do their higher-end days differ?** A dumbbell chart compares mean AQI with the 90th percentile, displaying reporting-day counts in hover details. The default county ranking requires at least 300 reported days; this is an analysis choice, not an EPA standard.
2. **How do monthly AQI patterns differ among counties?** A county-by-month heatmap compares monthly average AQI across selected counties.
3. **How often are reported county-days classified as Good, Moderate, or higher AQI categories, and how does this vary by month?** A 100% stacked bar chart shows the monthly category composition and flags rare reports above AQI 100.

## Interactive features

- County multiselect, date-range picker, and defining-pollutant multiselect
- Minimum reporting-day threshold for county rankings and number of displayed counties
- Four dynamic metrics: average reported AQI, reported county-days, reporting counties, and county-days above AQI 100
- Interactive Plotly charts, context-specific observations, and filtered-record CSV download

All metrics and charts are recalculated from the selected data. The reporting-days threshold affects only the county ranking; the other filters affect all charts and metrics.

## Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit application |
| `dashboard_data.csv` | Prepared North Carolina AQI records for deployment |
| `requirements.txt` | Python dependencies |
| `README.md` | Project documentation |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Interpretation notes and limitations

- Only 34 of North Carolina's 100 counties have records in this EPA file. **Missing counties are not equivalent to good air quality.**
- County monitoring coverage varies. Daily county AQI reports do not describe every location or person's exposure.
- A *county-day* is one county's reported AQI on a date, not a unique statewide calendar day.
- The 90th percentile describes higher-end reported days and is not a regulatory threshold.
- A defining pollutant is not a pollutant concentration or evidence of a pollution source.
- Trends are descriptive and do not establish causation or health outcomes.

## Generative AI use

AI tools assisted with boilerplate structuring, debugging, and drafting this documentation. The project design, dataset curation, code validation, and interpretations are my own.
