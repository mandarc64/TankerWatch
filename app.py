import streamlit as st
import pandas as pd
from geopy.distance import geodesic
import pydeck as pdk
import base64
import datetime
import openpyxl

# --------------------------
# Configuration & API Key
# --------------------------
st.set_page_config(page_title="Wildfire …", layout="wide")

# Inject CSS for modern styling
st.markdown(
    """
    <style>
    div[class^="block-container"] {
        padding-top: 0rem !important;
    }
    header.stAppHeader {
        background-color: transparent;
    }
    [data-testid="stSidebarHeader"] {
        height: 2rem;
    }
            
    /* Increase sidebar width */
    .css-1d391kg {
        width: 400px !important;
    }
    section[data-testid="stSidebar"] {
        width: 400px !important;
    }
    section[data-testid="stSidebar"] > div {
        width: 400px !important;
    }
    
    /* Adjust main content to account for wider sidebar */
    .main .block-container {
        padding-left: 420px !important;
    }
    
    /* Modern sidebar styling */
    .sidebar .sidebar-content {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Modern map container */
    .map-container {
        border-radius: 15px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        overflow: hidden;
        margin: 20px 0;
        border: 2px solid #e1e5e9;
    }
    
    /* Custom button styling */
    .stButton > button {
        background: linear-gradient(45deg, #FF6B6B, #FF8E8E);
        color: white;
        border: none;
        border-radius: 25px;
        padding: 0.5rem 1.5rem;
        font-weight: bold;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.4);
    }
    
    /* Modern input styling */
    .stNumberInput > div > div > input {
        border-radius: 10px;
        border: 2px solid #e1e5e9;
        transition: all 0.3s ease;
    }
    
    .stNumberInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }
    
    /* Title styling */
    .main-title {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* Map legend styling */
    .map-legend {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        margin: 10px 0;
        font-size: 14px;
    }
    
    .legend-icon {
        margin-right: 10px;
        font-size: 20px;
    }
    /* Loading spinner styles */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
        backdrop-filter: blur(5px);
    }

    .spinner {
        border: 4px solid #f3f3f3;
        border-top: 4px solid #667eea;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    .loading-text {
        color: white;
        margin-top: 20px;
        font-size: 18px;
        font-weight: bold;
    }
            
    /* Hide number input spinners/arrows */
    input[type=number]::-webkit-outer-spin-button,
    input[type=number]::-webkit-inner-spin-button {
        -webkit-appearance: none;
        margin: 0;
    }

    input[type=number] {
        -moz-appearance: textfield;
    }

    /* Hide Streamlit's number input buttons */
    .stNumberInput button {
        display: none !important;
    }

    .stNumberInput [data-testid="stNumberInputStepUp"],
    .stNumberInput [data-testid="stNumberInputStepDown"] {
        display: none !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    '<h1 class="main-title">🔥 TankerWatch Wildfire Response System</h1>',
    unsafe_allow_html=True,
)
map_placeholder = st.container()
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
    """Load and process airport data from Excel file"""
    df = pd.read_excel("AirTankerBases_2025_with_ICAO_codes.xlsx", engine="openpyxl")
    # Rename columns to match the expected format
    df.rename(
        columns={
            "Airport": "Name",
            "ICAO": "ICAO",
            "latitude_deg": "LAT",
            "longitude_deg": "LON",
        },
        inplace=True,
    )

    # Add missing columns with default values
    df["Elevation"] = "N/A"  # or you can leave this empty if not needed
    df["# of Runways"] = "N/A"  # or you can leave this empty if not needed

    return df[
        [
            "Name",
            "ICAO",
            "LAT",
            "LON",
            "Elevation",
            "# of Runways",
            "Region",
            "County",
            "State",
        ]
    ].dropna(subset=["LAT", "LON", "ICAO"])


@st.cache_data
def load_tanker_data():
    """Load and process tanker data from Excel file"""
    df = pd.read_excel("eod_loc_July7.xlsx", engine="openpyxl")
    df.rename(
        columns={"TailNumber": "Tanker Number", "Type": "Aircraft Type"}, inplace=True
    )
    df.columns = df.columns.map(str)
    for col in df.columns:
        if "2025" in col or "Jul" in col:
            df.rename(columns={col: "Airport"}, inplace=True)
            break
    return df[["Tanker Number", "Aircraft Type", "Airport"]]


# Load data
airport_df = load_airport_data()
tanker_df = load_tanker_data()

# Modern Wildfire Coordinates Input with Auto-Update
# --------------------------
with st.sidebar:
    st.markdown("### 🎯 Wildfire Location Control")
    st.markdown("---")

    # Current location display
    current_lat = st.session_state.get("wildfire_lat", 37.0)
    current_lon = st.session_state.get("wildfire_lon", -120.0)

    st.markdown(
        f"""
    <div style="font-size: 18px;">
        <strong>Current Fire Location:</strong><br>
        - 📍 Lat: <code>{current_lat:.4f}</code><br>
        - 📍 Lon: <code>{current_lon:.4f}</code>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.markdown("### 🔧 Update Coordinates")

    col1, col2 = st.columns(2)
    with col1:
        input_lat = st.number_input(
            "🌐 Latitude", value=current_lat, format="%.6f", step=None, key="lat_input"
        )
    with col2:
        input_lon = st.number_input(
            "🌐 Longitude", value=current_lon, format="%.6f", step=None, key="lon_input"
        )

    # Auto-update when input values change
    if input_lat != current_lat or input_lon != current_lon:
        st.session_state["wildfire_lat"] = input_lat
        st.session_state["wildfire_lon"] = input_lon
        st.rerun()

    # Manual update button (now optional)
    if st.button("🔄 Update Fire Location", use_container_width=True):
        with st.spinner("🔄 Updating fire location..."):
            st.session_state["wildfire_lat"] = input_lat
            st.session_state["wildfire_lon"] = input_lon
            st.success("✅ Fire location updated!")
            st.rerun()

    st.markdown("---")

    # Add legend here
    st.markdown("### 🗺️ Map Legend")
    st.markdown(
        """
    <div style="background: rgba(255, 255, 255, 0.1); padding: 15px; border-radius: 10px; margin: 10px 0;">
        <div style="margin: 8px 0;">
            <span style="font-size: 24px;">🔥</span> <small>Wildfire Location</small>
        </div>
        <div style="margin: 8px 0;">
            <span style="font-size: 24px;">📍</span> <small>Air Tanker Bases</small>
        </div>
        <div style="margin: 8px 0;">
            <span style="font-size: 24px;">✈️</span> <small>Air Tankers</small>
        </div>
        <div style="margin: 8px 0;">
            <span style="font-size: 24px;">📏</span> <small>Distance Lines</small>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # Quick location presets
    st.markdown("### 🗺️ Quick Locations")
    location_presets = {
        "🏔️ Northern California": (39.7392, -121.8375),
        "🌲 Oregon": (44.0521, -121.3153),
        "🏜️ Southern California": (34.0522, -118.2437),
        "🌵 Arizona": (34.0489, -111.0937),
        "🌲 Washington": (47.6062, -122.3321),
        "⛰️ Colorado": (39.5501, -105.7821),
    }

    for name, (lat, lon) in location_presets.items():
        if st.button(name, use_container_width=True):
            with st.spinner(f"🌍 Setting location to {name}..."):
                st.session_state["wildfire_lat"] = lat
                st.session_state["wildfire_lon"] = lon
                st.success(f"✅ Set to {name}")
                st.rerun()

lat = st.session_state.get("wildfire_lat", 37.0)
lon = st.session_state.get("wildfire_lon", -120.0)
wildfire_location = (lat, lon)

# --------------------------
# Nearest Bases Calculation
# --------------------------
airport_df["Distance to Fire (nm)"] = airport_df.apply(
    lambda row: distance_nm(wildfire_location, (row["LAT"], row["LON"])), axis=1
)
closest_bases = airport_df.nsmallest(3, "Distance to Fire (nm)").copy()
closest_bases["Distance to Fire (nm)"] = closest_bases["Distance to Fire (nm)"].round(1)

# --------------------------
# Modern Editable Tanker Table + Distances
# --------------------------
st.markdown("### ✏️ Air Tankers / Scoopers Location Management")
st.markdown(
    """
<div style="background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); 
            padding: 15px; border-radius: 10px; margin: 15px 0; border-left: 4px solid #2196F3;">
    <div style="display: flex; align-items: center;">
        <span style="font-size: 24px; margin-right: 10px;">💡</span>
        <div>
            <strong>Interactive Table:</strong> Edit aircraft locations, add new tankers, or remove existing ones.<br>
            <small>Changes will automatically update distances and map markers.</small>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.spinner("📊 Loading tanker data..."):
    editable_tankers = st.data_editor(
        tanker_df,
        use_container_width=True,
        num_rows="dynamic",
        key="tanker_editor",
        hide_index=True,
        column_config={
            "Tanker Number": st.column_config.TextColumn(
                "🚁 Tanker Number",
                help="Aircraft tail number or identifier",
                width="medium",
            ),
            "Aircraft Type": st.column_config.TextColumn(
                "✈️ Aircraft Type",
                help="Type of aircraft (e.g., DC-10, C-130)",
                width="medium",
            ),
            "Airport": st.column_config.TextColumn(
                "📍 Airport Code",
                help="ICAO airport code where aircraft is located",
                width="medium",
            ),
        },
    )

    # Safely convert to DataFrame
    if not isinstance(editable_tankers, pd.DataFrame):
        if isinstance(editable_tankers, dict):
            # Handle the dictionary properly
            if "edited_rows" in editable_tankers:
                # Use the original data and apply edits
                editable_tankers = tanker_df.copy()
            else:
                # Convert dict to DataFrame more safely
                try:
                    editable_tankers = pd.DataFrame.from_dict(
                        editable_tankers, orient="index"
                    ).T
                except:
                    editable_tankers = tanker_df.copy()
        else:
            editable_tankers = tanker_df.copy()

    # Now safely apply the distance calculation
    editable_tankers["Distance to Fire (nm)"] = editable_tankers.apply(
        compute_tanker_distance, axis=1
    )
st.markdown("---")

# --------------------------
# Prepare Tanker Data for Map
# --------------------------
# editable_tankers = st.session_state.get("tanker_editor", tanker_df.copy())

# # Safely convert to DataFrame
# if not isinstance(editable_tankers, pd.DataFrame):
#     if isinstance(editable_tankers, dict):
#         # Handle the dictionary properly
#         if 'edited_rows' in editable_tankers:
#             # Use the original data and apply edits
#             editable_tankers = tanker_df.copy()
#         else:
#             # Convert dict to DataFrame more safely
#             try:
#                 editable_tankers = pd.DataFrame.from_dict(editable_tankers, orient='index').T
#             except:
#                 editable_tankers = tanker_df.copy()
#     else:
#         editable_tankers = tanker_df.copy()

# editable_tankers["Distance to Fire (nm)"] = editable_tankers.apply(compute_tanker_distance, axis=1)
# Plot Air Tankers on the Map
valid_tankers = editable_tankers.copy()
valid_tankers["coords"] = valid_tankers["Airport"].apply(get_airport_coords)
valid_tankers = valid_tankers.dropna(subset=["coords"])
valid_tankers["LAT"] = valid_tankers["coords"].apply(lambda x: x[0])
valid_tankers["LON"] = valid_tankers["coords"].apply(lambda x: x[1])
valid_tankers["icon_data"] = [
    {
        "url": f"data:image/png;base64,{encode_image_to_base64('plane.png')}",
        "width": 64,
        "height": 64,
        "anchorY": 64,
    }
] * len(valid_tankers)

# Add offset to tanker icons for multiple tankers at same airport
valid_tankers["offset_index"] = valid_tankers.groupby("Airport").cumcount()
valid_tankers["LAT_offset"] = valid_tankers["LAT"] + (
    valid_tankers["offset_index"] * 0.01
)
valid_tankers["LON_offset"] = valid_tankers["LON"] + (
    valid_tankers["offset_index"] * 0.01
)

tanker_layer = pdk.Layer(
    "IconLayer",
    data=valid_tankers,
    get_icon="icon_data",
    get_position="[LON_offset, LAT_offset]",
    get_size=4,
    size_scale=10,
    pickable=True,
)

# ADD TANKER LABELS with offset for multiple tankers at same airport
tanker_label_data = valid_tankers.copy()
tanker_label_data["label_text"] = (
    tanker_label_data["Tanker Number"] + "\n" + tanker_label_data["Airport"]
)

# Add offset for multiple tankers at same airport
offset_factor = 0.01  # Adjust this to control spacing
tanker_label_data["offset_index"] = tanker_label_data.groupby("Airport").cumcount()
tanker_label_data["LAT_offset"] = tanker_label_data["LAT"] + (
    tanker_label_data["offset_index"] * offset_factor
)
tanker_label_data["LON_offset"] = tanker_label_data["LON"] + (
    tanker_label_data["offset_index"] * offset_factor
)

# Background text layer for tankers (black shadow)
tanker_text_bg_layer = pdk.Layer(
    "TextLayer",
    data=tanker_label_data,
    get_position="[LON_offset, LAT_offset]",
    get_text="label_text",
    get_size=14,
    get_color=[0, 0, 0, 200],  # Black shadow
    get_alignment_baseline="'top'",
    get_text_anchor="'middle'",
    billboard=True,
)

# Main text layer for tankers (yellow text for visibility)
tanker_text_layer = pdk.Layer(
    "TextLayer",
    data=tanker_label_data,
    get_position="[LON_offset, LAT_offset]",
    get_text="label_text",
    get_size=14,
    get_color=[255, 255, 0, 255],  # Yellow text
    get_alignment_baseline="'top'",
    get_text_anchor="'middle'",
    billboard=True,
)

# --------------------------
# Map Layers Setup
# --------------------------
line_data = []
for _, row in closest_bases.iterrows():
    line_data.append(
        {
            "start": [lon, lat],  # Fire location
            "end": [row["LON"], row["LAT"]],  # Base location
        }
    )

line_layer = pdk.Layer(
    "LineLayer",
    data=pd.DataFrame(line_data),
    get_source_position="start",
    get_target_position="end",
    get_color=[255, 0, 0, 200],  # Red with transparency
    get_width=3,
    pickable=False,
    # Add dashed line properties
    line_width_min_pixels=2,
    line_width_max_pixels=5,
    get_line_dash_array=[10, 5],  # This creates the dashed effect
)

fire_icon_data = pd.DataFrame(
    [
        {
            "lat": lat,
            "lon": lon,
            "icon_data": {
                "url": f"data:image/png;base64,{encode_image_to_base64('flame.png')}",
                "width": 64,
                "height": 64,
                "anchorY": 64,
            },
        }
    ]
)
fire_layer = pdk.Layer(
    "IconLayer",
    data=fire_icon_data,
    get_icon="icon_data",
    get_size=4,
    size_scale=10,
    get_position="[lon, lat]",
    pickable=True,
)

airport_icon_data = closest_bases.copy()
airport_icon_data["icon_data"] = [
    {
        "url": f"data:image/png;base64,{encode_image_to_base64('location.png')}",
        "width": 128,
        "height": 128,
        "anchorY": 128,
    }
] * len(closest_bases)
airport_layer = pdk.Layer(
    "IconLayer",
    data=airport_icon_data,
    get_icon="icon_data",
    get_size=4,
    size_scale=10,
    get_position="[LON, LAT]",
    pickable=True,
)

# ADD AIRPORT LABELS for closest bases
airport_label_data = closest_bases.copy()
airport_label_data["label_text"] = (
    airport_label_data["ICAO"]
    + "\n"
    + airport_label_data["Name"]
    + "\n"
    + airport_label_data["State"]
)

# Background text layer for airports (black shadow)
airport_text_bg_layer = pdk.Layer(
    "TextLayer",
    data=airport_label_data,
    get_position="[LON, LAT]",
    get_text="label_text",
    get_size=16,
    get_color=[0, 0, 0, 200],  # Black shadow
    get_alignment_baseline="'top'",
    get_text_anchor="'middle'",
    billboard=True,
)

# Main text layer for airports (black text)
airport_text_layer = pdk.Layer(
    "TextLayer",
    data=airport_label_data,
    get_position="[LON, LAT]",
    get_text="label_text",
    get_size=16,
    get_color=[0, 0, 0, 255],  # Black text
    get_alignment_baseline="'top'",
    get_text_anchor="'middle'",
    billboard=True,
)

label_data = pd.DataFrame(
    [
        {
            "lat": (lat + row["LAT"]) / 2,
            "lon": (lon + row["LON"]) / 2,
            "text": f"{row['Distance to Fire (nm)']:.0f}nm",
        }
        for _, row in closest_bases.iterrows()
    ]
)
# Background text layer (black shadow effect)
text_background_layer = pdk.Layer(
    "TextLayer",
    data=label_data,
    get_position="[lon, lat]",
    get_text="text",
    get_size=20,
    get_color=[0, 0, 0, 180],  # Semi-transparent black
    get_alignment_baseline="'bottom'",
    get_text_anchor="'middle'",
    billboard=True,
)

# Main text layer (white text)
text_layer = pdk.Layer(
    "TextLayer",
    data=label_data,
    get_position="[lon, lat]",
    get_text="text",
    get_size=20,
    get_color=[255, 255, 255, 255],  # Solid white
    get_alignment_baseline="'bottom'",
    get_text_anchor="'middle'",
    billboard=True,
)


# --------------------------
# MODERN MAP VIEW - NOW AT THE TOP!
# --------------------------
with map_placeholder:
    st.markdown("### 🗺️ Real-Time Wildfire Response Map")
    with st.spinner("🗺️ Loading interactive map..."):
        st.markdown('<div class="map-container">', unsafe_allow_html=True)
        st.pydeck_chart(
            pdk.Deck(
                map_style="mapbox://styles/mapbox/satellite-streets-v11",
                initial_view_state=pdk.ViewState(
                    latitude=lat, longitude=lon, zoom=7, pitch=45, bearing=0
                ),
                layers=[
                    line_layer,
                    fire_layer,
                    airport_layer,
                    airport_text_bg_layer,  # NEW
                    airport_text_layer,  # NEW
                    tanker_layer,
                    tanker_text_bg_layer,  # NEW
                    tanker_text_layer,  # NEW
                    text_background_layer,  # Distance labels
                    text_layer,  # Distance labels
                ],
                api_keys={"mapbox": pdk.settings.mapbox_api_key},
                height=600,
            )
        )
        st.markdown("</div>", unsafe_allow_html=True)

    # --------------------------
    # Closest Bases Summary
    # --------------------------
    st.markdown("### 🏆 3 Closest Air Tanker Bases to Wildfire")
    st.markdown("*Automatically calculated based on current fire location*")

    # Enhanced dataframe display
    st.dataframe(
        closest_bases[
            [
                "Name",
                "ICAO",
                "Region",
                "State",
                "LAT",
                "LON",
                "Distance to Fire (nm)",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("🏢 Base Name", width="medium"),
            "ICAO": st.column_config.TextColumn("🛩️ ICAO", width="small"),
            "Region": st.column_config.TextColumn("🌍 Region", width="small"),
            "State": st.column_config.TextColumn("🗺️ State", width="small"),
            "LAT": st.column_config.NumberColumn("📍 Latitude", format="%.4f"),
            "LON": st.column_config.NumberColumn("📍 Longitude", format="%.4f"),
            "Distance to Fire (nm)": st.column_config.NumberColumn(
                "🎯 Distance (nm)", format="%.1f"
            ),
        },
    )


# Map controls info
st.markdown(
    """
<div style="text-align: center; margin: 15px 0; color: #666;">
    <small>🖱️ <strong>Map Controls:</strong> Click and drag to pan • Scroll to zoom • Hold Shift + drag to rotate</small>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 📊 Air Tankers with Calculated Distances")
st.markdown("*Real-time distance calculations from current fire location*")

# Enhanced results display
st.dataframe(
    editable_tankers,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Distance to Fire (nm)": st.column_config.NumberColumn(
            "🎯 Distance (nm)",
            help="Distance from aircraft to fire location in nautical miles",
            format="%.1f",
        )
    },
)

# --------------------------
# Optional Date Comparison Logic
# --------------------------
today = datetime.date.today()


def row_has_today_date(row_date):
    if isinstance(row_date, datetime.datetime):
        row_date = row_date.date()
    return row_date == today
