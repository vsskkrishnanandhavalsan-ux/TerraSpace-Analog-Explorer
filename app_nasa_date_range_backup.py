
import json
import urllib.parse
import urllib.request
from datetime import date

import pandas as pd
import streamlit as st


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="TerraSpace Analog Explorer",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 TerraSpace Analog Explorer")
st.subheader("Exploring Earth Analog Environments for Space Exploration")

st.write(
    "Explore selected Earth environments using daily environmental data "
    "retrieved from the NASA POWER API."
)

st.info(
    "Data note: NASA POWER provides gridded data for representative coordinates. "
    "These are not direct measurements from every part of each region. "
    "The analog suitability score shown here is illustrative, not a NASA measurement."
)


# --------------------------------------------------
# EARTH ANALOG ENVIRONMENTS
# --------------------------------------------------

SITES = {
    "Atacama Desert": {
        "region": "Desert",
        "latitude": -22.9,
        "longitude": -68.2,
        "score": 92,
        "description": "A very dry high-altitude desert environment.",
    },
    "McMurdo, Antarctica": {
        "region": "Arctic / Polar",
        "latitude": -77.85,
        "longitude": 166.67,
        "score": 85,
        "description": "A cold polar reference location in Antarctica.",
    },
    "Mauna Loa, Hawaii": {
        "region": "Volcanic",
        "latitude": 19.54,
        "longitude": -155.58,
        "score": 78,
        "description": "A volcanic high-altitude environment.",
    },
    "Utqiagvik, Alaska": {
        "region": "Arctic / Polar",
        "latitude": 71.29,
        "longitude": -156.79,
        "score": 82,
        "description": "A cold Arctic coastal reference location.",
    },
}


# --------------------------------------------------
# NASA POWER PARAMETERS
# --------------------------------------------------

PARAMETERS = "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"


# --------------------------------------------------
# FETCH DATA FROM NASA POWER API
# --------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_power_data(latitude, longitude, start_date, end_date):

    query = {
        "parameters": PARAMETERS,
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }

    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        + urllib.parse.urlencode(query)
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "TerraSpace-Analog-Explorer/1.0"
        },
    )

    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))

    values = payload["properties"]["parameter"]

    records = []

    for day in values["T2M"]:

        solar_mj = values["ALLSKY_SFC_SW_DWN"].get(day)

        records.append(
            {
                "Date": pd.to_datetime(day, format="%Y%m%d"),
                "Temperature (°C)": values["T2M"].get(day),
                "Relative Humidity (%)": values["RH2M"].get(day),
                "Precipitation (mm/day)": values["PRECTOTCORR"].get(day),
                "Solar Radiation (kWh/m²/day)": (
                    solar_mj / 3.6
                    if solar_mj is not None
                    else None
                ),
            }
        )

    return pd.DataFrame(records)


# --------------------------------------------------
# SIDEBAR SETTINGS
# --------------------------------------------------

with st.sidebar:

    st.header("Explore")

    region_filter = st.selectbox(
        "Choose environment",
        [
            "All Regions",
            "Desert",
            "Arctic / Polar",
            "Volcanic",
        ],
    )

    st.divider()

    st.subheader("Choose date range")

    selected_dates = st.date_input(
        "Select start and end dates",
        value=(date(2025, 1, 1), date(2025, 1, 7)),
        min_value=date(1981, 1, 1),
        max_value=date.today(),
        help=(
            "Choose a start date and an end date. "
            "NASA POWER data availability can have a reporting delay."
        ),
    )

    st.caption("Default sample: 1–7 January 2025.")


# --------------------------------------------------
# DATE VALIDATION
# --------------------------------------------------

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:

    st.warning("Please select both a start date and an end date.")
    st.stop()


start_day, end_day = selected_dates

if start_day > end_day:

    st.error("The start date must be earlier than or equal to the end date.")
    st.stop()


start_api = start_day.strftime("%Y%m%d")
end_api = end_day.strftime("%Y%m%d")


# --------------------------------------------------
# SELECT ENVIRONMENTS
# --------------------------------------------------

selected_sites = [
    name
    for name, info in SITES.items()
    if region_filter == "All Regions"
    or info["region"] == region_filter
]


st.markdown("### Selected Earth environments")

cols = st.columns(len(selected_sites))

for col, name in zip(cols, selected_sites):

    with col:

        st.metric("Environment", name)

        st.caption(SITES[name]["description"])


# --------------------------------------------------
# RETRIEVE NASA DATA
# --------------------------------------------------

all_data = []
errors = []

with st.spinner("Retrieving selected dates from NASA POWER..."):

    for name in selected_sites:

        info = SITES[name]

        try:

            frame = fetch_power_data(
                info["latitude"],
                info["longitude"],
                start_api,
                end_api,
            )

            if frame.empty:

                errors.append(
                    (
                        name,
                        "NASA POWER returned no daily records for this date range.",
                    )
                )

                continue

            frame.insert(0, "Environment", name)

            all_data.append(frame)

        except Exception as exc:

            errors.append((name, str(exc)))


# --------------------------------------------------
# DISPLAY RESULTS
# --------------------------------------------------

if all_data:

    combined = pd.concat(all_data, ignore_index=True)

    st.success(
        f"NASA POWER data loaded for "
        f"{combined['Environment'].nunique()} environment(s), "
        f"from {start_day:%d %b %Y} to {end_day:%d %b %Y}."
    )

    # Latest available data

    st.markdown("### Latest available day in selected period")

    latest = (
        combined.sort_values("Date")
        .groupby("Environment", as_index=False)
        .tail(1)
        .sort_values("Environment")
    )

    st.dataframe(
        latest,
        use_container_width=True,
        hide_index=True,
    )

    # Daily data table

    st.markdown("### Daily NASA POWER data")

    st.dataframe(
        combined,
        use_container_width=True,
        hide_index=True,
    )

    # Temperature chart

    st.markdown("### Compare temperature")

    temperature_data = combined.pivot(
        index="Date",
        columns="Environment",
        values="Temperature (°C)",
    )

    st.line_chart(temperature_data)

    # Humidity chart

    st.markdown("### Compare relative humidity")

    humidity_data = combined.pivot(
        index="Date",
        columns="Environment",
        values="Relative Humidity (%)",
    )

    st.line_chart(humidity_data)

    # Solar radiation chart

    st.markdown("### Compare solar radiation")

    solar_data = combined.pivot(
        index="Date",
        columns="Environment",
        values="Solar Radiation (kWh/m²/day)",
    )

    st.line_chart(solar_data)

    # Environmental summary

    st.markdown("### Environmental comparison summary")

    st.caption(
        "These averages are calculated from the NASA POWER data returned "
        "for your selected dates. They are descriptive comparisons, not "
        "a ranking of which location is best for a Moon or Mars mission."
    )

    summary = (
        combined.groupby("Environment", as_index=False)
        .agg(
            **{
                "Mean temperature (°C)": (
                    "Temperature (°C)",
                    "mean",
                ),
                "Mean relative humidity (%)": (
                    "Relative Humidity (%)",
                    "mean",
                ),
                "Total precipitation (mm)": (
                    "Precipitation (mm/day)",
                    "sum",
                ),
                "Mean solar radiation (kWh/m²/day)": (
                    "Solar Radiation (kWh/m²/day)",
                    "mean",
                ),
            }
        )
        .round(2)
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
    )

    # Download CSV

    st.markdown("### Download your data")

    csv_data = combined.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download selected NASA data as CSV",
        data=csv_data,
        file_name="terraspace_nasa_power_data.csv",
        mime="text/csv",
    )

else:

    st.error(
        "No NASA POWER data could be loaded. "
        "Try a different date range or check your internet connection."
    )


# --------------------------------------------------
# DISPLAY ERRORS
# --------------------------------------------------

if errors:

    st.warning(
        "Some locations did not return data. "
        "Check the date range or try again later."
    )

    for name, message in errors:

        st.write(f"**{name}:** {message}")


# --------------------------------------------------
# DATA SOURCE AND METHOD
# --------------------------------------------------

st.markdown("---")

st.markdown("### Data source and method")

st.write(
    "Source: NASA POWER Daily Point API. Temperature is in °C, "
    "relative humidity in %, precipitation in mm/day. "
    "NASA POWER solar radiation is returned in MJ/m²/day "
    "and converted here to kWh/m²/day by dividing by 3.6."
)

st.write(
    f"Selected period: {start_day:%d %B %Y} to {end_day:%d %B %Y}. "
    "Each environment is represented by one latitude/longitude point. "
    "Values are gridded NASA POWER data, not field measurements "
    "or complete regional averages."
)

st.link_button(
    "Open NASA POWER",
    "https://power.larc.nasa.gov/",
)
