import streamlit as st
import pandas as pd
import plotly.express as px

# PAGE CONFIGURATION
st.set_page_config(
    page_title="TerraSpace Analog Explorer",
    page_icon="🌍",
    layout="wide"
)

# HEADER
st.title("🌍 TerraSpace Analog Explorer")
st.subheader("Exploring Earth Analog Environments for Space Exploration")

st.markdown("""
Welcome to TerraSpace Analog Explorer!

This platform helps explore and compare Earth environments
that may provide useful analogs for understanding planetary
exploration and future human missions.

⚠️ DEMO MODE: All values currently displayed are illustrative,
not actual NASA measurements.
""")

st.divider()

# SIDEBAR
st.sidebar.title("🛰️ Explorer Controls")

selected_region = st.sidebar.selectbox(
    "Select an Analog Environment",
    ["All Regions", "Desert", "Arctic", "Volcanic"]
)

st.sidebar.info(
    "Demo version using illustrative values. "
    "NASA datasets will be integrated when available."
)

# ILLUSTRATIVE DATA
data = {
    "Environment": [
        "Atacama Desert",
        "Antarctica",
        "Hawaii Volcanic Region",
        "Arctic Tundra"
    ],
    "Temperature (°C)": [-5, -45, 15, -20],
    "Pressure (kPa)": [75, 65, 90, 80],
    "Radiation Index": [8, 6, 5, 4],
    "Water Availability (%)": [10, 15, 45, 30],
    "Analog Score": [92, 85, 78, 82]
}

df = pd.DataFrame(data)

# FILTER DATA
if selected_region == "Desert":
    filtered_df = df[df["Environment"] == "Atacama Desert"]
elif selected_region == "Arctic":
    filtered_df = df[df["Environment"].isin(
        ["Antarctica", "Arctic Tundra"]
    )]
elif selected_region == "Volcanic":
    filtered_df = df[df["Environment"] == "Hawaii Volcanic Region"]
else:
    filtered_df = df

# KEY METRICS
st.header("📊 Environment Overview")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Environments",
    len(filtered_df)
)

col2.metric(
    "Average Analog Score",
    f"{filtered_df['Analog Score'].mean():.1f}/100"
)

col3.metric(
    "Average Temperature",
    f"{filtered_df['Temperature (°C)'].mean():.1f} °C"
)

st.divider()

# DATA TABLE
st.header("🌎 Analog Environment Comparison")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True
)

# GRAPH 1
st.header("🌡️ Temperature Comparison")

fig1 = px.bar(
    filtered_df,
    x="Environment",
    y="Temperature (°C)",
    color="Temperature (°C)",
    title="Illustrative Temperature Comparison"
)

st.plotly_chart(fig1, use_container_width=True)

# GRAPH 2
st.header("💧 Water Availability")

fig2 = px.bar(
    filtered_df,
    x="Environment",
    y="Water Availability (%)",
    color="Water Availability (%)",
    title="Illustrative Water Availability"
)

st.plotly_chart(fig2, use_container_width=True)

# GRAPH 3
st.header("🛰️ Analog Suitability")

fig3 = px.bar(
    filtered_df,
    x="Environment",
    y="Analog Score",
    color="Analog Score",
    title="Illustrative Analog Suitability Score"
)

st.plotly_chart(fig3, use_container_width=True)

# FOOTER
st.divider()

st.markdown("""
### About TerraSpace Analog Explorer

Our mission is to explore Earth analog environments
and understand how environmental observations can
support planetary exploration research.

**Data status:** Illustrative demonstration data.

**NASA data integration:** Planned.

**Developed for:** NASA Space Apps Challenge 2026 🚀
""")

