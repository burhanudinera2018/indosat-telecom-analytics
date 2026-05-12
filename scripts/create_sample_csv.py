"""
Create sample CSV from PostgreSQL for Streamlit deployment
"""

import pandas as pd
from sqlalchemy import create_engine
import os

print("="*50)
print("📊 MEMBUAT SAMPLE CSV DARI POSTGRESQL")
print("="*50)

# Koneksi ke database lokal
print("\n🔌 Koneksi ke PostgreSQL local...")
engine = create_engine('postgresql:///indosat_db?host=localhost')

# Ambil data agregat per jam
print("📖 Membaca data dari tabel cdr_hourly...")
df = pd.read_sql("""
    SELECT 
        EXTRACT(HOUR FROM hour) as hour,
        AVG(internet_traffic) as avg_traffic,
        SUM(internet_traffic) as total_traffic,
        COUNT(DISTINCT square_id) as active_grids
    FROM cdr_hourly
    GROUP BY EXTRACT(HOUR FROM hour)
    ORDER BY hour
""", engine)

print(f"\n✅ Berhasil! {len(df)} baris data (24 jam).")
print(df.to_string(index=False))

# Buat folder data jika belum ada
os.makedirs('data', exist_ok=True)

# Simpan sebagai CSV
csv_path = 'data/hourly_traffic_sample.csv'
df.to_csv(csv_path, index=False)
print(f"\n💾 File disimpan: {csv_path}")
print(f"📦 Ukuran file: ~1 KB")

# Verifikasi
print("\n📋 Preview 5 baris pertama:")
print(df.head().to_string(index=False))
print("\n🎉 Selesai! File siap untuk deploy ke Streamlit Cloud.")