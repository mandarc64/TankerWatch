import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import pydeck as pdk
import base64
import datetime

# --------------------------
# Configuration & API Key
# --------------------------
st.set_page_config(page_title="Wildfire …", layout="wide")

# Inject CSS to remove top gap
st.markdown("""
    <style>
    /* Remove top padding on main container */
    div[class^="block-container"] {
        padding-top: 0rem !important;
    }
    /* Optional: make header background transparent */
    header.stAppHeader {
        background-color: transparent;
    }
    /* Optional: adjust sidebar header spacing */
    [data-testid="stSidebarHeader"] {
        height: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("Wildfire Response Prototype App")


pdk.settings.mapbox_api_key = st.secrets["mapbox"]["api_key"]

# --------------------------
# Utility Functions
# --------------------------
def distance_nm(coord1, coord2):
    return geodesic(coord1, coord2).nautical

def get_airport_coords(icao_code):
    match = airport_df[airport_df["ICAO"] == icao_code]
    if not match.empty:
        return (match.iloc[0]["LAT"], match.iloc[0]["LON"])
    return None

def compute_tanker_distance(row):
    coords = get_airport_coords(row["Airport"])
    if coords:
        return distance_nm(wildfire_location, coords)
    return None

def encode_image_to_base64(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# --------------------------
# Load Data
# --------------------------
@st.cache_data
def load_airport_data():
    df = pd.read_csv("airports.csv")
    return df[["Name", "ICAO", "LAT", "LON", "Elevation", "# of Runways"]].dropna(subset=["LAT", "LON", "ICAO"])

@st.cache_data
def load_tanker_data():
    df = pd.read_excel("eod_loc_July7.xlsx", engine="openpyxl")
    df.rename(columns={"TailNumber": "Tanker Number", "Type": "Aircraft Type"}, inplace=True)

    # 👉 Convert all column names to str upfront
    df.columns = df.columns.map(str)

    # Locate the date-like column and rename it
    for col in df.columns:
        if "2025" in col or "Jul" in col:
            df.rename(columns={col: "Airport"}, inplace=True)
            break

    return df[["Tanker Number", "Aircraft Type", "Airport"]]


airport_df = load_airport_data()
tanker_df = load_tanker_data()

# --------------------------
# Wildfire Coordinates Input
# --------------------------
with st.sidebar:
    st.header("Enter Wildfire Coordinates")
    input_lat = st.number_input("Latitude", value=37.0, format="%.6f")
    input_lon = st.number_input("Longitude", value=-120.0, format="%.6f")
    if st.button("Update Wildfire Location"):
        st.session_state["wildfire_lat"] = input_lat
        st.session_state["wildfire_lon"] = input_lon

lat = st.session_state.get("wildfire_lat", 37.0)
lon = st.session_state.get("wildfire_lon", -120.0)
wildfire_location = (lat, lon)

# ... [imports, functions, data loading, sidebar as before] ...

# --------------------------
# Nearest Bases Calculation
# --------------------------
airport_df["Distance to Fire (nm)"] = airport_df.apply(
    lambda row: distance_nm(wildfire_location, (row["LAT"], row["LON"])),
    axis=1
)
closest_bases = airport_df.nsmallest(3, "Distance to Fire (nm)").copy()
closest_bases["Distance to Fire (nm)"] = closest_bases["Distance to Fire (nm)"].round(1)

# --------------------------
# Map Layers Setup
# --------------------------
line_data = [{"path": [wildfire_location, (row["LAT"], row["LON"])]} for _, row in closest_bases.iterrows()]
line_layer = pdk.Layer("LineLayer", data=pd.DataFrame(line_data),
                       get_source_position=lambda _: wildfire_location,
                       get_target_position=lambda r: r["path"][1],
                       get_color=[255, 0, 0], get_width=2, pickable=False)

fire_icon_data = pd.DataFrame([{
    "lat": lat, "lon": lon,
    "icon_data": {
        "url": f"data:image/png;base64,{encode_image_to_base64('flame.png')}",
        "width": 64, "height": 64, "anchorY": 64
    }
}])
fire_layer = pdk.Layer("IconLayer", data=fire_icon_data, get_icon="icon_data",
                       get_size=4, size_scale=10, get_position="[lon, lat]", pickable=True)

airport_icon_data = closest_bases.copy()
airport_icon_data["icon_data"] = [{
    "url": f"data:image/png;base64,{encode_image_to_base64('location.png')}",
    "width": 128, "height": 128, "anchorY": 128
}] * len(closest_bases)
airport_layer = pdk.Layer("IconLayer", data=airport_icon_data, get_icon="icon_data",
                          get_size=4, size_scale=10, get_position="[LON, LAT]", pickable=True)

label_data = pd.DataFrame([{
    "lat": (lat + row["LAT"]) / 2,
    "lon": (lon + row["LON"]) / 2,
    "text": f"{row['Distance to Fire (nm)']:.0f}nm"
} for _, row in closest_bases.iterrows()])
text_layer = pdk.Layer("TextLayer", data=label_data,
                       get_position="[lon, lat]", get_text="text",
                       get_size=16, get_color=[0, 0, 0], get_alignment_baseline="'bottom'")

# --------------------------
# Map View (moved here!)
# --------------------------
st.subheader("Map View")
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/streets-v11",
    initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=5),
    layers=[line_layer, fire_layer, airport_layer, text_layer],
    api_keys={"mapbox": pdk.settings.mapbox_api_key}
))

# --------------------------
# Then show tables below
# --------------------------
st.subheader("3 Closest Air Tanker Bases to Wildfire")
st.dataframe(closest_bases[["Name", "ICAO", "LAT", "LON", "Elevation", "# of Runways", "Distance to Fire (nm)"]])

st.subheader("Air Tankers / Scoopers Location Table")
editable_tankers = st.data_editor(tanker_df, use_container_width=True, num_rows="dynamic",key="tanker_editor")

# Append distance to editable tanker table
editable_tankers["Distance to Fire (nm)"] = editable_tankers.apply(compute_tanker_distance, axis=1)
st.dataframe(editable_tankers)


# Example date comparison fix
today = datetime.date.today()
def row_has_today_date(row_date):
    if isinstance(row_date, datetime.datetime):
        row_date = row_date.date()
    return row_date == today

# You can implement your comparison logic using the function above
# e.g., mark rows or filter editable_tankers based on that date