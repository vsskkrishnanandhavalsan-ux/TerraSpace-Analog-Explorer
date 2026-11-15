import json
import urllib.parse
import math
import urllib.request
import urllib.error
from datetime import date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
import streamlit as st


# ============================================================
# TERRASPACE ANALOG EXPLORER — ADVANCED VERSION
# NASA POWER Daily Point API
# ============================================================

st.set_page_config(
    page_title="TerraSpace Analog Explorer",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 TerraSpace Analog Explorer")
st.subheader("Comparative Earth-environment research for Moon and Mars exploration")

st.markdown(
    """
    Explore representative desert, Arctic, Antarctic and volcanic environments
    using daily environmental data from NASA POWER. Compare locations, inspect
    data completeness, and examine environmental patterns relevant to analog research.
    """
)

st.info(
    "**Scientific scope:** This tool compares selected Earth locations using "
    "gridded NASA POWER data. It does not establish that a location is a true "
    "lunar or Martian analog, and it does not rank locations for mission suitability."
)


# ------------------------------------------------------------
# MULTI-LOCATION SITE DATABASE
# Coordinates are representative sampling points selected for this project.
# They are not official NASA analog-site designations.
# ------------------------------------------------------------

SITES = [
    {
        "site": "Atacama — Central",
        "environment": "Desert",
        "region": "Atacama Desert, Chile",
        "latitude": -22.90,
        "longitude": -68.20,
        "description": "High-altitude hyper-arid desert reference point.",
    },
    {
        "site": "Atacama — Northern",
        "environment": "Desert",
        "region": "Atacama Desert, Chile",
        "latitude": -21.50,
        "longitude": -68.30,
        "description": "Northern Atacama desert reference point.",
    },
    {
        "site": "Atacama — Southern",
        "environment": "Desert",
        "region": "Atacama Desert, Chile",
        "latitude": -24.00,
        "longitude": -69.00,
        "description": "Southern Atacama desert reference point.",
    },
    {
        "site": "McMurdo — Station area",
        "environment": "Antarctic",
        "region": "Ross Island, Antarctica",
        "latitude": -77.85,
        "longitude": 166.67,
        "description": "Cold Antarctic coastal reference point.",
    },
    {
        "site": "Ross Ice Shelf — Reference",
        "environment": "Antarctic",
        "region": "Ross Ice Shelf, Antarctica",
        "latitude": -78.50,
        "longitude": 175.00,
        "description": "Ross Ice Shelf reference coordinate.",
    },
    {
        "site": "Transantarctic — Reference",
        "environment": "Antarctic",
        "region": "Transantarctic region, Antarctica",
        "latitude": -82.00,
        "longitude": 160.00,
        "description": "Interior Antarctic reference coordinate.",
    },
    {
        "site": "Mauna Loa — Observatory area",
        "environment": "Volcanic",
        "region": "Hawaii, USA",
        "latitude": 19.54,
        "longitude": -155.58,
        "description": "High-altitude volcanic reference point.",
    },
    {
        "site": "Mauna Loa — Northern slope",
        "environment": "Volcanic",
        "region": "Hawaii, USA",
        "latitude": 19.65,
        "longitude": -155.45,
        "description": "Northern volcanic-slope reference point.",
    },
    {
        "site": "Mauna Loa — Southern slope",
        "environment": "Volcanic",
        "region": "Hawaii, USA",
        "latitude": 19.40,
        "longitude": -155.55,
        "description": "Southern volcanic-slope reference point.",
    },
    {
        "site": "Utqiagvik — Coastal",
        "environment": "Arctic",
        "region": "Alaska, USA",
        "latitude": 71.29,
        "longitude": -156.79,
        "description": "Arctic coastal reference point near Utqiagvik.",
    },
    {
        "site": "North Slope — Reference",
        "environment": "Arctic",
        "region": "Alaska, USA",
        "latitude": 70.20,
        "longitude": -148.50,
        "description": "Alaska North Slope reference coordinate.",
    },
    {
        "site": "Arctic Alaska — Reference",
        "environment": "Arctic",
        "region": "Alaska, USA",
        "latitude": 69.60,
        "longitude": -148.70,
        "description": "Arctic Alaska inland reference coordinate.",
    },
]

PARAMETERS = "T2M,RH2M,PRECTOTCORR,ALLSKY_SFC_SW_DWN"

VARIABLES = [
    "Temperature (°C)",
    "Relative Humidity (%)",
    "Precipitation (mm/day)",
    "Solar Radiation (kWh/m²/day)",
]

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"


# ------------------------------------------------------------
# DATA CLEANING AND API ACCESS
# ------------------------------------------------------------

def clean_value(value):
    """Convert NASA POWER missing/invalid values to None."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number == -999 or pd.isna(number):
        return None
    return number


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_power_data(latitude, longitude, start_date, end_date):
    """Retrieve daily NASA POWER data for one coordinate."""
    query = {
        "parameters": PARAMETERS,
        "community": "RE",
        "longitude": longitude,
        "latitude": latitude,
        "start": start_date,
        "end": end_date,
        "format": "JSON",
    }
    url = NASA_POWER_URL + "?" + urllib.parse.urlencode(query)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TerraSpace-Analog-Explorer/2.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"NASA POWER returned HTTP error {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to NASA POWER: {exc.reason}") from exc
    except TimeoutError as exc:
        raise RuntimeError("The NASA POWER request timed out.") from exc

    properties = payload.get("properties", {})
    values = properties.get("parameter")
    if not isinstance(values, dict):
        raise RuntimeError("NASA POWER response did not contain parameter data.")
    if "T2M" not in values:
        raise RuntimeError("Temperature data was not present in the response.")

    all_days = set()
    for parameter_data in values.values():
        if isinstance(parameter_data, dict):
            all_days.update(parameter_data.keys())

    records = []
    for day in sorted(all_days):
        temp = clean_value(values.get("T2M", {}).get(day))
        humidity = clean_value(values.get("RH2M", {}).get(day))
        precipitation = clean_value(values.get("PRECTOTCORR", {}).get(day))
        solar_mj = clean_value(values.get("ALLSKY_SFC_SW_DWN", {}).get(day))
        solar_kwh = solar_mj / 3.6 if solar_mj is not None else None

        records.append(
            {
                "Date": pd.to_datetime(day, format="%Y%m%d"),
                "Temperature (°C)": temp,
                "Relative Humidity (%)": humidity,
                "Precipitation (mm/day)": precipitation,
                "Solar Radiation (kWh/m²/day)": solar_kwh,
            }
        )

    return pd.DataFrame(records)


# ------------------------------------------------------------
# SIDEBAR CONTROLS
# ------------------------------------------------------------

with st.sidebar:
    st.header("Explore environments")
    environment_filter = st.selectbox(
        "Choose environment",
        ["All Regions", "Desert", "Arctic", "Antarctic", "Volcanic"],
    )

    st.divider()
    st.subheader("Date range")
    selected_dates = st.date_input(
        "Select start and end dates",
        value=(date(2025, 1, 1), date(2025, 1, 7)),
        min_value=date(1981, 1, 1),
        max_value=date.today(),
        help="NASA POWER daily data can have a reporting delay.",
    )

    st.caption("For a first test, keep the default 7-day period.")
    st.divider()
    if st.button("Clear cached NASA data", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache cleared. Rerun to retrieve fresh data.")


# ------------------------------------------------------------
# VALIDATE INPUTS AND SELECT SITES
# ------------------------------------------------------------

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.warning("Please select both a start date and an end date.")
    st.stop()

start_day, end_day = selected_dates
if start_day > end_day:
    st.error("Start date must be earlier than or equal to end date.")
    st.stop()

if (end_day - start_day).days > 366:
    st.error("Please select a period of 366 days or less for this multi-location demo.")
    st.stop()

start_api = start_day.strftime("%Y%m%d")
end_api = end_day.strftime("%Y%m%d")

selected_sites = [
    site for site in SITES
    if environment_filter == "All Regions"
    or site["environment"] == environment_filter
]

st.markdown("### Selected sampling locations")
st.caption(
    f"{len(selected_sites)} representative coordinate(s) selected. "
    "Coordinates are project sampling choices, not official analog-site boundaries."
)

site_table = pd.DataFrame(selected_sites)
st.dataframe(
    site_table[["site", "environment", "region", "latitude", "longitude", "description"]],
    use_container_width=True,
    hide_index=True,
)


# ------------------------------------------------------------
# FETCH ALL SELECTED LOCATIONS
# ------------------------------------------------------------

records = []
errors = []

progress = st.progress(0, text="Preparing NASA POWER requests...")
with ThreadPoolExecutor(max_workers=4) as executor:
    future_to_site = {
        executor.submit(
            fetch_power_data,
            site["latitude"],
            site["longitude"],
            start_api,
            end_api,
        ): site
        for site in selected_sites
    }

    completed = 0
    for future in as_completed(future_to_site):
        site = future_to_site[future]
        completed += 1
        progress.progress(
            completed / len(selected_sites),
            text=f"Retrieving NASA POWER data: {completed}/{len(selected_sites)} locations",
        )
        try:
            frame = future.result()
            if frame.empty:
                errors.append((site["site"], "No daily records returned for this period."))
                continue
            frame.insert(0, "Longitude", site["longitude"])
            frame.insert(0, "Latitude", site["latitude"])
            frame.insert(0, "Region", site["region"])
            frame.insert(0, "Environment", site["environment"])
            frame.insert(0, "Site", site["site"])
            records.append(frame)
        except Exception as exc:
            errors.append((site["site"], str(exc)))

progress.empty()

if not records:
    st.error(
        "No NASA POWER data could be loaded. Check your internet connection, "
        "try another date range, or inspect the errors below."
    )
    for site_name, message in errors:
        st.write(f"**{site_name}:** {message}")
    st.stop()

data = pd.concat(records, ignore_index=True)
data = data.sort_values(["Environment", "Site", "Date"]).reset_index(drop=True)

successful_sites = data["Site"].nunique()
successful_environments = data["Environment"].nunique()
st.success(
    f"Loaded NASA POWER data for {successful_sites} of {len(selected_sites)} "
    f"selected locations across {successful_environments} environment(s)."
)

if errors:
    with st.expander(f"Locations with data errors ({len(errors)})"):
        for site_name, message in errors:
            st.write(f"**{site_name}:** {message}")


# ------------------------------------------------------------
# HIGH-LEVEL METRICS
# ------------------------------------------------------------

st.markdown("## Project overview")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Locations loaded", successful_sites)
c2.metric("Environments loaded", successful_environments)
c3.metric("Selected period", f"{(end_day - start_day).days + 1} days")
c4.metric("Daily records", len(data))


# ------------------------------------------------------------
# TABS
# ------------------------------------------------------------

overview_tab, comparison_tab, location_tab, map_tab, quality_tab, method_tab, space_tab = st.tabs(
    [
        "📊 Overview",
        "📈 Regional comparison",
        "📍 Location details",
        "🗺️ Map",
        "🧪 Data quality",
        "🔬 Methodology",
        "🌍 Earth–Moon–Mars",
    ]
)

# ------------------------------------------------------------
# OVERVIEW TAB
# ------------------------------------------------------------

with overview_tab:
    st.markdown("### Environmental data summary")
    summary = (
        data.groupby("Environment")
        .agg(
            **{
                "Locations represented": ("Site", "nunique"),
                "Mean temperature (°C)": ("Temperature (°C)", "mean"),
                "Minimum temperature (°C)": ("Temperature (°C)", "min"),
                "Maximum temperature (°C)": ("Temperature (°C)", "max"),
                "Mean relative humidity (%)": ("Relative Humidity (%)", "mean"),
                "Total precipitation (mm)": (
                    "Precipitation (mm/day)",
                    lambda x: x.sum(min_count=1),
                ),
                "Mean solar radiation (kWh/m²/day)": (
                    "Solar Radiation (kWh/m²/day)", "mean"
                ),
            }
        )
        .reset_index()
        .round(2)
    )
    st.dataframe(summary, use_container_width=True, hide_index=True)

    st.markdown("### Data completeness")
    completeness_rows = []
    for (environment, site), group in data.groupby(["Environment", "Site"]):
        for variable in VARIABLES:
            total = len(group)
            valid = int(group[variable].notna().sum())
            completeness_rows.append(
                {
                    "Environment": environment,
                    "Site": site,
                    "Variable": variable,
                    "Valid records": valid,
                    "Returned records": total,
                    "Completeness (%)": round(100 * valid / total, 1) if total else 0,
                }
            )
    completeness = pd.DataFrame(completeness_rows)
    st.dataframe(completeness, use_container_width=True, hide_index=True)

    st.markdown("### Environmental patterns over time")
    variable_choice = st.selectbox("Choose variable to plot", VARIABLES)
    daily_region = (
        data.groupby(["Date", "Environment"])[variable_choice]
        .mean()
        .unstack("Environment")
        .sort_index()
    )
    st.line_chart(daily_region)
    st.caption(
        "Each line is the daily mean across successfully returned sampling "
        "locations in that environment. Missing values are ignored by the mean."
    )


# ------------------------------------------------------------
# REGIONAL COMPARISON TAB
# ------------------------------------------------------------

with comparison_tab:
    st.markdown("### Compare environmental distributions")
    comparison_variable = st.selectbox(
        "Variable for comparison",
        VARIABLES,
        key="comparison_variable",
    )

    box_data = data[["Environment", "Site", "Date", comparison_variable]].dropna()
    if box_data.empty:
        st.warning("No valid values are available for this variable.")
    else:
        chart_data = box_data.pivot_table(
            index="Date",
            columns="Environment",
            values=comparison_variable,
            aggfunc="mean",
        )
        st.line_chart(chart_data)
        st.caption(
            "This chart compares daily environment-level means, not individual "
            "field measurements or mission suitability."
        )

        st.markdown("### Site-level statistics")
        site_stats = (
            data.groupby(["Environment", "Site"])
            .agg(
                **{
                    "Mean": (comparison_variable, "mean"),
                    "Minimum": (comparison_variable, "min"),
                    "Maximum": (comparison_variable, "max"),
                    "Valid days": (comparison_variable, "count"),
                }
            )
            .reset_index()
            .round(2)
        )
        st.dataframe(site_stats, use_container_width=True, hide_index=True)


# ------------------------------------------------------------
# LOCATION DETAILS TAB
# ------------------------------------------------------------

with location_tab:
    st.markdown("### Inspect one sampling location")
    available_sites = sorted(data["Site"].unique().tolist())
    chosen_site = st.selectbox("Select location", available_sites)
    one_site = data[data["Site"] == chosen_site].sort_values("Date")

    selected_site_info = next(site for site in selected_sites if site["site"] == chosen_site)
    st.write(selected_site_info["description"])
    st.caption(
        f"Environment: {selected_site_info['environment']} | "
        f"Region: {selected_site_info['region']} | "
        f"Coordinates: {selected_site_info['latitude']}, "
        f"{selected_site_info['longitude']}"
    )

    st.dataframe(one_site, use_container_width=True, hide_index=True)

    detail_variable = st.selectbox(
        "Choose variable for this location",
        VARIABLES,
        key="detail_variable",
    )
    st.line_chart(one_site.set_index("Date")[[detail_variable]])

    st.markdown("### Location statistics")
    detail_stats = one_site[VARIABLES].agg(["mean", "min", "max", "count"]).T
    detail_stats.columns = ["Mean", "Minimum", "Maximum", "Valid records"]
    st.dataframe(detail_stats.round(2), use_container_width=True)


# ------------------------------------------------------------
# MAP TAB
# ------------------------------------------------------------

with map_tab:
    st.markdown("### Sampling-location map")
    map_points = (
        data[["Site", "Environment", "Latitude", "Longitude"]]
        .drop_duplicates()
        .rename(columns={"Latitude": "lat", "Longitude": "lon"})
    )
    st.map(map_points[["lat", "lon"]], use_container_width=True)
    st.dataframe(
        map_points.rename(columns={"lat": "Latitude", "lon": "Longitude"}),
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "Map pins show the project-selected sampling coordinates. "
        "They do not represent the full geographic extent of each environment."
    )


# ------------------------------------------------------------
# METHODOLOGY AND SPACE EXPLORATION INTERPRETATION
# ------------------------------------------------------------
with quality_tab:
    st.header("Spatial Data Quality Check")

    st.info(
        "This analysis checks identical daily time series, "
        "nearby coordinates and missing data. Identical data "
        "does not prove that two locations share the same NASA grid cell."
    )

    # Site-level data quality
    site_quality = []

    for site_name, group in data.groupby("Site"):
        group = group.sort_values("Date")

        signature = tuple(
            tuple(
                None if pd.isna(row[col]) else round(float(row[col]), 8)
                for col in VARIABLES
            )
            for _, row in group.iterrows()
        )

        site_quality.append({
            "Site": site_name,
            "Environment": group["Environment"].iloc[0],
            "Latitude": float(group["Latitude"].iloc[0]),
            "Longitude": float(group["Longitude"].iloc[0]),
            "Records": len(group),
            "Signature": signature
        })

    quality_df = pd.DataFrame(site_quality)

    quality_df["Series Group"] = (
        pd.factorize(quality_df["Signature"])[0] + 1
    )

    duplicate_sites = quality_df[
        quality_df.duplicated("Series Group", keep=False)
    ]

    st.subheader("1. Identical Daily Data Detection")

    if duplicate_sites.empty:
        st.success("No identical daily time series detected.")
    else:
        st.warning(
            "Some locations have identical daily data. "
            "They may represent shared gridded data rather than "
            "independent observations."
        )

        st.dataframe(
            duplicate_sites[
                ["Series Group", "Site", "Environment",
                 "Latitude", "Longitude", "Records"]
            ],
            use_container_width=True,
            hide_index=True
        )

    st.subheader("2. Coordinate Proximity Check")

    distance_limit = st.slider(
        "Nearby location threshold (km)",
        min_value=10,
        max_value=200,
        value=50,
        step=10
    )

    def haversine_km(lat1, lon1, lat2, lon2):
        radius = 6371.0

        p1 = math.radians(lat1)
        p2 = math.radians(lat2)

        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)

        a = (
            math.sin(dp / 2) ** 2
            + math.cos(p1) * math.cos(p2)
            * math.sin(dl / 2) ** 2
        )

        return 2 * radius * math.asin(math.sqrt(a))

    nearby_pairs = []

    for i in range(len(quality_df)):
        for j in range(i + 1, len(quality_df)):

            a = quality_df.iloc[i]
            b = quality_df.iloc[j]

            distance = haversine_km(
                a["Latitude"], a["Longitude"],
                b["Latitude"], b["Longitude"]
            )

            if distance <= distance_limit:
                nearby_pairs.append({
                    "Location 1": a["Site"],
                    "Location 2": b["Site"],
                    "Distance (km)": round(distance, 2)
                })

    if nearby_pairs:
        st.dataframe(
            pd.DataFrame(nearby_pairs),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("No location pairs found within this threshold.")

    st.subheader("3. Missing Data Check")

    missing_data = (
        data.groupby("Site")[VARIABLES]
        .apply(lambda group: group.isna().sum())
    )

    st.dataframe(
        missing_data,
        use_container_width=True
    )

    st.subheader("4. Overall Quality Summary")

    total_sites = len(quality_df)
    unique_series = quality_df["Series Group"].nunique()
    duplicate_count = len(duplicate_sites)

    col1, col2, col3 = st.columns(3)

    col1.metric("Loaded locations", total_sites)
    col2.metric("Unique time-series groups", unique_series)
    col3.metric("Locations in duplicate groups", duplicate_count)

    st.caption(
        "These are diagnostic checks, not proof of independent "
        "NASA POWER grid cells. NASA POWER grid metadata is needed "
        "to confirm grid-cell identity."
    )
with method_tab:
    st.markdown("### Data source")
    st.write(
        "Source: NASA POWER Daily Point API. The application requests "
        "T2M (2-m air temperature), RH2M (2-m relative humidity), "
        "PRECTOTCORR (corrected precipitation) and ALLSKY_SFC_SW_DWN "
        "(all-sky surface shortwave downward radiation)."
    )

    st.markdown("### Units and processing")
    st.write(
        "- Temperature: °C\n"
        "- Relative humidity: %\n"
        "- Precipitation: mm/day\n"
        "- Solar radiation: NASA POWER MJ/m²/day converted to kWh/m²/day "
        "by dividing by 3.6.\n"
        "- NASA POWER missing-value sentinel (-999) and invalid values are "
        "excluded from statistical calculations."
    )

    st.markdown("### Sampling approach and limitations")
    st.write(
        f"Selected period: {start_day:%d %B %Y} to {end_day:%d %B %Y}. "
        f"The project contains {len(SITES)} selected sampling coordinates "
        "across four environment categories. These are representative points "
        "chosen for exploratory comparison; they are not official NASA analog "
        "sites or complete regional averages. NASA POWER values are gridded "
        "data products, not direct field measurements. Nearby coordinates may "
        "represent similar gridded conditions. Data availability can vary by "
        "parameter, location and date."
    )

    st.markdown("### Relevance to Moon and Mars analog research")
    st.write(
        "Temperature, humidity, precipitation and solar radiation describe "
        "selected aspects of Earth's surface environment. They can support "
        "first-stage environmental comparison and help identify questions "
        "for further analog research. However, these variables alone do not "
        "measure radiation exposure, atmospheric pressure, soil chemistry, "
        "dust behaviour, terrain mechanics, subsurface ice, toxicity or "
        "operational safety. A site should not be called a validated lunar "
        "or Martian analog based only on this dataset."
    )

    st.markdown("### Future scientific extensions")
    st.write(
        "Potential future work includes adding terrain and elevation datasets, "
        "geological context, soil properties, radiation measurements, "
        "high-resolution local observations, and direct comparisons with "
        "relevant lunar and Martian datasets."
    )

    st.link_button("Open NASA POWER", "https://power.larc.nasa.gov/")
    st.link_button(
        "NASA POWER API documentation",
        "https://power.larc.nasa.gov/docs/services/api/",
    )


# ------------------------------------------------------------
# DOWNLOADS
# ------------------------------------------------------------

st.markdown("---")
st.markdown("## Export results")

csv_bytes = data.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Download all daily NASA POWER records (CSV)",
    data=csv_bytes,
    file_name="terraspace_nasa_power_multisite_data.csv",
    mime="text/csv",
)

summary_csv = (
    data.groupby("Environment")[VARIABLES]
    .mean()
    .round(3)
    .reset_index()
    .to_csv(index=False)
    .encode("utf-8")
)
st.download_button(
    "📥 Download environment summary (CSV)",
    data=summary_csv,
    file_name="terraspace_environment_summary.csv",
    mime="text/csv",
)

st.caption(
    "TerraSpace Analog Explorer | Exploratory environmental comparison | "
    "NASA POWER data source acknowledged"
)
# ============================================================
# EARTH - MOON - MARS COMPARISON DASHBOARD
# ============================================================

with space_tab:
    st.header("🌍 Earth–Moon–Mars Environmental Comparison")

    st.markdown(
        "Explore environmental datasets from Earth, the lunar South Pole "
        "and Mars. Each dataset is presented with its own measurement context."
    )

    st.subheader("1. Earth — NASA POWER")

    earth_temperature = data["Temperature (°C)"].mean()
    earth_humidity = data["Relative Humidity (%)"].mean()
    earth_solar = data["Solar Radiation (kWh/m²/day)"].mean()

    e1, e2, e3 = st.columns(3)
    e1.metric("Mean temperature", f"{earth_temperature:.2f} °C")
    e2.metric("Mean humidity", f"{earth_humidity:.2f} %")
    e3.metric("Mean solar radiation", f"{earth_solar:.2f} kWh/m²/day")

    st.caption(
        "Earth values are averages across successfully loaded NASA POWER "
        "locations and the selected date range."
    )

    st.divider()
    st.subheader("2. Moon — Diviner lunar South Pole data")

    moon_file = "moon_shackleton_region_clean.csv"

    if __import__("os").path.exists(moon_file):
        moon = pd.read_csv(moon_file)

        if "temp_avg_C" in moon.columns:
            lunar_avg = pd.to_numeric(
                moon["temp_avg_C"], errors="coerce"
            ).dropna()

            if not lunar_avg.empty:
                st.metric(
                    "Diviner annual average temperature",
                    f"{lunar_avg.mean():.2f} °C"
                )
                st.caption(
                    "This is the mean of the available Diviner annual-average "
                    "temperature values in the selected lunar analysis region."
                )

        if "temp_max_C" in moon.columns:
            lunar_max = pd.to_numeric(
                moon["temp_max_C"], errors="coerce"
            ).dropna()

            if not lunar_max.empty:
                st.metric(
                    "Diviner annual maximum temperature",
                    f"{lunar_max.mean():.2f} °C"
                )

        if "ice_depth_clean_m" in moon.columns:
            ice = pd.to_numeric(
                moon["ice_depth_clean_m"], errors="coerce"
            ).dropna()

            if not ice.empty:
                st.metric(
                    "Mean non-negative modeled ice-depth value",
                    f"{ice.mean():.3f} m"
                )

        st.caption(
    "Diviner temperature products represent different measurement "
    "depths. The PDS format identifies -999 as the invalid value. "
    "Other negative ice-depth values, including -1, are flagged for "
    "further investigation and are not included in the non-negative "
    "summary. This is a model-derived parameter, not direct detection "
    "of lunar water ice."
)

    else:
        st.warning(
            "Lunar CSV not found. Keep moon_shackleton_region_clean.csv "
            "in the project folder."
        )

    st.divider()
    st.subheader("3. Mars — Perseverance MEDA")

    mars_file = "mars2020_meda_calibrated_ATS.csv"

    if __import__("os").path.exists(mars_file):
        mars_index = pd.read_csv(mars_file)
        mars_index.columns = mars_index.columns.str.strip()

        st.success("NASA MEDA Air Temperature Sensor index available.")

        st.metric("Indexed Mars data products", len(mars_index))

        st.info(
            "The MEDA ATS index identifies calibrated air-temperature "
            "science-data products. Actual observation files have not yet "
            "been retrieved and processed in this prototype."
        )

        st.dataframe(
            mars_index.head(5),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.warning("MEDA index CSV not found in the project folder.")

    st.divider()
    st.subheader("4. Scientific interpretation")

    st.markdown(
        """
        - **Earth:** NASA POWER provides gridded daily environmental data.
        - **Moon:** Diviner provides lunar thermal measurements and modeled
          ice-stability information.
        - **Mars:** MEDA provides calibrated atmospheric sensor products;
          actual observations still need processing.

        These datasets have different instruments, spatial scales, time
        coverage and measurement conditions. Their values should not be
        treated as directly equivalent or used to calculate a mission
        suitability ranking without further scientific validation.
        """
    )