"""
Quick Milan Heatmap - Fixed version with cellId mapping
Improved: Softer green for better map visibility, strong red/orange for hotspots
"""

import pandas as pd
import json
import folium
from folium.plugins import HeatMap
from branca.colormap import linear
from sqlalchemy import create_engine
import os

print("🗺️ Creating Milan Interactive Heatmap...")
print("="*50)

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# 1. Load traffic data
print("📊 Loading traffic data from database...")
df_traffic = pd.read_sql("""
    SELECT 
        square_id,
        SUM(internet_traffic) as total_traffic,
        AVG(internet_traffic) as avg_traffic
    FROM cdr_hourly
    GROUP BY square_id
    ORDER BY total_traffic DESC
""", engine)

print(f"   Loaded {len(df_traffic)} grid cells")
if not df_traffic.empty:
    print(f"   Top grid: {df_traffic.iloc[0]['square_id']} with traffic {df_traffic.iloc[0]['total_traffic']:.0f}")

# 2. Load GeoJSON (cari file yang ada)
geojson_candidates = [
    'data/raw/milan_grid_manual.geojson',
    'data/raw/milano-grid.geojson',
    'data/raw/milano.grid.geojson'
]

geojson_path = None
for candidate in geojson_candidates:
    if os.path.exists(candidate):
        geojson_path = candidate
        break

if geojson_path is None:
    print("❌ No GeoJSON file found!")
    exit(1)

print(f"📁 Using grid: {geojson_path}")

with open(geojson_path, 'r') as f:
    milan_grid = json.load(f)

print(f"   Grid cells in file: {len(milan_grid['features'])}")

# 3. Create traffic dictionary (square_id -> total_traffic)
traffic_dict = dict(zip(df_traffic['square_id'].astype(int), df_traffic['total_traffic']))

# 4. Match and add traffic data to grid properties
print("🔄 Matching traffic data with grid cells...")
matched = 0
for feature in milan_grid['features']:
    # Get grid ID from cellId property
    grid_id = feature['properties'].get('cellId')
    
    if grid_id is not None:
        traffic = traffic_dict.get(int(grid_id), 0)
        feature['properties']['traffic'] = float(traffic)
        if traffic > 0:
            matched += 1
    else:
        feature['properties']['traffic'] = 0

print(f"   Matched {matched} grid cells with traffic data")

# Get min/max for colormap
valid_traffics = [f['properties']['traffic'] for f in milan_grid['features'] if f['properties']['traffic'] > 0]
if valid_traffics:
    min_traffic = min(valid_traffics)
    max_traffic = max(valid_traffics)
else:
    min_traffic, max_traffic = 0, 1

print(f"   Traffic range: {min_traffic:.0f} - {max_traffic:.0f}")

# 5. Create map with better basemap and zoom
milan_center = [45.4642, 9.1900]
m = folium.Map(
    location=milan_center, 
    zoom_start=13,
    tiles='OpenStreetMap',
    control_scale=True
)

# Add basemap options
folium.TileLayer('CartoDB positron', name='Light Mode').add_to(m)

# Add title
title_html = '''
<div style="position: fixed; top: 10px; left: 10px; z-index: 1000; background: white; padding: 8px 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
    <h4 style="margin: 0;">📊 Milan Telecom Traffic Heatmap</h4>
    <small>Internet Traffic Intensity | Indosat Ooredoo Analysis</small>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Add choropleth layer with SOFTER GREEN for background visibility
folium.GeoJson(
    milan_grid,
    name='Traffic Intensity',
    style_function=lambda feature: {
        'fillColor': '#e03131' if feature['properties'].get('traffic', 0) > max_traffic * 0.7 else
                     '#fd7e14' if feature['properties'].get('traffic', 0) > max_traffic * 0.4 else
                     '#fcc419' if feature['properties'].get('traffic', 0) > max_traffic * 0.1 else
                     '#c8e6c9',  # Soft green (almost pastel, map visible underneath)
        'color': '#666666',
        'weight': 0.6,
        'fillOpacity': 0.35 if feature['properties'].get('traffic', 0) < max_traffic * 0.1 else 0.65,
        'opacity': 0.7,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['cellId', 'traffic'],
        aliases=['Grid ID:', 'Traffic:'],
        localize=True,
        sticky=False
    ),
    popup=folium.GeoJsonPopup(
        fields=['cellId', 'traffic'],
        aliases=['🚏 Grid ID:', '📊 Total Traffic:'],
        localize=True
    )
).add_to(m)

# Add colormap
colormap = linear.YlOrRd_09.scale(min_traffic, max_traffic)
colormap.caption = 'Internet Traffic Intensity (Higher = More Red)'
colormap.add_to(m)

# Layer control
folium.LayerControl().add_to(m)

# Save
os.makedirs('images_indosat', exist_ok=True)
output_path = 'images_indosat/milan_traffic_heatmap.html'
m.save(output_path)
print(f"\n✅ Heatmap saved: {output_path}")
print(f"   Open in browser: open {output_path}")

# Statistics
print("\n📊 FINAL STATISTICS:")
print(f"   Total grids with traffic: {matched}")
print(f"   Max traffic: {max_traffic:.0f}")
print(f"   Min traffic: {min_traffic:.0f}")
print(f"\n🏆 Top 5 busiest grids:")
top5 = df_traffic.head(5)
for i, row in top5.iterrows():
    print(f"   Grid {int(row['square_id'])}: {row['total_traffic']:.0f} traffic")