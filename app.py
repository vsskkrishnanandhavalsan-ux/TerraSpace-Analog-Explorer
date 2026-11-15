
import streamlit as st
import pandas as pd
import plotly.express as px
import requests

from datetime import date, timedelta


# =====================================
# PAGE CONFIGURATION
# =====================================

st.set_page_config(
    page_title="TerraSpace Analog Explorer",
    page_icon="🌍",
    layout="wide"
)


# =====================================
# ENVIRONMENT LOCATIONS
# =====================================

locations = {
    "Atacama Desert": {
        "latitude": -22.91,
        "longitude": -68.20,
        "region": "Desert"
    },

    "Antarctica": {
        "latitude": -77.85,
        "longitude": 166.67,
        "region": "Arctic"
    },

    "Hawaii Volcanic Region": {
        "latitude": 19.42,
        "longitude": -155.29,
        "region": "Volcanic"
    },

    "Arctic Tundra": {
        "latitude": 71.29,
        "longitude": -156.79,
        "region": "Arctic"
    }
}


# =====================================
# NASA POWER API
# =====================================

@st.cache_data(ttl=3600)
def get_nasa_data(latitude, longitude):

    start_date = date(2025, 1, 1)
    end_date = date(2025, 1, 30)

    url = (
        "https://power.larc.nasa.gov/api/temporal/"
        "daily/point"
    )

    params = {
        "parameters": "T2M,ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date.strftime("%Y%m%d"),
        "end": end_date.strftime("%Y%m%d"),
        "format": "JSON",
        "time-standard": "UTC"
    }

    response = requests.get(
        url,
        params=params,
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    parameters = result["properties"]["parameter"]

    temperature = parameters["T2M"]
    solar = parameters["ALLSKY_SFC_SW_DWN"]

    
    df = pd.DataFrame({
        "Date": list(temperature.keys()),
        "Temperature (°C)": list(temperature.values()),
        "Solar Radiation (kWh/m²/day)": [
            solar.get(d) for d in temperature.keys()
        ]
    })

    df["Date"] = pd.to_datetime(
        df["Date"],
        format="%Y%m%d"
    )

    df["Temperature (°C)"] = pd.to_numeric(
        df["Temperature (°C)"],
        errors="coerce"
    )

    df["Solar Radiation (kWh/m²/day)"] = pd.to_numeric(
        df["Solar Radiation (kWh/m²/day)"],
        errors="coerce"
    )

    df.loc[
        df["Temperature (°C)"] <= -999,
        "Temperature (°C)"
    ] = float("nan")

    df.loc[
        df["Solar Radiation (kWh/m²/day)"] <= -999,
        "Solar Radiation (kWh/m²/day)"
    ] = float("nan")

    return df
# =====================================
# HEADER
# =====================================

st.title("🌍 TerraSpace Analog Explorer")

st.subheader(
    "Exploring Earth Analog Environments for Space Exploration"
)

st.markdown("""
Welcome to TerraSpace Analog Explorer!

Explore Earth environments that may provide useful
analogs for planetary exploration and future missions.

**Scientific data source:** NASA POWER API

Temperature and solar radiation are retrieved
from NASA POWER.
""")

st.divider()


# =====================================
# SIDEBAR
# =====================================

st.sidebar.title("🛰️ Explorer Controls")

selected_region = st.sidebar.selectbox(
    "Select an Analog Environment",
    [
        "All Regions",
        "Desert",
        "Arctic",
        "Volcanic"
    ]
)

if st.sidebar.button("🔄 Refresh NASA Data"):

    get_nasa_data.clear()

    st.rerun()


# =====================================
# FETCH NASA DATA
# =====================================

records = []

temperature_history = {}

errors = []

with st.spinner(
    "Retrieving temperature and solar radiation from NASA..."
):

    for environment, location in locations.items():

        try:

            data = get_nasa_data(
                location["latitude"],
                location["longitude"]
            )

            records.append({

                "Environment": environment,

                "Temperature (°C)": data[
                    "Temperature (°C)"
                ].mean(),

                "Solar Radiation (kWh/m²/day)": data[
                    "Solar Radiation (kWh/m²/day)"
                ].mean(),

                "Region": location["region"]

            })

            temperature_history[
                environment
            ] = data

        except Exception as e:

            errors.append(
                f"{environment}: {str(e)}"
            )


# =====================================
# ERROR HANDLING
# =====================================

for error in errors:

    st.warning(error)


if not records:

    st.error(
        "NASA data could not be retrieved. "
        "Check your internet connection."
    )

    st.stop()


df = pd.DataFrame(records)


# =====================================
# FILTER DATA
# =====================================

if selected_region == "All Regions":

    filtered_df = df.copy()

else:

    filtered_df = df[
        df["Region"] == selected_region
    ]

 # =====================================
# ENVIRONMENT COMPARISON TABLE
# =====================================

st.divider()

st.header("🌎 Analog Environment Comparison")

comparison_df = filtered_df[
    [
        "Environment",
        "Temperature (°C)",
        "Solar Radiation (kWh/m²/day)"
    ]
].copy()

st.dataframe(
    comparison_df,
    use_container_width=True,
    hide_index=True
)


# =====================================
# ENVIRONMENT OVERVIEW
# =====================================

st.header("📊 Environment Overview")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Environments Retrieved",
    len(filtered_df)
)

col2.metric(
    "Average Temperature",
    f"{filtered_df['Temperature (°C)'].mean():.2f} °C"
)

col3.metric(
    "Average Solar Radiation",
    f"{filtered_df['Solar Radiation (kWh/m²/day)'].mean():.2f} kWh/m²/day"
)

st.divider()


# =====================================
# DATA TABLE
# =====================================

st.header("🌎 Analog Environment Comparison")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True
)


# =====================================
# TEMPERATURE GRAPH
# =====================================

st.header("🌡️ Temperature Comparison")

fig1 = px.bar(
    filtered_df,
    x="Environment",
    y="Temperature (°C)",
    color="Temperature (°C)",
    title="NASA Temperature Comparison"
)

st.plotly_chart(
    fig1,
    use_container_width=True
)


# =====================================
# SOLAR RADIATION GRAPH
# =====================================

st.header("☀️ Solar Radiation Comparison")

fig2 = px.bar(
    filtered_df,
    x="Environment",
    y="Solar Radiation (kWh/m²/day)",
    color="Solar Radiation (kWh/m²/day)",
    title="NASA Solar Radiation Comparison"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)


# =====================================
# ENVIRONMENT HISTORY
# =====================================

st.header("📈 Environmental Data History")

selected_environment = st.selectbox(
    "Choose an Environment",
    list(temperature_history.keys())
)

history_df = temperature_history[
    selected_environment
]


# TEMPERATURE HISTORY

st.subheader("🌡️ Daily Temperature")

fig3 = px.line(
    history_df,
    x="Date",
    y="Temperature (°C)",
    markers=True,
    title=f"Temperature History - {selected_environment}"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)


# SOLAR RADIATION HISTORY

st.subheader("☀️ Daily Solar Radiation")

fig4 = px.line(
    history_df,
    x="Date",
    y="Solar Radiation (kWh/m²/day)",
    markers=True,
    title=f"Solar Radiation History - {selected_environment}"
)

st.plotly_chart(
    fig4,
    use_container_width=True
)


# =====================================
# DATA STATUS
# =====================================

st.divider()

st.header("🔬 Data Integration Status")

st.success(
    "Temperature: NASA POWER API"
)

st.success(
    "Solar Radiation: NASA POWER API"
)

st.warning(
    "Atmospheric pressure, water indicators "
    "and analog suitability scores are pending."
)


# =====================================
# DATA SOURCE
# =====================================

st.markdown("""
### Data Source

NASA POWER – Prediction Of Worldwide Energy Resources

Temperature parameter: T2M

Solar radiation parameter: ALLSKY_SFC_SW_DWN

Solar radiation unit: kWh/m²/day

Data frequency: Daily

Period requested: Last 30 days.

Note: NASA POWER provides gridded environmental
data, not direct ground-station measurements.
Missing values are excluded from averages.

### About TerraSpace

Developed for NASA Space Apps Challenge 2026 🚀
""")