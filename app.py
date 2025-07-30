import streamlit as st
import pydeck as pdk
#import panel as pn
import pandas as pd
import h3
import requests

# Controls
MAX_SAFE_RES = 5
res = 3
filled = True
wireframe = False
opacity = 0.1

st.set_page_config(page_title="Churches in Germany", layout="wide")
st.title("Churches in Germany")

st.markdown(
    "Drag to spin the globe, scroll to zoom. "
    "Use the sidebar to change H3 resolution or styling."
)

# Data prep
@st.cache_data(show_spinner=True)
def hex_df_at_resolution(target_res: int) -> pd.DataFrame:
    """Return a DataFrame of all H3 cells at a given resolution."""
    if target_res == 0:
        cells = list(h3.get_res0_cells())
    else:
        cells = []
        for base in h3.get_res0_cells():
            cells.extend(h3.cell_to_children(base, target_res))

    # Filter to Germany bounding box (approx lat 47–55° N, lon 5–16° E)
    def _in_germany(h):
        lat, lon = h3.cell_to_latlng(h)
        return 47.0 <= lat <= 55.5 and 5.0 <= lon <= 16.5

    cells = [h for h in cells if _in_germany(h)]
    return pd.DataFrame({"hex_id": cells})

# Load church locations in Germany from OpenStreetMap and pre-compute their H3 index
@st.cache_data(show_spinner=True)
def load_church_locations() -> pd.DataFrame:
    """Fetch all Christian church nodes in Germany via the Overpass API."""
    overpass_url = "https://overpass-api.de/api/interpreter"
    overpass_query = """
    [out:json][timeout:900];
    area["ISO3166-1"="DE"][admin_level=2]->.searchArea;
    (
      node["amenity"="place_of_worship"]["religion"="christian"](area.searchArea);
    );
    out center;
    """
    resp = requests.get(overpass_url, params={"data": overpass_query})
    resp.raise_for_status()
    data = resp.json()
    coords = [(float(el["lat"]), float(el["lon"])) for el in data["elements"] if "lat" in el and "lon" in el]
    return pd.DataFrame(coords, columns=["lat", "lon"])

# Load church locations once (cached)
church_df = load_church_locations()

with st.container():
    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

    with col1:
        res = st.slider(
            "H3 resolution", 3, MAX_SAFE_RES, res,
            help="Higher resolution = more (smaller) hexagons"
        )

    with col2:
        filled = st.checkbox("Filled hexagons", filled)

    with col3:
        wireframe = st.checkbox("Show borders", wireframe)

    with col4:
        opacity = st.slider("Fill opacity", 0.05, 0.2, opacity, 0.01)

# Choose visualization mode
mode = st.radio("Visualization mode", ["Heatmap", "Stacks"], horizontal=True)




mask_geojson = {
    "type": "FeatureCollection",
    "features": [{
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            # 1st (outer) ring – entire world CCW
            # 2nd ring – Germany bbox CW (opposite winding = hole)
            "coordinates": [[
                [-180, -90], [-180, 90], [180, 90], [180, -90], [-180, -90]
            ], [
                [5.0, 47.0], [5.0, 55.5], [16.5, 55.5], [16.5, 47.0], [5.0, 47.0]
            ]]
        },
        "properties": {}
    }]
}

mask_layer = pdk.Layer(
    "GeoJsonLayer",
    mask_geojson,
    stroked=True,
    filled=True,
    get_fill_color=[0, 0, 0, 200],   # RGBA – 200≈80 % opaque
    get_line_color=[255, 255, 255, 255],
    lineWidthMinPixels=4,
    pickable=False,
)


# ---------------------------------------------
# Recompute data for selected resolution & styling
church_df["hex_id"] = church_df.apply(
    lambda r: h3.latlng_to_cell(r["lat"], r["lon"], res), axis=1
)
church_counts = church_df.groupby("hex_id").size().reset_index(name="churches")

df = hex_df_at_resolution(res).merge(church_counts, on="hex_id", how="left")
df["churches"] = df["churches"].fillna(0)

alpha = int(255 * opacity)
max_count = df["churches"].max()

# Map counts to a simple red-yellow gradient

def _count_to_color(cnt: float) -> list[int]:
    if max_count == 0:
        return [200, 200, 200, alpha]
    ratio = cnt / max_count  # 0‒1
    r = int(255 * ratio)
    g = int(180 * (1 - ratio))
    b = 50
    return [r, g, b, alpha]

df["color"] = df["churches"].apply(_count_to_color)
# Elevation for stacks (each church adds fixed height)
height_per_church = 1000  # meters
df["elevation"] = df["churches"] * height_per_church

st.caption(
    f"Rendering **{len(df):,}** hexagons at res **{res}**. Max churches in a cell: {int(max_count)}"
)

# Offer CSV download
st.download_button(
    "Download CSV",
    data=df.to_csv(index=False),
    file_name=f"churches_by_hex_res_{res}.csv",
    mime="text/csv",
    use_container_width=True,
)

# ---------------------------------------------
# Layer
alpha = int(255 * opacity)

if mode == "Heatmap":
    layer = pdk.Layer(
        "H3HexagonLayer",
        df,
        get_hexagon="hex_id",
        pickable=True,
        auto_highlight=True,
        filled=True,
        wireframe=True,
        extruded=False,
        get_fill_color="color",
        get_line_color=[255, 255, 255, alpha],
        lineWidthMinPixels=1,
    )
else:
    layer = pdk.Layer(
        "H3HexagonLayer",
        df,
        get_hexagon="hex_id",
        pickable=True,
        auto_highlight=True,
        filled=True,
        wireframe=False,
        extruded=True,
        get_elevation="elevation",
        elevation_scale=1,
        get_fill_color="color",
        get_line_color=[80, 80, 80, alpha],
        lineWidthMinPixels=1,
    )

# View
# Adjust camera for 3-D stacks
if mode == "Stacks":
    pitch, bearing = 45, 0  # tilt & rotate for perspective
else:
    pitch, bearing = 0, 0

map_view = pdk.View(type="MapView", controller=True)
initial_view_state = pdk.ViewState(
    latitude=51.0,      # (47 + 55)/2
    longitude=10.5,     # (5 + 16.5)/2
    zoom=5.4,           # tweak to taste
    pitch=pitch,
    bearing=bearing,
)
map_provider = None
map_style = None

deck = pdk.Deck(
    layers=[layer, mask_layer],
    views=[map_view],
    initial_view_state=initial_view_state,
    map_provider=map_provider,
    map_style=map_style,
    #tooltip={"text": "{hex_id} (res " + str(res) + ")"},
)

st.markdown(
    """
    <style>
    /* Remove page padding */
    .main .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
    }
    /* Make the deck.gl canvas take the full viewport */
    div[data-testid="stDeckGlJsonChart"] canvas {
        height: 80vh !important;   /* full viewport height */
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.pydeck_chart(deck, use_container_width=True)

