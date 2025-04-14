import streamlit as st
import pandas as pd
import os
import io
import altair as alt
from datetime import date

st.set_page_config(page_title="AirLog Buddy Pro", page_icon="🌿")
st.title("🌬️ AirLog Buddy Pro")
st.subheader("Daily Air Pollution Logger & Visualizer")

DATA_FILE = "airlog_data_cleaned.csv"

# ✅ CPCB 24-hour standards
standards = {
    "PM10": 100,
    "PM2.5": 60,
    "SO2": 80,
    "NOx": 80,
    "O3": 180
}

# 📝 Form for new entry
with st.form("data_entry_form"):
    log_date_str = st.text_input("📅 Enter Date (DD-MM-YYYY)", value=date.today().strftime("%d-%m-%Y"))
    try:
        log_date = pd.to_datetime(log_date_str, format="%d-%m-%Y").date()
    except ValueError:
        st.error("Invalid date format. Use DD-MM-YYYY")
        log_date = None

    location = st.text_input("📍 Location / Station / Lab Name")
    pm10 = st.number_input("PM10 (µg/m³)", min_value=0.0)
    pm25 = st.number_input("PM2.5 (µg/m³)", min_value=0.0)
    so2 = st.number_input("SO₂ (µg/m³)", min_value=0.0)
    nox = st.number_input("NOₓ (µg/m³)", min_value=0.0)
    o3 = st.number_input("O₃ (µg/m³)", min_value=0.0)
    submit = st.form_submit_button("🔍 Analyze & Save")

# ✅ Save to CSV
if submit and log_date:
    entry = {
        "Date": log_date,
        "Location": location,
        "PM10": pm10,
        "PM2.5": pm25,
        "SO2": so2,
        "NOx": nox,
        "O3": o3
    }

    if os.path.exists(DATA_FILE):
        df_existing = pd.read_csv(DATA_FILE)
        df = pd.concat([df_existing, pd.DataFrame([entry])], ignore_index=True)
    else:
        df = pd.DataFrame([entry])

    df.to_csv(DATA_FILE, index=False)
    st.success("✅ Data saved successfully!")

    st.markdown("### 📊 Analysis Results")
    for param, value in entry.items():
        if param in standards:
            if value <= standards[param]:
                st.success(f"{param}: {value} µg/m³ ✅ Safe")
            else:
                st.error(f"{param}: {value} µg/m³ 🚨 Above CPCB Limit ({standards[param]})")

# 📥 Load and clean CSV
df = pd.read_csv(DATA_FILE)
df.columns = df.columns.str.strip()

# ✅ Drop PM25 if both PM25 and PM2.5 exist
if "PM25" in df.columns and "PM2.5" in df.columns:
    df.drop(columns=["PM25"], inplace=True)
elif "PM25" in df.columns and "PM2.5" not in df.columns:
    df.rename(columns={"PM25": "PM2.5"}, inplace=True)

df = df.loc[:, ~df.columns.duplicated()]
df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date

# 📍 Filter by location
locations = ["All"] + sorted(df["Location"].dropna().unique())
selected_location = st.selectbox("📍 Filter by location", locations)
filtered_data = df if selected_location == "All" else df[df["Location"] == selected_location]

# 📤 Export to CSV
if not filtered_data.empty:
    csv_data = io.StringIO()
    filtered_data.to_csv(csv_data, index=False)
    st.download_button(
        label="📥 Download Filtered Data (CSV)",
        data=csv_data.getvalue(),
        file_name=f"{selected_location}_AirLog.csv",
        mime="text/csv"
    )

# 📊 Pollutant-wise chart
pollutant = st.selectbox("Select pollutant to visualize", options=["PM10", "PM2.5", "SO2", "NOx", "O3"])

# Optional preview (for debugging)
st.markdown("#### Filtered Data Preview")
st.dataframe(filtered_data[["Date", pollutant]])

if not filtered_data.empty and pollutant in filtered_data.columns:
    chart_data = filtered_data[["Date", pollutant]].dropna()
    chart_data = chart_data.sort_values("Date")

    def get_color(val):
        if val <= 0.5 * standards[pollutant]:
            return "green"
        elif val <= standards[pollutant]:
            return "yellow"
        return "red"

    chart_data["color"] = chart_data[pollutant].apply(get_color)

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y(f"{pollutant}:Q", title=f"{pollutant} (µg/m³)"),
        color=alt.Color("color:N", legend=None),
        tooltip=["Date", pollutant]
    ).properties(width=700, height=400, title=f"{pollutant} Levels Over Time")

    st.altair_chart(chart, use_container_width=True)

# 📊 Multi-Pollutant Comparison (Side-by-side)
st.subheader("📊 Multi-Pollutant Comparison")

if not filtered_data.empty:
    melted = filtered_data.melt(
        id_vars=["Date", "Location"],
        value_vars=["PM10", "PM2.5", "SO2", "NOx", "O3"],
        var_name="Pollutant",
        value_name="Value"
    )

    summary = melted.groupby(["Date", "Pollutant"], as_index=False)["Value"].max()

    comparison_chart = alt.Chart(summary).mark_bar().encode(
        x=alt.X("Date:T", title="Date"),
        y=alt.Y("Value:Q", title="Concentration (µg/m³)"),
        color=alt.Color("Pollutant:N", title="Pollutant"),
        column=alt.Column("Pollutant:N", spacing=10)
    ).resolve_scale(y='independent').properties(
        width=130,
        height=400,
        title="Multi-Pollutant Trends"
    )

    st.altair_chart(comparison_chart, use_container_width=True)
else:
    st.info("No data available for multi-pollutant chart.")
