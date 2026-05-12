"""
EDA for Milan Telecom Dataset
Indosat Ooredoo Data Science Portfolio
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine, text

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# 1. Load data dari database
print("📊 Loading data from PostgreSQL...")
df = pd.read_sql("""
    SELECT 
        hour,
        square_id,
        internet_traffic
    FROM cdr_hourly
    WHERE square_id <= 500
    ORDER BY hour, square_id
""", engine)

print(f"   Loaded {len(df):,} records")
print(f"   Date range: {df['hour'].min()} to {df['hour'].max()}")
print(f"   Unique grids: {df['square_id'].nunique()}")

# 2. Daily pattern (aggregasi per jam)
print("\n📈 Analyzing daily traffic pattern...")
hourly_pattern = df.groupby(df['hour'].dt.hour)['internet_traffic'].mean()

# 3. Visualisasi
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Daily pattern
ax1 = axes[0, 0]
hourly_pattern.plot(kind='line', marker='o', ax=ax1, color='#2ecc71', linewidth=2)
ax1.set_title('Internet Traffic Pattern (24 Hours)', fontsize=12, fontweight='bold')
ax1.set_xlabel('Hour of Day')
ax1.set_ylabel('Avg Internet Traffic')
ax1.grid(True, alpha=0.3)

# Plot 2: Distribution of internet traffic
ax2 = axes[0, 1]
df['internet_traffic'].hist(bins=50, ax=ax2, color='#3498db', edgecolor='black', alpha=0.7)
ax2.set_title('Distribution of Internet Traffic', fontsize=12, fontweight='bold')
ax2.set_xlabel('Internet Traffic')
ax2.set_ylabel('Frequency')
ax2.set_xlim(0, df['internet_traffic'].quantile(0.95))

# Plot 3: Top 20 busiest grid cells
ax3 = axes[1, 0]
busiest_grids = df.groupby('square_id')['internet_traffic'].sum().nlargest(20)
busiest_grids.plot(kind='barh', ax=ax3, color='#e74c3c')
ax3.set_title('Top 20 Busiest Grid Cells (Total Traffic)', fontsize=12, fontweight='bold')
ax3.set_xlabel('Total Internet Traffic')

# Plot 4: Hourly heatmap (sample top grids)
ax4 = axes[1, 1]
# Pilih 10 grid dengan traffic tertinggi
top10_grids = df.groupby('square_id')['internet_traffic'].sum().nlargest(10).index
df_top10 = df[df['square_id'].isin(top10_grids)]
pivot = df_top10.pivot_table(index='square_id', columns=df_top10['hour'].dt.hour, 
                              values='internet_traffic', aggfunc='mean')
sns.heatmap(pivot, ax=ax4, cmap='YlOrRd', annot=True, fmt='.0f', cbar_kws={'label': 'Traffic'})
ax4.set_title('Traffic Heatmap: Top 10 Grids x Hour', fontsize=12, fontweight='bold')
ax4.set_xlabel('Hour of Day')

plt.tight_layout()
plt.savefig('images_indosat/eda_telecom_milan.png', dpi=150, bbox_inches='tight')
print("✅ EDA plot saved: images_indosat/eda_telecom_milan.png")
plt.show()

# 4. Statistical summary
print("\n📊 Statistical Summary:")
print(df['internet_traffic'].describe())

# 5. Peak hour analysis
peak_hour = hourly_pattern.idxmax()
peak_value = hourly_pattern.max()
print(f"\n🚀 Peak hour: {peak_hour}:00 with avg traffic {peak_value:.1f}")

# 6. Weekend vs Weekday (if multiple days data available)
if (df['hour'].max() - df['hour'].min()).days > 0:
    df['is_weekend'] = df['hour'].dt.dayofweek.isin([5, 6])
    weekend_avg = df.groupby('is_weekend')['internet_traffic'].mean()
    print(f"\n📅 Weekend avg traffic: {weekend_avg[True]:.1f}")
    print(f"   Weekday avg traffic: {weekend_avg[False]:.1f}")