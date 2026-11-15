
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

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

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data folder"

st.title("🌍 TerraSpace Analog Explorer")
st.subheader("Exploring Earth Analog Environments for Space Exploration")

st.write(
    "Compare Earth analog environments using NASA POWER data "
    "and explore actual Mars 2020 MEDA observations."
)

# --------------------------------------------------
# EARTH ANALOG LOCATIONS
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
        "description": "A cold polar reference location.",
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

PARAMETERS = "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"

# --------------------------------------------------
# XML AND CSV FILE DISCOVERY
# --------------------------------------------------

def normalize_filename(name):
    """Normalize filenames to handle duplicate download suffixes."""
    return (
        Path(name).stem
        .replace(" (1)", "")
        .replace(" (2)", "")
        .replace(" ", "")
        .upper()
    )


def find_meda_files():
    if not DATA_DIR.exists():
        raise FileNotFoundError(
            f"Data folder not found: {DATA_DIR}"
        )

    xml_files = list(DATA_DIR.glob("*.xml"))
    csv_files = list(DATA_DIR.glob("*.csv")) + list(
        DATA_DIR.glob("*.CSV")
    )

    if not xml_files:
        raise FileNotFoundError("No XML file found in data folder.")

    xml_path = xml_files[0]

    root = ET.parse(xml_path).getroot()

    referenced_csv = None

    for element in root.iter():
        if element.tag.endswith("file_name"):
            referenced_csv = element.text
            break

    csv_path = None

    if referenced_csv:
        expected = normalize_filename(referenced_csv)

        for candidate in csv_files:
            if normalize_filename(candidate.name) == expected:
                csv_path = candidate
                break

    # Fallback for a downloaded file renamed by Windows
    if csv_path is None and len(csv_files) == 1:
        csv_path = csv_files[0]

    if csv_path is None:
        raise FileNotFoundError(
            "Could not match the CSV file referenced by the XML."
        )

    return xml_path, csv_path


# --------------------------------------------------
# READ NASA PDS4 XML METADATA
# --------------------------------------------------

def read_meda_metadata(xml_path):

    root = ET.parse(xml_path).getroot()

    metadata = {}

    wanted_fields = [
        "logical_identifier",
        "title",
        "version_id",
        "start_date_time",
        "stop_date_time",
        "purpose",
        "processing_level",
        "name",
        "type",
        "start_sol_number",
        "stop_sol_number",
    ]

    for element in root.iter():

        tag = element.tag.split("}")[-1]

        if tag in wanted_fields and element.text:
            metadata.setdefault(tag, element.text.strip())

    metadata["temperature_columns"] = []

    for element in root.iter():

        if element.tag.split("}")[-1] == "Field_Delimited":

            field_name = None

            for child in element:
                if child.tag.split("}")[-1] == "name":
                    field_name = child.text

            if field_name and field_name.startswith("ATS_LOCAL_TEMP"):
                metadata["temperature_columns"].append(field_name)

    return metadata


# --------------------------------------------------
# LOAD NASA MEDA CSV DATA
# --------------------------------------------------

@st.cache_data
def load_meda_csv(csv_path):

    frame = pd.read_csv(csv_path)

    frame.columns = frame.columns.str.strip()

    # Display MEDA CSV column names
    st.markdown("### MEDA CSV column names")
    st.write(list(frame.columns))

    # Inspect MEDA time columns
    st.markdown("### MEDA time column samples")

    time_columns = ["SCLK", "LMHD", "LTSD"]

    for column in time_columns:
        if column in frame.columns:
            st.write(f"**{column}**")
            st.write(frame[column].head(10))

    # Convert numeric columns
    for column in frame.columns:
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.notna().any():
            frame[column] = converted

    temperature_columns = [
        column for column in frame.columns
        if column.startswith("ATS_LOCAL_TEMP")
    ]

    for column in temperature_columns:
        frame[column] = pd.to_numeric(
            frame[column], errors="coerce"
        )

    return frame


# --------------------------------------------------
# NASA POWER API
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
        headers={"User-Agent": "TerraSpace-Analog-Explorer/1.0"},
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        payload = json.loads(response.read().decode("utf-8"))

    values = payload["properties"]["parameter"]

    records = []

    for day in values["T2M"]:

        solar = values["ALLSKY_SFC_SW_DWN"].get(day)

        records.append({
            "Date": pd.to_datetime(day, format="%Y%m%d"),
            "Temperature (°C)": values["T2M"].get(day),
            "Relative Humidity (%)": values["RH2M"].get(day),
            "Precipitation (mm/day)": values["PRECTOTCORR"].get(day),
            "Solar Radiation (kWh/m²/day)": (
                solar / 3.6 if solar is not None else None
            ),
        })

    return pd.DataFrame(records)


# ==================================================
# SECTION 1: MARS 2020 MEDA DATA EXPLORER
# ==================================================

st.markdown("---")
st.header("🔴 Mars 2020 MEDA Data Explorer")

try:

    xml_path, csv_path = find_meda_files()

    metadata = read_meda_metadata(xml_path)
    meda_data = load_meda_csv(str(csv_path))

    st.success("NASA XML metadata and CSV data loaded successfully!")

    st.markdown("### Mission information")

    col1, col2, col3 = st.columns(3)

    col1.metric("Mission", "Mars 2020")
    col2.metric("Instrument", "MEDA")
    col3.metric("Data records", f"{len(meda_data):,}")

    st.write("**Dataset:**", metadata.get("title", "Not available"))
    st.write("**Target:** Mars")
    st.write("**Processing level:**", metadata.get(
        "processing_level", "Not available"
    ))
    st.write("**Start time:**", metadata.get(
        "start_date_time", "Not available"
    ))
    st.write("**Stop time:**", metadata.get(
        "stop_date_time", "Not available"
    ))

    st.caption(f"XML file: {xml_path.name}")
    st.caption(f"CSV file: {csv_path.name}")

    
    st.markdown("### MEDA temperature measurements")

    temperature_columns = [
        column for column in meda_data.columns
        if column.startswith("ATS_LOCAL_TEMP")
    ]

    if temperature_columns:

        # Convert Kelvin measurements to Celsius.
        for column in temperature_columns:
            meda_data[column + "_C"] = (
                meda_data[column] - 273.15
            )

        st.write(
            "Temperature measurements from five MEDA sensor positions."
        )

        # Select the measurement records to analyse.
        st.markdown("### Select MEDA measurement range")

        total_records = len(meda_data)

        if total_records > 0:

            selected_range = st.slider(
                "Choose measurement records",
                min_value=0,
                max_value=total_records - 1,
                value=(0, total_records - 1),
                step=1,
            )

            start_record, end_record = selected_range

            selected_data = meda_data.iloc[
                start_record:end_record + 1
            ].copy()

            # Extract the Mars sol number from LMST.
            if "LMST" in selected_data.columns:

                selected_data["Mars Sol"] = (
                    selected_data["LMST"]
                    .astype(str)
                    .str.extract(r"^(\d+)")
                    .astype("Int64")
                )

                available_sols = sorted(
                    selected_data["Mars Sol"]
                    .dropna()
                    .unique()
                )

                if available_sols:

                    selected_sol = st.selectbox(
                        "Choose a Mars Sol",
                        available_sols,
                    )

                    selected_data = selected_data[
                        selected_data["Mars Sol"] == selected_sol
                    ].copy()

            st.caption(
                f"Showing records {start_record + 1} "
                f"to {end_record + 1} "
                f"out of {total_records:,} records."
            )

            chart_columns = [
                column + "_C"
                for column in temperature_columns
            ]

            selected_sensor = st.selectbox(
                "Choose a MEDA temperature sensor",
                temperature_columns,
            )

            
            st.markdown(
                "### MEDA temperature graph — Mars Local Time"
            )

            selected_chart_column = selected_sensor + "_C"

            if "LMST" in selected_data.columns:

                chart_data = selected_data.set_index("LMST")[
                    [selected_chart_column]
                ]

                chart_data.index.name = "Mars Local Mean Solar Time"

                st.caption(
                    "X-axis: Mars Local Mean Solar Time (LMST) | "
                    "Y-axis: Temperature (°C)"
                )

                st.line_chart(
                    chart_data,
                    x_label="Mars Local Mean Solar Time (LMST)",
                    y_label="Temperature (°C)",
                )

            else:
                st.warning(
                    "LMST time column not found. "
                    "Displaying measurements by record number."
                )

                st.line_chart(
                    selected_data[[selected_chart_column]]
                )

            st.markdown("### Temperature statistics")

            stats = selected_data[
                [selected_chart_column]
            ].describe().T

            stats["Mean (°C)"] = stats["mean"]
            stats["Minimum (°C)"] = stats["min"]
            stats["Maximum (°C)"] = stats["max"]

            st.dataframe(
                stats[[
                    "Mean (°C)",
                    "Minimum (°C)",
                    "Maximum (°C)",
                ]].round(2),
                use_container_width=True,
            )


            st.markdown("### MEDA raw CSV measurements")

            st.dataframe(
                selected_data,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download MEDA analysis CSV",
                selected_data.to_csv(index=False),
                file_name="terraspace_meda_analysis.csv",
                mime="text/csv",
            )

        else:
            st.warning("The MEDA CSV contains no records.")

    else:
        st.warning(
            "No ATS_LOCAL_TEMP columns were found in the CSV."
        )


except Exception as exc:

    st.error(f"Mars MEDA data loading error: {exc}")

    st.info(
        "Check that the XML and corresponding CSV files "
        "are both inside the data folder."
    )


# ==================================================
# SECTION 2: EARTH ANALOG EXPLORER
# ==================================================

st.markdown("---")
st.header("🌍 Earth Analog Environment Explorer")

st.info(
    "NASA POWER provides gridded environmental data. "
    "These are representative coordinates, not direct "
    "measurements from every part of each region. "
    "The analog suitability scores are illustrative."
)

with st.sidebar:

    st.header("Explore Earth Environments")

    region_filter = st.selectbox(
        "Choose environment",
        [
            "All Regions",
            "Desert",
            "Arctic / Polar",
            "Volcanic",
        ],
    )

    selected_sites = [
        name for name, info in SITES.items()
        if region_filter == "All Regions"
        or info["region"] == region_filter
    ]

    st.caption("NASA POWER daily data.")

    st.divider()

    st.caption("Sample period: 1–7 January 2025")


st.markdown("### Selected Earth environments")

cols = st.columns(len(selected_sites))

for col, name in zip(cols, selected_sites):

    with col:
        st.metric("Environment", name)
        st.caption(SITES[name]["description"])


all_data = []
errors = []

with st.spinner("Retrieving NASA POWER data..."):

    for name in selected_sites:

        info = SITES[name]

        try:

            frame = fetch_power_data(
                info["latitude"],
                info["longitude"],
                "20250101",
                "20250107",
            )

            frame.insert(0, "Environment", name)

            all_data.append(frame)

        except Exception as exc:

            errors.append((name, str(exc)))


if all_data:

    combined = pd.concat(all_data, ignore_index=True)

    st.success(
        f"NASA POWER data loaded for "
        f"{combined['Environment'].nunique()} environment(s)."
    )

    st.markdown("### Latest sample-day comparison")

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

    st.markdown("### Daily environmental data")

    st.dataframe(
        combined,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Temperature comparison")

    st.line_chart(
        combined.pivot(
            index="Date",
            columns="Environment",
            values="Temperature (°C)",
        )
    )

    st.markdown("### Relative humidity comparison")

    st.line_chart(
        combined.pivot(
            index="Date",
            columns="Environment",
            values="Relative Humidity (%)",
        )
    )

    st.markdown("### Solar radiation comparison")

    st.line_chart(
        combined.pivot(
            index="Date",
            columns="Environment",
            values="Solar Radiation (kWh/m²/day)",
        )
    )

    st.markdown("### Illustrative analog suitability scores")

    score_frame = pd.DataFrame([
        {
            "Environment": name,
            "Illustrative score": SITES[name]["score"],
        }
        for name in selected_sites
    ])

    st.bar_chart(
        score_frame.set_index("Environment")
    )

    st.caption(
        "Scores are illustrative placeholders, not scientifically "
        "validated rankings."
    )

else:

    st.warning(
        "NASA POWER data could not be loaded. "
        "Check your internet connection and try again."
    )


if errors:

    st.warning("Some locations could not be loaded.")

    for name, message in errors:
        st.write(f"**{name}:** {message}")


# ==================================================
# SECTION 3: DATA SOURCES
# ==================================================

st.markdown("---")
st.header("📚 Data Sources and Method")

st.write(
    "Mars data: NASA PDS4 Mars 2020 MEDA calibrated "
    "Air Temperature Sensor observations."
)

st.write(
    "Earth environmental data: NASA POWER Daily Point API."
)

st.write(
    "MEDA temperature data are supplied in Kelvin. "
    "The dashboard converts them into Celsius by subtracting 273.15."
)

st.write(
    "NASA POWER solar radiation is converted from "
    "MJ/m²/day to kWh/m²/day by dividing by 3.6."
)

st.link_button(
    "Open NASA POWER",
    "https://power.larc.nasa.gov/",
)

st.link_button(
    "Open NASA PDS",
    "https://pds.nasa.gov/",
)

st.caption(
    "TerraSpace Analog Explorer | Research prototype"
)
