# Buat file src/milan_heatmap.py
import pandas as pd
import json
import folium
from folium.plugins import HeatMap
from branca.colormap import linear
from sqlalchemy import create_engine, text

print("🗺️ Creating Milan Interactive Heatmap...")
print("="*50)

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# 1. Load traffic data per grid
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
print(f"   Top grid: {df_traffic.iloc[0]['square_id']} with traffic {df_traffic.iloc[0]['total_traffic']:.0f}")

# 2. Load grid geojson
geojson_files = [
    'data/raw/milano.grid.geojson',
    'data/raw/milano_grid.geojson', 
    'data/raw/milan_grid.geojson',
    'data/raw/milan_grid_manual.geojson'
]

geojson_path = None
for f in geojson_files:
    import os
    if os.path.exists(f):
        geojson_path = f
        break

if geojson_path is None:
    print("❌ No grid geojson file found. Creating manual grid...")
    # Create manual grid (as in Opsi B above)
    # ... (kode untuk membuat manual grid)
    geojson_path = 'data/raw/milan_grid_manual.geojson'

print(f"📁 Using grid: {geojson_path}")

# 3. Baca geojson
with open(geojson_path, 'r') as f:
    milan_grid = json.load(f)

print(f"   Grid cells in geojson: {len(milan_grid['features'])}")

# 4. Match traffic data dengan grid cells
print("🔄 Matching traffic data with grid cells...")

# Extract grid IDs from geojson
for feature in milan_grid['features']:
    # Try different property names for ID
    grid_id = feature['properties'].get('id') or \
              feature['properties'].get('Id') or \
              feature['properties'].get('square_id') or \
              feature['properties'].get('cell_id')
    
    if grid_id is None:
        # Jika tidak ada ID, gunakan index sebagai ID
        grid_id = feature['properties'].get('cartodb_id', idx + 1)
    
    # Find traffic data for this grid
    traffic_row = df_traffic[df_traffic['square_id'] == int(grid_id)]
    if not traffic_row.empty:
        feature['properties']['traffic'] = float(traffic_row.iloc[0]['total_traffic'])
        feature['properties']['avg_traffic'] = float(traffic_row.iloc[0]['avg_traffic'])
    else:
        feature['properties']['traffic'] = 0
        feature['properties']['avg_traffic'] = 0

# 5. Buat peta
print("🗺️ Generating interactive map...")

# Center of Milan
milan_center = [45.4642, 9.1900]

# Create map
m = folium.Map(
    location=milan_center,
    zoom_start=12,
    tiles='CartoDB positron',
    control_scale=True
)

# Add title
title_html = '''
<div style="position: fixed; top: 10px; left: 10px; z-index: 1000; background: white; padding: 10px 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
    <h3>📊 Milan Telecom Traffic Heatmap</h3>
    <p>Internet traffic intensity by grid cell | <strong>Indosat Ooredoo</strong></p>
</div>
'''
m.get_root().html.add_child(folium.Element(title_html))

# Color mapping
min_traffic = df_traffic['total_traffic'].min()
max_traffic = df_traffic['total_traffic'].max()
colormap = linear.YlOrRd_09.scale(min_traffic, max_traffic)
colormap.caption = 'Internet Traffic Intensity'

# Add grid cells as choropleth
folium.GeoJson(
    milan_grid,
    name='Traffic Intensity',
    style_function=lambda feature: {
        'fillColor': colormap(feature['properties'].get('traffic', 0)),
        'color': 'black',
        'weight': 0.5,
        'fillOpacity': 0.7,
        'dashArray': '5,5'
    },
    tooltip=folium.GeoJsonTooltip(
        fields=['id', 'traffic', 'avg_traffic'],
        aliases=['Grid ID:', 'Total Traffic:', 'Avg Traffic:'],
        localize=True,
        sticky=False,
        labels=True
    ),
    popup=folium.GeoJsonPopup(
        fields=['id', 'traffic', 'avg_traffic'],
        aliases=['🚏 Grid ID:', '📊 Total Traffic:', '📈 Avg Traffic:'],
        localize=True,
        sticky=False
    )
).add_to(m)

# Add heatmap layer (alternative visualization)
heat_data = []
for feature in milan_grid['features']:
    if feature['properties'].get('traffic', 0) > 0:
        # Get center of polygon (approximate)
        coords = feature['geometry']['coordinates'][0]
        center_lat = sum(c[1] for c in coords) / len(coords)
        center_lon = sum(c[0] for c in coords) / len(coords)
        heat_data.append([center_lat, center_lon, feature['properties']['traffic']])

HeatMap(heat_data, radius=15, blur=10, max_zoom=13).add_to(m)

# Add colormap legend
colormap.add_to(m)

# Add layer control
folium.LayerControl().add_to(m)

# Save map
output_path = 'images/milan_traffic_heatmap.html'
m.save(output_path)
print(f"\n✅ Heatmap saved: {output_path}")
print(f"   Open in browser: open {output_path}")

# 6. Tampilkan statistik
print("\n📊 STATISTICS:")
print(f"   Total grids analyzed: {len([f for f in milan_grid['features'] if f['properties'].get('traffic', 0) > 0])}")
print(f"   Maximum traffic: {max_traffic:.0f}")
print(f"   Minimum traffic: {min_traffic:.0f}")
print(f"   Top 5 busiest grids:")
top5 = df_traffic.head(5)
for i, row in top5.iterrows():
    print(f"      Grid {int(row['square_id'])}: {row['total_traffic']:.0f} traffic")