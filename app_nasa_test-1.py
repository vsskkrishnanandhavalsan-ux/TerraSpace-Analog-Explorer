import json
import urllib.parse
import urllib.request

import pandas as pd
import streamlit as st

st.set_page_config(page_title="TerraSpace NASA Data Test", page_icon="🌍", layout="wide")

st.title("🌍 TerraSpace Analog Explorer")
st.subheader("NASA POWER data connection test")
st.write(
    "This is a separate test version. It fetches daily environmental data "
    "from NASA POWER for the Atacama Desert reference location."
)

st.info(
    "Location: Atacama Desert reference point (22.9° S, 68.2° W). "
    "The values are NASA POWER gridded data for this point, not measurements "
    "from every part of the Atacama Desert."
)

@st.cache_data(ttl=3600)
def get_nasa_data():
    params = {
        "parameters": "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN",
        "community": "RE",
        "longitude": -68.2,
        "latitude": -22.9,
        "start": "20250101",
        "end": "20250107",
        "format": "JSON",
    }
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point?"
        + urllib.parse.urlencode(params)
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "TerraSpace-Analog-Explorer/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

try:
    with st.spinner("Connecting to NASA POWER and retrieving data..."):
        result = get_nasa_data()

    parameter_data = result["properties"]["parameter"]
    rows = []
    for date_key in parameter_data["T2M"]:
        rows.append(
            {
                "Date": pd.to_datetime(date_key, format="%Y%m%d"),
                "Temperature (°C)": parameter_data["T2M"].get(date_key),
                "Relative Humidity (%)": parameter_data["RH2M"].get(date_key),
                "Precipitation (mm/day)": parameter_data["PRECTOTCORR"].get(date_key),
                "Solar Radiation (kWh/m²/day)": (
                    parameter_data["ALLSKY_SFC_SW_DWN"].get(date_key) / 3.6
                    if parameter_data["ALLSKY_SFC_SW_DWN"].get(date_key) is not None
                    else None
                ),
            }
        )

    df = pd.DataFrame(rows)
    st.success("Connected successfully! NASA POWER data received.")
    st.caption("Period: 1–7 January 2025 | Source: NASA POWER Daily API")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("### Temperature over time")
    st.line_chart(df.set_index("Date")[["Temperature (°C)"]])

    st.markdown("### Relative humidity over time")
    st.line_chart(df.set_index("Date")[["Relative Humidity (%)"]])

    st.markdown("### Solar radiation over time")
    st.line_chart(df.set_index("Date")[["Solar Radiation (kWh/m²/day)"]])

    st.markdown("### Data source")
    st.link_button(
        "Open NASA POWER",
        "https://power.larc.nasa.gov/",
    )
    st.caption(
        "NASA POWER provides gridded/reanalysis-based data. These values should "
        "not be described as direct ground-station measurements. Solar radiation "
        "has been converted from MJ/m²/day to kWh/m²/day."
    )

except Exception as error:
    st.error("The NASA data request could not be completed.")
    st.write("Please check your internet connection and try again.")
    st.caption(f"Technical detail: {error}")
