# src/create_static_map.py
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import json
import numpy as np

def create_static_map():
    """Create static PNG map of Milan traffic"""
    
    print("🗺️ Creating static map PNG...")
    
    # Load grid
    with open('data/raw/milan_grid_manual.geojson', 'r') as f:
        grid = json.load(f)
    
    # Create figure
    fig, ax = plt.subplots(1, 1, figsize=(12, 10))
    
    patches = []
    traffic_values = []
    
    for feature in grid['features']:
        coords = feature['geometry']['coordinates'][0]
        polygon = Polygon(coords, closed=True)
        patches.append(polygon)
        traffic_values.append(feature['properties'].get('traffic', 0))
    
    # Create patch collection
    p = PatchCollection(patches, cmap='YlOrRd', alpha=0.7, edgecolor='black', linewidth=0.5)
    p.set_array(np.array(traffic_values))
    ax.add_collection(p)
    
    # Set limits
    ax.set_xlim(9.0, 9.5)
    ax.set_ylim(45.2, 45.7)
    
    ax.set_xlabel('Longitude', fontsize=12)
    ax.set_ylabel('Latitude', fontsize=12)
    ax.set_title('Milan Telecom Traffic by Grid Cell\nIndosat Ooredoo Network Analysis', fontsize=14, fontweight='bold')
    
    # Add colorbar
    cbar = plt.colorbar(p, ax=ax)
    cbar.set_label('Internet Traffic Intensity', fontsize=10)
    
    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    plt.savefig('images/milan_traffic_static_map.png', dpi=200, bbox_inches='tight')
    print("✅ Static map saved: images/milan_traffic_static_map.png")

if __name__ == "__main__":
    create_static_map()