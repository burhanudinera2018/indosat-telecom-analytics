"""
Clustering Milan Grid Cells based on Internet Traffic Patterns
Indosat Ooredoo Data Science Portfolio
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import os
import json
import folium

print("="*60)
print("🗺️ CLUSTERING MILAN GRID CELLS BY TRAFFIC PATTERN")
print("="*60)

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# 1. Load data: rata-rata traffic per grid per jam
print("\n📊 Loading hourly traffic data...")
df = pd.read_sql("""
    SELECT 
        square_id,
        EXTRACT(HOUR FROM hour) as hour_of_day,
        AVG(internet_traffic) as avg_traffic
    FROM cdr_hourly
    GROUP BY square_id, EXTRACT(HOUR FROM hour)
    ORDER BY square_id, hour_of_day
""", engine)

print(f"   Loaded {len(df)} records")
print(f"   Grid cells: {df['square_id'].nunique()}")
print(f"   Hours: {df['hour_of_day'].nunique()}")

# 2. Pivot table: grid sebagai baris, jam sebagai kolom
print("\n📊 Creating pivot table (grids × hours)...")
pivot_df = df.pivot(index='square_id', columns='hour_of_day', values='avg_traffic')
pivot_df = pivot_df.fillna(0)  # Isi missing dengan 0

print(f"   Shape: {pivot_df.shape[0]} grids × {pivot_df.shape[1]} hours")
print(f"   Columns (hours): {list(pivot_df.columns.astype(int))}")

# 3. Normalisasi data (StandardScaler)
print("\n📊 Normalizing data...")
scaler = StandardScaler()
data_scaled = scaler.fit_transform(pivot_df)
print(f"   Data scaled: {data_scaled.shape}")

# 4. Menentukan jumlah cluster optimal (Elbow Method)
print("\n📊 Finding optimal number of clusters (Elbow Method)...")
inertias = []
silhouette_scores = []
K_range = range(2, 11)

for k in K_range:
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(data_scaled)
    inertias.append(kmeans.inertia_)
    silhouette_scores.append(silhouette_score(data_scaled, kmeans.labels_))
    print(f"   K={k}: Inertia={kmeans.inertia_:.0f}, Silhouette={silhouette_scores[-1]:.3f}")

# 5. Pilih K optimal (berdasarkan elbow dan silhouette tertinggi)
optimal_k = K_range[np.argmax(silhouette_scores)]
print(f"\n✅ Optimal K = {optimal_k} (highest silhouette score: {max(silhouette_scores):.3f})")

# 6. Jalankan clustering final
print(f"\n📊 Running final clustering with K={optimal_k}...")
kmeans_final = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
clusters = kmeans_final.fit_predict(data_scaled)

# Tambahkan label cluster ke pivot_df
pivot_df['cluster'] = clusters
print(f"   Cluster distribution:")
for c in range(optimal_k):
    count = (clusters == c).sum()
    print(f"      Cluster {c}: {count} grids ({count/len(clusters)*100:.1f}%)")

# 7. Interpretasi cluster berdasarkan pola traffic
print("\n📊 Creating cluster profiles...")

# Hitung rata-rata traffic per jam per cluster
cluster_profiles = []
for c in range(optimal_k):
    cluster_data = pivot_df[pivot_df['cluster'] == c].drop('cluster', axis=1)
    cluster_mean = cluster_data.mean().values
    cluster_profiles.append(cluster_mean)

cluster_profiles_df = pd.DataFrame(
    cluster_profiles,
    columns=pivot_df.columns[:-1],  # exclude cluster column
    index=[f'Cluster {c}' for c in range(optimal_k)]
)

# 8. Visualisasi: Elbow & Silhouette
print("\n📊 Generating visualization charts...")
os.makedirs('images_indosat', exist_ok=True)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Elbow plot
axes[0].plot(K_range, inertias, 'bo-', linewidth=2, markersize=8)
axes[0].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
axes[0].set_xlabel('Number of Clusters (K)', fontsize=12)
axes[0].set_ylabel('Inertia (Within-cluster sum of squares)', fontsize=12)
axes[0].set_title('Elbow Method for Optimal K', fontsize=14)
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Silhouette score
axes[1].plot(K_range, silhouette_scores, 'go-', linewidth=2, markersize=8)
axes[1].axvline(x=optimal_k, color='r', linestyle='--', label=f'Optimal K={optimal_k}')
axes[1].set_xlabel('Number of Clusters (K)', fontsize=12)
axes[1].set_ylabel('Silhouette Score', fontsize=12)
axes[1].set_title('Silhouette Score for Optimal K', fontsize=14)
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('images_indosat/clustering_optimal_k.png', dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ Saved: images_indosat/clustering_optimal_k.png")

# 9. Visualisasi: Cluster Profiles (traffic pattern per cluster)
fig, ax = plt.subplots(figsize=(14, 7))

# Plot profile setiap cluster
for c in range(optimal_k):
    profile = cluster_profiles_df.loc[f'Cluster {c}']
    ax.plot(profile.index, profile.values, linewidth=2, marker='o', markersize=4, label=f'Cluster {c}')

ax.set_xlabel('Hour of Day', fontsize=12)
ax.set_ylabel('Average Internet Traffic (normalized)', fontsize=12)
ax.set_title(f'Traffic Patterns by Cluster (K={optimal_k})', fontsize=14)
ax.legend(loc='upper right')
ax.grid(True, alpha=0.3)
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f'{h}:00' for h in range(0, 24, 2)])

plt.tight_layout()
plt.savefig('images_indosat/cluster_profiles.png', dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ Saved: images_indosat/cluster_profiles.png")

# 10. Heatmap cluster profiles
fig, ax = plt.subplots(figsize=(12, 6))
sns.heatmap(cluster_profiles_df, cmap='YlOrRd', ax=ax, cbar_kws={'label': 'Traffic Intensity'})
ax.set_xlabel('Hour of Day', fontsize=12)
ax.set_ylabel('Cluster', fontsize=12)
ax.set_title(f'Cluster Traffic Patterns Heatmap (K={optimal_k})', fontsize=14)
ax.set_xticks(range(0, 24, 2))
ax.set_xticklabels([f'{h}:00' for h in range(0, 24, 2)])

plt.tight_layout()
plt.savefig('images_indosat/cluster_heatmap.png', dpi=150, bbox_inches='tight')
plt.close()
print("   ✅ Saved: images_indosat/cluster_heatmap.png")

# 11. Tampilkan statistik per cluster
print("\n📊 CLUSTER STATISTICS:")
for c in range(optimal_k):
    cluster_grids = pivot_df[pivot_df['cluster'] == c]
    peak_hour = cluster_grids.drop('cluster', axis=1).mean().idxmax()
    peak_value = cluster_grids.drop('cluster', axis=1).mean().max()
    print(f"\n   🏷️  Cluster {c}: {len(cluster_grids)} grids")
    print(f"      Peak hour: {int(peak_hour)}:00 (traffic: {peak_value:.1f})")
    print(f"      Traffic range: {cluster_grids.drop('cluster', axis=1).values.min():.1f} - {cluster_grids.drop('cluster', axis=1).values.max():.1f}")

# 12. Peta Clustering (jika GeoJSON tersedia)
print("\n🗺️ Generating cluster map...")

# Load GeoJSON
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

if geojson_path:
    with open(geojson_path, 'r') as f:
        milan_grid = json.load(f)
    
    # Create cluster dictionary
    cluster_dict = dict(zip(pivot_df.index.astype(int), pivot_df['cluster']))
    
    # Add cluster to geojson properties
    for feature in milan_grid['features']:
        grid_id = feature['properties'].get('cellId')
        if grid_id is not None:
            cluster = cluster_dict.get(int(grid_id), -1)
            feature['properties']['cluster'] = int(cluster)
        else:
            feature['properties']['cluster'] = -1
    
    # Warna untuk setiap cluster
    cluster_colors = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf', '#999999']
    
    m = folium.Map(location=[45.4642, 9.1900], zoom_start=12, tiles='CartoDB positron', control_scale=True)
    
    # Add cluster layer
    folium.GeoJson(
        milan_grid,
        name='Grid Clusters',
        style_function=lambda feature: {
            'fillColor': cluster_colors[feature['properties'].get('cluster', 0) % len(cluster_colors)],
            'color': 'black',
            'weight': 0.5,
            'fillOpacity': 0.5,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=['cellId', 'cluster'],
            aliases=['Grid ID:', 'Cluster:'],
            localize=True
        )
    ).add_to(m)
    
    folium.LayerControl().add_to(m)
    cluster_map_path = 'images_indosat/milan_cluster_map.html'
    m.save(cluster_map_path)
    print(f"   ✅ Cluster map saved: {cluster_map_path}")
else:
    print("   ⚠️ GeoJSON not found, cluster map skipped")

# 13. Interpretasi bisnis
print("\n" + "="*60)
print("💼 BUSINESS INSIGHTS & RECOMMENDATIONS")
print("="*60)

print(f"""
Berdasarkan clustering {optimal_k} segmen area di Milan:

""" + "\n".join([f"""
📌 Cluster {c}: {len(pivot_df[pivot_df['cluster'] == c])} grids ({len(pivot_df[pivot_df['cluster'] == c])/len(pivot_df)*100:.1f}%)
   • Peak hour: {int(cluster_profiles_df.loc[f'Cluster {c}'].idxmax())}:00
   • Karakteristik: {'Area bisnis padat (siang & malam)' if cluster_profiles_df.loc[f'Cluster {c}'].max() > 1 else 'Area residensial' if cluster_profiles_df.loc[f'Cluster {c}'].max() < 0.5 else 'Area campuran'}
   • Rekomendasi: {'Prioritas investasi BTS & paket unlimited malam' if cluster_profiles_df.loc[f'Cluster {c}'].idxmax() > 18 else 'Fokus paket keluarga & bundling device'}
""" for c in range(optimal_k)]))

print("\n🎯 TOP RECOMMENDATIONS FOR INDOSAT OOREDOO:")
print("   1. Cluster dengan peak malam → Luncurkan 'Paket Unlimited Malam' (21:00-06:00)")
print("   2. Cluster dengan peak siang → Fokus pada paket bisnis & corporate")
print("   3. Cluster residensial → Bundling dengan layanan hiburan (OTT, game)")
print("   4. Cluster campuran → Dynamic pricing berdasarkan jam penggunaan")

print("\n" + "="*60)
print("🎉 CLUSTERING COMPLETED!")
print("="*60)
print("\n📁 Output files:")
print("   images_indosat/clustering_optimal_k.png")
print("   images_indosat/cluster_profiles.png")
print("   images_indosat/cluster_heatmap.png")
if geojson_path:
    print("   images_indosat/milan_cluster_map.html")