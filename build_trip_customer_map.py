from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
BJCTA_PATH = BASE_DIR / "bjcta_para.csv"
ECOLANE_PATH = BASE_DIR / "Ecolane Reservation and Trip Data July 2022 - June 2023.xlsx"
CBG_PATH = BASE_DIR / "tl_2021_01_bg" / "tl_2021_01_bg.shp"
OUT_PATH = BASE_DIR / "trip_customer_address_cbg_map.html"


def combine_address_parts(df: pd.DataFrame, prefix: str) -> pd.Series:
    street_number = df[f"{prefix} Street Number"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
    street = df[f"{prefix} Street"].fillna("").astype(str).str.strip()
    city_col = f"{prefix} City"
    city = df[city_col].fillna("").astype(str).str.strip() if city_col in df.columns else ""
    zip_code = df[f"{prefix} Zipcode"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)

    address = (street_number.str.strip() + " " + street).str.strip()
    if isinstance(city, pd.Series):
        address = address.where(city.eq(""), address + ", " + city)
    address = address.where(zip_code.eq(""), address + ", " + zip_code)
    return address.str.replace(r"\s+", " ", regex=True).str.strip()


def load_bjcta() -> pd.DataFrame:
    df = pd.read_csv(BJCTA_PATH)
    out = pd.DataFrame(
        {
            "dataset": "BJCTA",
            "customer": df["Customer Number"].astype(str),
            "trip": "BJCTA-" + df["Trip ID"].astype(str),
            "date": pd.to_datetime(df["Trip Date"], errors="coerce").dt.strftime("%Y-%m-%d"),
            "status": df["Trip Status"].astype(str).str.strip().str.lower(),
            "purpose": df["Purpose"].fillna("").astype(str),
            "pickup_address": df["pickup_address"].fillna(combine_address_parts(df, "Pick-up")),
            "pickup_lat": pd.to_numeric(df["pickup_lat"], errors="coerce"),
            "pickup_lon": pd.to_numeric(df["pickup_lon"], errors="coerce"),
            "dropoff_address": df["dropoff_address"].fillna(combine_address_parts(df, "Drop-off")),
            "dropoff_lat": pd.to_numeric(df["dropoff_lat"], errors="coerce"),
            "dropoff_lon": pd.to_numeric(df["dropoff_lon"], errors="coerce"),
        }
    )
    return out.dropna(subset=["date"])


def load_ecolane() -> pd.DataFrame:
    df = pd.read_excel(ECOLANE_PATH, sheet_name="SMART Trip Data")
    out = pd.DataFrame(
        {
            "dataset": "Ecolane",
            "customer": df["Customer Number"].astype(str),
            "trip": "Ecolane-" + df["Trip ID"].astype(str),
            "date": pd.to_datetime(df["Trip Date"], errors="coerce").dt.strftime("%Y-%m-%d"),
            "status": df["Trip Status"].astype(str).str.strip().str.lower(),
            "purpose": df["Purpose"].fillna("").astype(str),
            "pickup_address": combine_address_parts(df, "Pick-up"),
            "pickup_lat": pd.to_numeric(df["Pick-up Latitude"], errors="coerce"),
            "pickup_lon": pd.to_numeric(df["Pick-up Longitude"], errors="coerce"),
            "dropoff_address": combine_address_parts(df, "Drop-off"),
            "dropoff_lat": pd.to_numeric(df["Drop-off Latitude"], errors="coerce"),
            "dropoff_lon": pd.to_numeric(df["Drop-off Longitude"], errors="coerce"),
        }
    )
    return out.dropna(subset=["date"])


def make_stop_events(trips: pd.DataFrame) -> pd.DataFrame:
    common = ["dataset", "customer", "trip", "date", "status", "purpose"]
    pickups = trips[common + ["pickup_address", "pickup_lat", "pickup_lon"]].rename(
        columns={"pickup_address": "address", "pickup_lat": "lat", "pickup_lon": "lon"}
    )
    pickups["direction"] = "pickup"

    dropoffs = trips[common + ["dropoff_address", "dropoff_lat", "dropoff_lon"]].rename(
        columns={"dropoff_address": "address", "dropoff_lat": "lat", "dropoff_lon": "lon"}
    )
    dropoffs["direction"] = "dropoff"

    events = pd.concat([pickups, dropoffs], ignore_index=True)
    events = events.dropna(subset=["lat", "lon"])
    events = events[
        events["lat"].between(32.5, 34.5)
        & events["lon"].between(-88.0, -85.0)
        & events["address"].fillna("").ne("")
    ].copy()
    events["lat_round"] = events["lat"].round(6)
    events["lon_round"] = events["lon"].round(6)
    events["location_key"] = (
        events["address"].str.upper().str.replace(r"\s+", " ", regex=True).str.strip()
        + "|"
        + events["lat_round"].astype(str)
        + "|"
        + events["lon_round"].astype(str)
    )
    return events


def attach_cbg(events: pd.DataFrame, cbg: gpd.GeoDataFrame) -> pd.DataFrame:
    points = gpd.GeoDataFrame(
        events.reset_index(names="event_id"),
        geometry=gpd.points_from_xy(events["lon"], events["lat"]),
        crs="EPSG:4326",
    ).to_crs(cbg.crs)
    joined = gpd.sjoin(points[["event_id", "geometry"]], cbg[["GEOID", "geometry"]], how="left", predicate="within")
    geoid = joined.dropna(subset=["GEOID"]).drop_duplicates("event_id").set_index("event_id")["GEOID"]
    events = events.reset_index(drop=True)
    events["geoid"] = events.index.map(geoid).fillna("")
    return events


def compact_payload(events: pd.DataFrame, cbg_geojson: dict) -> dict:
    dates = sorted(events["date"].dropna().unique().tolist())
    dataset_values = ["BJCTA", "Ecolane"]
    direction_values = ["pickup", "dropoff"]
    status_values = sorted(events["status"].fillna("").unique().tolist())

    date_index = {value: idx for idx, value in enumerate(dates)}
    dataset_index = {value: idx for idx, value in enumerate(dataset_values)}
    direction_index = {value: idx for idx, value in enumerate(direction_values)}
    status_index = {value: idx for idx, value in enumerate(status_values)}
    customer_index = {value: idx for idx, value in enumerate(sorted(events["customer"].astype(str).unique()))}

    locations = (
        events.groupby("location_key", as_index=False)
        .agg(address=("address", "first"), lat=("lat_round", "first"), lon=("lon_round", "first"))
        .sort_values(["address", "lat", "lon"])
        .reset_index(drop=True)
    )
    location_index = {value: idx for idx, value in enumerate(locations["location_key"])}

    encoded_events = []
    for row in events.itertuples(index=False):
        encoded_events.append(
            [
                dataset_index[row.dataset],
                direction_index[row.direction],
                date_index[row.date],
                customer_index[str(row.customer)],
                location_index[row.location_key],
                row.geoid,
                status_index[row.status],
            ]
        )

    return {
        "dates": dates,
        "datasets": dataset_values,
        "directions": direction_values,
        "statuses": status_values,
        "locations": locations[["address", "lat", "lon"]].values.tolist(),
        "events": encoded_events,
        "cbg": cbg_geojson,
    }


def build_html(payload: dict) -> str:
    payload_json = json.dumps(payload, separators=(",", ":"))
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trip and Customer Map by Address and CBG</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; font-family: Arial, sans-serif; }}
    .panel {{
      position: absolute; top: 12px; left: 12px; z-index: 1000; width: 330px;
      background: rgba(255, 255, 255, 0.96); border-radius: 8px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.22); padding: 12px;
    }}
    .panel h1 {{ font-size: 16px; margin: 0 0 10px; }}
    .row {{ display: grid; grid-template-columns: 96px 1fr; gap: 8px; align-items: center; margin: 8px 0; }}
    label {{ font-size: 12px; font-weight: 700; color: #333; }}
    select, input {{ width: 100%; box-sizing: border-box; font-size: 12px; padding: 5px; }}
    button {{ cursor: pointer; padding: 7px 10px; border: 0; border-radius: 6px; background: #284b63; color: white; }}
    .summary {{ margin-top: 10px; font-size: 12px; line-height: 1.45; color: #222; }}
    .legend {{ background: rgba(255,255,255,.95); padding: 8px; border-radius: 6px; line-height: 1.35; font-size: 12px; }}
    .legend span {{ display: inline-block; width: 13px; height: 13px; margin-right: 5px; vertical-align: middle; }}
    .muted {{ color: #666; font-size: 11px; }}
    .leaflet-popup-content {{ font-size: 12px; }}
  </style>
</head>
<body>
<div id="map"></div>
<div class="panel">
  <h1>Trips and Customers</h1>
  <div class="row"><label for="layerMode">Map level</label><select id="layerMode"><option value="address">Address points</option><option value="cbg">CBG blocks</option></select></div>
  <div class="row"><label for="dataset">Dataset</label><select id="dataset"><option value="all">Both datasets</option><option value="0">BJCTA</option><option value="1">Ecolane</option></select></div>
  <div class="row"><label for="direction">Address type</label><select id="direction"><option value="all">Pickup + dropoff</option><option value="0">Pickup only</option><option value="1">Dropoff only</option></select></div>
  <div class="row"><label for="status">Status</label><select id="status"><option value="all">All statuses</option></select></div>
  <div class="row"><label for="startDate">Start date</label><input id="startDate" type="date"></div>
  <div class="row"><label for="endDate">End date</label><input id="endDate" type="date"></div>
  <div class="row"><label>Quick range</label><div><button id="oneDay">1 day</button> <button id="oneMonth">1 month</button> <button id="sixMonths">6 months</button></div></div>
  <div class="summary" id="summary"></div>
  <div class="muted">Trips are counted as address stop events. Customers are distinct customers in the selected filter.</div>
</div>
<script>
const DATA = {payload_json};
const map = L.map('map').setView([33.52, -86.80], 10);
L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}}).addTo(map);

let activeLayer = L.layerGroup().addTo(map);
let legend = L.control({{position: 'bottomright'}});
legend.onAdd = function() {{
  const div = L.DomUtil.create('div', 'legend');
  div.innerHTML = '<b>Trips</b><br><span style="background:#f7fbff"></span>Low<br><span style="background:#6baed6"></span>Medium<br><span style="background:#08306b"></span>High';
  return div;
}};
legend.addTo(map);

const dateMin = DATA.dates[0];
const dateMax = DATA.dates[DATA.dates.length - 1];
const startInput = document.getElementById('startDate');
const endInput = document.getElementById('endDate');
startInput.min = dateMin; startInput.max = dateMax; startInput.value = dateMin;
endInput.min = dateMin; endInput.max = dateMax; endInput.value = dateMax;

const statusSelect = document.getElementById('status');
DATA.statuses.forEach((status, idx) => {{
  const option = document.createElement('option');
  option.value = String(idx);
  option.textContent = status || '<blank>';
  statusSelect.appendChild(option);
}});

function addDays(dateString, days) {{
  const date = new Date(dateString + 'T00:00:00');
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}}

function colorScale(value, maxValue) {{
  if (!value) return '#f7fbff';
  const ratio = Math.min(1, value / Math.max(1, maxValue));
  if (ratio > 0.70) return '#08306b';
  if (ratio > 0.45) return '#2171b5';
  if (ratio > 0.22) return '#6baed6';
  if (ratio > 0.08) return '#c6dbef';
  return '#eff3ff';
}}

function passesFilter(event) {{
  const dataset = document.getElementById('dataset').value;
  const direction = document.getElementById('direction').value;
  const status = document.getElementById('status').value;
  const date = DATA.dates[event[2]];
  if (dataset !== 'all' && event[0] !== Number(dataset)) return false;
  if (direction !== 'all' && event[1] !== Number(direction)) return false;
  if (status !== 'all' && event[6] !== Number(status)) return false;
  return date >= startInput.value && date <= endInput.value;
}}

function aggregateByLocation() {{
  const stats = new Map();
  let totalTrips = 0;
  const allCustomers = new Set();
  for (const event of DATA.events) {{
    if (!passesFilter(event)) continue;
    const loc = event[4];
    if (!stats.has(loc)) stats.set(loc, {{trips: 0, customers: new Set()}});
    const item = stats.get(loc);
    item.trips += 1;
    item.customers.add(event[3]);
    totalTrips += 1;
    allCustomers.add(event[3]);
  }}
  return {{stats, totalTrips, totalCustomers: allCustomers.size}};
}}

function aggregateByCbg() {{
  const stats = new Map();
  let totalTrips = 0;
  const allCustomers = new Set();
  for (const event of DATA.events) {{
    if (!passesFilter(event) || !event[5]) continue;
    const geoid = event[5];
    if (!stats.has(geoid)) stats.set(geoid, {{trips: 0, customers: new Set()}});
    const item = stats.get(geoid);
    item.trips += 1;
    item.customers.add(event[3]);
    totalTrips += 1;
    allCustomers.add(event[3]);
  }}
  return {{stats, totalTrips, totalCustomers: allCustomers.size}};
}}

function renderAddressLayer() {{
  const result = aggregateByLocation();
  const values = [...result.stats.values()].map(v => v.trips);
  const maxTrips = values.length ? Math.max(...values) : 1;
  for (const [locIdx, item] of result.stats.entries()) {{
    const loc = DATA.locations[locIdx];
    const radius = Math.max(4, Math.min(22, 3 + Math.sqrt(item.trips) * 0.55));
    const marker = L.circleMarker([loc[1], loc[2]], {{
      radius,
      color: '#17324d',
      weight: 1,
      fillColor: colorScale(item.trips, maxTrips),
      fillOpacity: 0.72
    }});
    marker.bindPopup(`<b>${{loc[0]}}</b><br>Trips: ${{item.trips.toLocaleString()}}<br>Customers: ${{item.customers.size.toLocaleString()}}`);
    marker.addTo(activeLayer);
  }}
  document.getElementById('summary').innerHTML =
    `Visible addresses: <b>${{result.stats.size.toLocaleString()}}</b><br>` +
    `Trips: <b>${{result.totalTrips.toLocaleString()}}</b><br>` +
    `Customers: <b>${{result.totalCustomers.toLocaleString()}}</b>`;
}}

function renderCbgLayer() {{
  const result = aggregateByCbg();
  const values = [...result.stats.values()].map(v => v.trips);
  const maxTrips = values.length ? Math.max(...values) : 1;
  L.geoJSON(DATA.cbg, {{
    style: feature => {{
      const item = result.stats.get(feature.properties.GEOID) || {{trips: 0}};
      return {{
        color: '#333',
        weight: 0.5,
        fillColor: colorScale(item.trips, maxTrips),
        fillOpacity: item.trips ? 0.68 : 0.12
      }};
    }},
    onEachFeature: (feature, layer) => {{
      const item = result.stats.get(feature.properties.GEOID) || {{trips: 0, customers: new Set()}};
      layer.bindPopup(`<b>CBG ${{feature.properties.GEOID}}</b><br>Trips: ${{item.trips.toLocaleString()}}<br>Customers: ${{item.customers.size.toLocaleString()}}`);
    }}
  }}).addTo(activeLayer);
  document.getElementById('summary').innerHTML =
    `Visible CBGs: <b>${{result.stats.size.toLocaleString()}}</b><br>` +
    `Trips mapped to CBG: <b>${{result.totalTrips.toLocaleString()}}</b><br>` +
    `Customers: <b>${{result.totalCustomers.toLocaleString()}}</b>`;
}}

function render() {{
  activeLayer.clearLayers();
  if (startInput.value > endInput.value) endInput.value = startInput.value;
  if (document.getElementById('layerMode').value === 'address') renderAddressLayer();
  else renderCbgLayer();
}}

document.querySelectorAll('select,input').forEach(el => el.addEventListener('change', render));
document.getElementById('oneDay').addEventListener('click', () => {{ endInput.value = startInput.value; render(); }});
document.getElementById('oneMonth').addEventListener('click', () => {{
  const end = addDays(startInput.value, 30);
  endInput.value = end <= dateMax ? end : dateMax;
  render();
}});
document.getElementById('sixMonths').addEventListener('click', () => {{
  const end = addDays(startInput.value, 183);
  endInput.value = end <= dateMax ? end : dateMax;
  render();
}});
render();
</script>
</body>
</html>
"""


def main() -> None:
    print("Loading trip tables...")
    trips = pd.concat([load_bjcta(), load_ecolane()], ignore_index=True)
    events = make_stop_events(trips)
    print(f"Stop events with coordinates: {len(events):,}")

    print("Loading Jefferson County CBG polygons...")
    cbg = gpd.read_file(CBG_PATH)
    cbg = cbg[(cbg["STATEFP"] == "01") & (cbg["COUNTYFP"] == "073")].copy()
    cbg = cbg.to_crs("EPSG:4326")
    cbg["geometry"] = cbg.geometry.simplify(0.00035, preserve_topology=True)

    print("Assigning stop events to CBGs...")
    events = attach_cbg(events, cbg)
    print(f"Events mapped to CBGs: {events['geoid'].ne('').sum():,} / {len(events):,}")

    cbg_geojson = json.loads(cbg[["GEOID", "geometry"]].to_json())
    payload = compact_payload(events, cbg_geojson)

    print("Writing HTML...")
    OUT_PATH.write_text(build_html(payload), encoding="utf-8")
    size_mb = OUT_PATH.stat().st_size / 1024**2
    print(f"Wrote {OUT_PATH} ({size_mb:,.1f} MB)")


if __name__ == "__main__":
    main()
