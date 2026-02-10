# app.py - Deals Scout Daily (Family MVP)
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
import requests
from la_neighborhoods import LA_CITY_NEIGHBORHOODS

st.set_page_config(page_title="Deals Scout Daily - Apts", layout="wide")

# ─── Load custom styles ────────────────────────────────
try:
    with open("src/style.css") as css:
        st.markdown(f'<style>{css.read()}</style>', unsafe_allow_html=True)
except:
    pass  # skip if file not found

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

@st.cache_data(ttl="24h", show_spinner=False)
def load_coast():
    try:
        gdf = gpd.read_file(COAST_URL)
        if gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        return gdf
    except Exception as e:
        st.error(f"Could not load coast: {e}")
        return None

# ── Full-screen responsive video ── plays twice then stops ──
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
        object-fit: cover;
        z-index: -999;
    }

    .overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0, 0, 20, 0.45);
        z-index: -998;
        pointer-events: none;
    }

    .block-container {
        position: relative;
        z-index: 1;
        background: transparent;
        color: #ffffff;
    }
</style>

<video id="bg-video" autoplay muted playsinline>
    <source src="https://raw.githubusercontent.com/georgeandrewsc/deal_scout_main/main/src/assets/helios.mp4" type="video/mp4">
    Your browser does not support the video tag.
</video>

<div class="overlay"></div>

<script>
    const video = document.getElementById('bg-video');
    let playCount = 0;
    
    video.addEventListener('ended', function() {
        playCount++;
        if (playCount < 2) {
            this.currentTime = 0;
            this.play();
        } else {
            this.pause();  // stop after 2 plays
            this.currentTime = this.duration;  // stay on last frame
        }
    });
</script>
"""

st.markdown(video_background, unsafe_allow_html=True)

st.title("Deal Scout")

# ── Secrets ──
CLIENT_ID     = st.secrets.get("CLIENT_ID", "32faf26bf8db4e12ac712b9c9f578faa")
CLIENT_SECRET = st.secrets.get("CLIENT_SECRET", "82ff1c63ee4141d0bfe2924c0ae9c5df")
TOKEN_URL     = "https://api.cotality.com/trestle/oidc/connect/token"
API_BASE      = "https://api.cotality.com/trestle/odata"

# ── Zoning and Coast URLs ──
ZONING_URL = "/workspaces/deal_scout_main/src/zoning.geojson"
COAST_URL = "/workspaces/deal_scout_main/src/coastal.geojson"

# ── Futuristic button style ──
st.markdown("""
<style>
    .stButton > button {
        font-family: 'Orbitron', sans-serif !important;
        font-weight: 900;
        font-size: 1.8rem;
        padding: 1rem 3rem;
        border-radius: 12px;
        background: linear-gradient(135deg, #ff6b6b, #ff8e53);
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

col1, col2 = st.columns(2)

with col1:
    development_button = st.button("Put me on the Development Fish", type="primary", key="dev_fish_button")

with col2:
    apartment_button = st.button("Put me on the Apartment Fish", type="primary", key="apt_fish_button")

# Common token fetch (run only if a button is pressed)
if development_button or apartment_button:
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

if development_button:

    status = st.status("Starting Development process...", expanded=True)
    status.update(label="Initializing zoning layer...", state="running")

    placeholder = st.empty()
    placeholder.spinner("Loading zoning data...")

    zoning_gdf = load_zoning()
    placeholder.empty()

    if zoning_gdf is None:
        status.update(label="Failed to load zoning data", state="error")
        st.stop()

    status.update(
        label=f"Zoning layer loaded successfully ({len(zoning_gdf):,} polygons)",
        state="complete"
    )

    with st.spinner("Fetching MLS listings (1–3 min)..."):
        selected_fields = [
            'ListingKey', 'MlsStatus', 'ListPrice', 'StreetNumber', 'StreetName', 'UnitNumber', 'City',
            'Longitude', 'Latitude', 'LotSizeArea', 'LotSizeUnits', 'LotSizeSquareFeet',
            'PropertyType', 'PropertySubType', 'AssociationFee', 'AssociationYN', 'AssociationName',
            'DaysOnMarket'
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
            progress_bar.progress(min(count / 10000, 1.0))

        mls = pd.DataFrame(all_listings)
        mls.rename(columns={"ListPrice": "CurrentPrice"}, inplace=True)

    with st.spinner("Cleaning data & calculating..."):
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

        if 'LotSizeArea' in mls.columns and 'LotSizeUnits' in mls.columns:
            area = pd.to_numeric(mls['LotSizeArea'], errors='coerce')
            units = mls['LotSizeUnits'].astype(str).str.lower().str.strip()
            mls['lot_sqft'] = area
            mls.loc[units.str.contains('acre', na=False), 'lot_sqft'] *= 43560
        else:
            mls['lot_sqft'] = pd.to_numeric(mls.get('LotSizeSquareFeet'), errors='coerce')

        valid = mls.dropna(subset=['lot_sqft', 'Longitude', 'Latitude', 'CurrentPrice'])
        valid = valid[(valid['lot_sqft'] > 100) & (valid['CurrentPrice'] > 0)]

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

        # Format price per unit: round to nearest thousand → divide by 1000 → add 'k'
        matched['price_per_unit_display'] = ((matched['price_per_unit'] / 1000).round(0).astype(int)).astype(str) + 'k'

        # Final filter
        matched = matched[matched['price_per_unit'] >= 25000]

    # ── Sort while we still have the numeric column ──
    matched = matched.sort_values('price_per_unit', ascending=True)

    # ── Prepare display dataframe ──
    display_df = matched[[
        'Address',
        'CurrentPrice',
        'max_units',
        'price_per_unit_display',
        'DaysOnMarket',
        'Zoning',
        'soft_per_unit',
        'zone_code'
    ]].rename(columns={
        'CurrentPrice': 'Purchase Price',
        'max_units': 'Potential Units',
        'price_per_unit_display': 'Price per Unit',
        'DaysOnMarket': 'Days on Market',
        'soft_per_unit': 'Min Sqft/Unit',
        'zone_code': 'Base Zone'
    })

    display_df = display_df.head(750)

    st.success(f"Showing top {len(display_df):,} development deals after all filters")
    if len(display_df) < len(matched):
        st.caption(f"(filtered & sorted from {len(matched):,} total matches)")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Address": st.column_config.TextColumn("Address", width="medium"),
            "Purchase Price": st.column_config.NumberColumn(
                "Purchase Price",
                format="$%d",           # adds $ and commas
            ),
            "Potential Units": st.column_config.NumberColumn("Potential Units", format="%d"),
            "Price per Unit": st.column_config.TextColumn("Price per Unit", width="small"),
            "Days on Market": st.column_config.NumberColumn("Days on Market", format="%d"),
            "Min Sqft/Unit": st.column_config.NumberColumn("Min Sqft/Unit", format="%d"),
            "Base Zone": st.column_config.TextColumn("Base Zone", width="small"),
            "Zoning": st.column_config.TextColumn("Zoning", width="medium"),
        }
    )

    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Top Development Deals CSV",
        data=csv,
        file_name="development_deals.csv",
        mime="text/csv"
    )

if apartment_button:


    status = st.status("Starting Apartment process...", expanded=True)
    status.update(label="Initializing coast layer...", state="running")

    placeholder = st.empty()
    placeholder.spinner("Loading coast data...")

    coast_gdf = load_coast()
    placeholder.empty()

    if coast_gdf is None:
        status.update(label="Failed to load coast data", state="error")
        st.stop()

    status.update(
        label=f"Coast layer loaded successfully ({len(coast_gdf):,} features)",
        state="complete"
    )

    with st.spinner("Fetching MLS listings (1–3 min)..."):
        selected_fields = [
            'ListingKey', 'MlsStatus', 'ListPrice', 'StreetNumber', 'StreetName', 'UnitNumber', 'City',
            'Longitude', 'Latitude', 'DaysOnMarket', 'PropertyType', 'PropertySubType',
            'NumberOfUnitsTotal', 'YearBuilt', 'BuildingAreaTotal', 'BedroomsTotal', 'ParkingTotal'
        ]
        query = f"{API_BASE}/Property?" + "&".join([
            f"$select={','.join(selected_fields)}",
            "$filter=MlsStatus eq 'Active' and PropertyType eq 'ResidentialIncome' and NumberOfUnitsTotal ge 2 and Longitude ne null and Latitude ne null and Latitude ge 32 and Latitude le 35",
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
            progress_bar.progress(min(count / 10000, 1.0))

        mls = pd.DataFrame(all_listings)
        mls.rename(columns={"ListPrice": "CurrentPrice"}, inplace=True)

    with st.spinner("Cleaning data & calculating..."):
        def build_address(r):
            parts = [str(r.get(c, '')) for c in ['StreetNumber', 'StreetName', 'City'] if pd.notna(r.get(c))]
            return ' '.join(parts).strip()

        mls['Address'] = mls.apply(build_address, axis=1)

        valid = mls.dropna(subset=['NumberOfUnitsTotal', 'Longitude', 'Latitude', 'CurrentPrice', 'BuildingAreaTotal', 'BedroomsTotal', 'ParkingTotal', 'YearBuilt'])
        valid = valid[(valid['NumberOfUnitsTotal'] >= 2) & (valid['NumberOfUnitsTotal'] <= 1000)]
        valid = valid[(valid['CurrentPrice'] > 0)]

        # Exclude LA pre-1978
        # valid = valid[~((valid['City'].str.strip().str.lower() == 'los angeles') & (valid['YearBuilt'] < 1978))]
        
        # Normalize city names for lookup (strip, lower, remove extra spaces)
        valid['City_normalized'] = valid['City'].astype(str).str.strip().str.lower()

        # Exclude if the City field matches ANY known LA City neighborhood/community and is built pre-1978
        valid = valid[~valid['City_normalized'].isin(LA_CITY_NEIGHBORHOODS)& (valid['YearBuilt'] < 1978)]

        # Optional: drop the helper column if you don't need it
        valid = valid.drop(columns=['City_normalized'], errors='ignore')

        # Building size and bedrooms
        valid = valid[valid['BuildingAreaTotal'] >= valid['NumberOfUnitsTotal'] * 1000]
        valid = valid[valid['BedroomsTotal'] <= valid['NumberOfUnitsTotal'] * 2]

        # Parking
        valid = valid[valid['ParkingTotal'] >= valid['NumberOfUnitsTotal']]

        # Calculate price per unit
        valid['price_per_unit'] = (valid['CurrentPrice'] / valid['NumberOfUnitsTotal']).round().astype(int)

        # Geo for distance
        gdf_mls = gpd.GeoDataFrame(
            valid,
            geometry=gpd.points_from_xy(valid.Longitude, valid.Latitude),
            crs="EPSG:4326"
        )
        gdf_mls = gdf_mls.to_crs("EPSG:32611")  # UTM 11N for SoCal

        coast_gdf = coast_gdf.to_crs("EPSG:32611")
        coast_boundary = coast_gdf.unary_union.boundary

        gdf_mls['dist_to_coast_m'] = gdf_mls.geometry.distance(coast_boundary)

        gdf_mls['max_ppu'] = np.where(gdf_mls['dist_to_coast_m'] <= 804.672, 600000, 500000)

        # Filter price per unit
        matched = gdf_mls[gdf_mls['price_per_unit'] <= gdf_mls['max_ppu']]

        # Format price per unit display
        matched['price_per_unit_display'] = ((matched['price_per_unit'] / 1000).round(0).astype(int)).astype(str) + 'k'

    # ── Sort ──
    matched = matched.sort_values('price_per_unit', ascending=True)

    # ── Prepare display dataframe ──
    display_df = matched[[
        'Address',
        'price_per_unit_display',
        'CurrentPrice'
    ]].rename(columns={
        'price_per_unit_display': 'Price per Unit',
        'CurrentPrice': 'Purchase Price'
    })

    display_df = display_df.head(750)

    st.success(f"Showing top {len(display_df):,} apartment deals after all filters")
    if len(display_df) < len(matched):
        st.caption(f"(filtered & sorted from {len(matched):,} total matches)")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Address": st.column_config.TextColumn("Address", width="medium"),
            "Price per Unit": st.column_config.TextColumn("Price per Unit", width="small"),
            "Purchase Price": st.column_config.NumberColumn(
                "Purchase Price",
                format="$%d",
            ),
        }
    )

    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download Top Apartment Deals CSV",
        data=csv,
        file_name="apartment_deals.csv",
        mime="text/csv"
    )