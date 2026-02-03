# import streamlit as st

# st.title("🎈 My new app")
# st.write(
#     "Let's start building! For help and inspiration, head over to [docs.streamlit.io](https://docs.streamlit.io/)."
# )

# app.py - Deals Scout Daily (Family MVP)
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import requests
from st_aggrid import AgGrid

st.set_page_config(page_title="Deals Scout Daily", layout="wide")

# ─── Load custom styles ────────────────────────────────
with open("src/style.css") as css:
    st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)

@st.cache_data(ttl="24h", show_spinner=False)
def load_zoning():
    try:
        gdf = gpd.read_file(ZONING_URL)
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        return gdf
    except Exception as e:
        st.error(f"Could not load zoning: {e}")
        return None

# ── Full-screen responsive video: plays once, freezes on last frame, covers entire screen ──
video_background = """
<style>
    header {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background: transparent !important;
    }

    #bg-video {
        position: fixed;
        top: 50%;
        left: 50%;
        min-width: 100%;
        min-height: 100%;
        width: auto;
        height: auto;
        transform: translate(-50%, -50%);
        object-fit: cover;          /* Key addition: fills screen, crops if needed, no distortion */
        z-index: -999;
    }

    .overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 20, 0.45);  /* adjust 0.45 → 0.55 if text readability needs improvement */
        z-index: -998;
        pointer-events: none;
    }

    .block-container {
        position: relative;
        z-index: 1;
        background: transparent;
        color: #ffffff;
    }

    .ag-theme-streamlit {
        background: rgba(255, 255, 255, 0.08) !important;
    }
</style>

<video id="bg-video" autoplay muted playsinline>
    <source src="https://raw.githubusercontent.com/georgeandrewsc/deal_scout_main/main/src/assets/helios.mp4" type="video/mp4">
    Your browser does not support the video tag.
</video>

<div class="overlay"></div>

<script>
    document.getElementById('bg-video').addEventListener('ended', function() {
        this.pause();  // Freeze on last frame
    });
</script>
"""

st.markdown(video_background, unsafe_allow_html=True)



# Now your app content
st.title("Deal Scout")


# ── Secrets (add these in Streamlit Cloud → Settings → Secrets) ──
CLIENT_ID     = st.secrets.get("CLIENT_ID", "32faf26bf8db4e12ac712b9c9f578faa")
CLIENT_SECRET = st.secrets.get("CLIENT_SECRET", "82ff1c63ee4141d0bfe2924c0ae9c5df")
TOKEN_URL     = "https://api.cotality.com/trestle/oidc/connect/token"
API_BASE      = "https://api.cotality.com/trestle/odata"

# ── Zoning: replace with your own public GitHub raw URL ──
ZONING_URL = "/workspaces/deal_scout_main/src/zoning.geojson"


# ── Load zoning once (cached) ───────────────────────────────
# @st.cache_data(ttl="24h", show_spinner="Loading zoning data...")
# def load_zoning():
#     try:
#         gdf = gpd.read_file(ZONING_URL)
#         if gdf.crs != "EPSG:4326":
#             gdf = gdf.to_crs("EPSG:4326")
#         return gdf
#     except Exception as e:
#         st.error(f"Could not load zoning file from URL: {e}")
#         st.stop()

# zoning_gdf = load_zoning()
# st.caption(f"Zoning loaded ({len(zoning_gdf)} polygons)")


# ── Fetch & Process Button ────────────────────────────────
# Move this CSS block higher — right after the Google Fonts import
# (or keep it here if you prefer, but it needs to load before the button)
st.markdown("""
<style>
    .stButton > button {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900;
        font-size: 1.8rem;               /* bigger for impact */
        padding: 1rem 3rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #ff6b6b, #ff8e53);  /* orange-red futuristic gradient */
        color: white;
        border: 2px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 0 20px rgba(255, 107, 107, 0.7), 0 0 40px rgba(255, 142, 83, 0.4);
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.9);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: scale(1.08);
        box-shadow: 0 0 30px rgba(255, 107, 107, 1), 0 0 60px rgba(255, 142, 83, 0.7);
        background: linear-gradient(135deg, #ff8e53, #ff6b6b);
    }
    .stButton > button:active {
        transform: scale(0.98);
    }
</style>
""", unsafe_allow_html=True)

# The futuristic button
# if st.button("Put me on the fish", type="primary", key="fish_button"):
#     # ── Load zoning only when user clicks ─────────────────
#     with st.spinner("Initializing zoning layer..."):
#         zoning_gdf = load_zoning()
#         if zoning_gdf is None:
#             st.error("Failed to load zoning data")
#             st.stop()
if st.button("Put me on the fish", type="primary", key="fish_button"):

    # ── Show feedback IMMEDIATELY ────────────────────────────────
    status = st.status("Starting process...", expanded=True)
    status.update(label="Initializing zoning layer...", state="running")

    # Small placeholder so the user sees something is happening right away
    placeholder = st.empty()
    placeholder.spinner("Loading zoning data... please wait")

    # ── Now do the actual (possibly slow) loading ─────────────────
    zoning_gdf = load_zoning()

    # Remove the placeholder spinner
    placeholder.empty()

    if zoning_gdf is None:
        status.update(label="Failed to load zoning data", state="error")
        st.stop()

    # Update status — now we know it's done
    status.update(
        label=f"Zoning layer loaded successfully ({len(zoning_gdf):,} polygons)",
        state="complete"
    )

    # ── Continue with the rest of your process ───────────────────
    # status.update(label="Authenticating with API...", state="running")

    st.success(f"Zoning ready — {len(zoning_gdf):,} polygons")

    # Then continue with token, API fetch, etc.
    with st.spinner("Getting API token..."):
        token_resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type":    "client_credentials",
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope":         "api"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        if token_resp.status_code != 200:
            st.error(f"Token request failed: {token_resp.text}")
            st.stop()
        access_token = token_resp.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    with st.spinner("Fetching MLS listings (1–3 min)..."):
        selected_fields = [
            'ListingKey', 'MlsStatus', 'ListPrice', 'StreetNumber', 'StreetName', 'UnitNumber', 'City',
            'Longitude', 'Latitude', 'LotSizeArea', 'LotSizeUnits', 'LotSizeSquareFeet',
            'PropertyType', 'PropertySubType', 'AssociationFee', 'AssociationYN', 'AssociationName'
        ]
        query = f"{API_BASE}/Property?" + "&".join([
            f"$select={','.join(selected_fields)}",
            "$filter=MlsStatus eq 'Active' and ListPrice gt 50000 and Longitude ne null and Latitude ne null and LotSizeSquareFeet gt 100",
            "$top=200",
            "$orderby=ListPrice asc"
        ])

        all_listings = []
        next_url = query
        progress_bar = st.progress(0)
        count = 0

        while next_url:
            resp = requests.get(next_url, headers=headers)
            if resp.status_code != 200:
                st.error(f"API error {resp.status_code}: {resp.text[:300]}")
                st.stop()
            page = resp.json()
            all_listings.extend(page.get("value", []))
            next_url = page.get("@odata.nextLink")
            count += len(page.get("value", []))
            progress_bar.progress(min(count / 10000, 1.0))  # rough

        mls = pd.DataFrame(all_listings)
        mls.rename(columns={"ListPrice": "CurrentPrice"}, inplace=True)

    with st.spinner("Cleaning data & calculating..."):
        # Exclude condos / units / HOA
        exclude_type = ['Apartment', 'Condominium']
        exclude_sub = ['Apartment', 'Condominium', 'Condo', 'Planned Development']
        mls = mls[
            ~mls['PropertyType'].isin(exclude_type) &
            ~mls['PropertySubType'].isin(exclude_sub) &
            mls['UnitNumber'].isna() &
            (mls['AssociationFee'].fillna(0) == 0) &
            (mls['AssociationYN'].fillna('N').str.upper() != 'Y') &
            (mls['AssociationName'].isna() | (mls['AssociationName'] == ''))
        ]

        def build_address(r):
            parts = [str(r.get(c, '')) for c in ['StreetNumber', 'StreetName', 'City'] if pd.notna(r.get(c))]
            return ' '.join(parts).strip()

        mls['Address'] = mls.apply(build_address, axis=1)

        # Lot sqft standardization
        if 'LotSizeArea' in mls.columns and 'LotSizeUnits' in mls.columns:
            area = pd.to_numeric(mls['LotSizeArea'], errors='coerce')
            units = mls['LotSizeUnits'].astype(str).str.lower().str.strip()
            mls['lot_sqft'] = area
            mls.loc[units.str.contains('acre', na=False), 'lot_sqft'] *= 43560
        else:
            mls['lot_sqft'] = pd.to_numeric(mls.get('LotSizeSquareFeet'), errors='coerce')

        valid = mls.dropna(subset=['lot_sqft', 'Longitude', 'Latitude', 'CurrentPrice'])
        valid = valid[(valid['lot_sqft'] > 100) & (valid['CurrentPrice'] > 0)]

        # Spatial join
        gdf_mls = gpd.GeoDataFrame(
            valid,
            geometry=gpd.points_from_xy(valid.Longitude, valid.Latitude),
            crs="EPSG:4326"
        )
        matched = gpd.sjoin(gdf_mls, zoning_gdf, how='left', predicate='within')
        matched = matched[matched['Zoning'].notna()]

        matched['zone_code'] = (
            matched['Zoning']
            .fillna('No Zoning')
            .astype(str)
            .str.replace(r'\(.*?\)|\[.*?\]|-.*|/.*|\s+', '', regex=True)
            .str.split(r'[-+]').str[0]
            .str.upper()
        )

        # Density & metrics
        density_map = {
            'A1': 108900, 'A2': 43560, 'RA': 17500, 'RE9': 9000, 'RE11': 11000, 'RE15': 15000, 'RE20': 20000,
            'RE40': 40000, 'R1': 5000, 'RS': 7500, 'R2': 2500, 'RD1.5': 1500, 'RD2': 2000, 'RD3': 3000,
            'RMP':20000, 'RW2':1150, 'RAS3':800, 'CR':400, 'C1':800, 'C2':400, 'C4':400, 'C5':400,
            'CM':800, 'MR1':400, 'M1':400, 'MR2':200, 'M2':200,
            'RD4': 4000, 'RD5': 5000, 'RD6': 6000, 'R3': 800, 'R4': 400, 'R5': 200, 'PB': 1
        }
        matched['soft_per_unit'] = matched['zone_code'].map(density_map).fillna(1000).astype(int)
        matched['max_units']   = np.ceil(matched['lot_sqft'] / matched['soft_per_unit'].replace(0, np.nan)).astype(int)
        matched['price_per_unit'] = np.where(
            matched['max_units'] > 0,
            (matched['CurrentPrice'] / matched['max_units']).round().astype(int),
            np.nan
        )
        matched['price_per_unit'] = matched['price_per_unit'].fillna(0).astype(int)

        # Final filters for realism
                # Final filters for realism
        matched = matched[matched['price_per_unit'] >= 25000]

    # ── Prepare the display dataframe ──
    display_df = matched[[
        'Address', 'CurrentPrice', 'max_units', 'Zoning',
        'price_per_unit', 'soft_per_unit', 'zone_code'
    ]].rename(columns={
        'CurrentPrice': 'Purchase Price',
        'max_units': 'Potential Units',
        'price_per_unit': 'Price per Unit',
        'soft_per_unit': 'Min Sqft/Unit',
        'zone_code': 'Base Zone'
    }).sort_values('Price per Unit')          # sorts from lowest to highest price per unit

    # Limit to the top 100 best deals
    display_df = display_df.head(1000)

    # Show the correct number of displayed rows
    st.success(f"Showing top {len(display_df):,} deals after all filters")

    # Optional: show how many were processed before limiting
    if len(display_df) < len(matched):
        st.caption(f"(filtered & sorted from {len(matched):,} total matches)")

    # Display the table (only 100 rows max)
    # AgGrid(
    #     display_df,
    #     height=700,
    #     fit_columns_on_grid_load=True,
    #     enable_enterprise_modules=False,
    #     key='deals_table'
    # )
    # Replace the AgGrid block with this
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        
        # Enables multi-column sorting + column configuration
        column_config={
            "Address": st.column_config.TextColumn("Address", width="medium"),
            "Purchase Price": st.column_config.NumberColumn("Purchase Price", format="%d"),
            "Potential Units": st.column_config.NumberColumn("Potential Units", format="%d"),
            "Price per Unit": st.column_config.NumberColumn("Price per Unit", format="%d"),
            "Min Sqft/Unit": st.column_config.NumberColumn("Min Sqft/Unit", format="%d"),
            "Base Zone": st.column_config.TextColumn("Base Zone"),
            "Zoning": st.column_config.TextColumn("Zoning", width="medium"),
        }
    )

    # Download only the displayed rows
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Top 100 CSV",
        data=csv,
        file_name="deals_top_100.csv",
        mime="text/csv"
    )