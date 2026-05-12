"""
Export data from local PostgreSQL to Supabase
Run: python scripts/export_to_supabase.py
"""

import pandas as pd
from sqlalchemy import create_engine, text
import urllib.parse
import os

print("="*60)
print("📤 EXPORTING DATA TO SUPABASE")
print("="*60)

# ============================================
# KONFIGURASI (GANTI DENGAN MILIK ANDA)
# ============================================

# Database lokal (sumber data)
LOCAL_DB = 'postgresql:///indosat_db?host=localhost'

# Supabase configuration
# Dapatkan dari: Project Dashboard → Connect → Session pooler
SUPABASE_HOST = "aws-0-ap-southeast-1.pooler.supabase.com"
SUPABASE_PROJECT_REF = "kskdebwbhtrmehlztjdi"  # dari URL project Anda
SUPABASE_PASSWORD = "Indosat2025"  # Ganti dengan password Supabase Anda

# Encode password (untuk karakter spesial)
encoded_password = urllib.parse.quote(SUPABASE_PASSWORD, safe='')

# Build connection string
SUPABASE_USER = f"postgres.{SUPABASE_PROJECT_REF}"
SUPABASE_URL = f"postgresql://{SUPABASE_USER}:{encoded_password}@{SUPABASE_HOST}:5432/postgres"

print(f"📋 Target Supabase: {SUPABASE_HOST}")
print(f"   User: {SUPABASE_USER}")

# ============================================
# EXPORT DATA
# ============================================

# 1. Koneksi ke database lokal
print("\n📊 Reading data from local database...")
engine_local = create_engine(LOCAL_DB)

# Load data (agregasi, bukan granular untuk hemat space)
print("   Loading CDR hourly data...")
df = pd.read_sql("""
    SELECT 
        square_id,
        hour,
        internet_traffic,
        sms_in,
        sms_out,
        call_in,
        call_out
    FROM cdr_hourly
    LIMIT 500000
""", engine_local)

print(f"   ✅ Loaded {len(df):,} records")
print(f"   Columns: {list(df.columns)}")

# 2. Koneksi ke Supabase
print("\n🔌 Connecting to Supabase...")
try:
    engine_supabase = create_engine(SUPABASE_URL)
    with engine_supabase.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("   ✅ Connected to Supabase!")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    exit(1)

# 3. Create table and insert data
print("\n📤 Uploading data to Supabase...")

# Drop existing table if any
try:
    with engine_supabase.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS cdr_hourly CASCADE;"))
        conn.commit()
    print("   ✅ Existing table dropped")
except:
    pass

# Upload data
df.to_sql('cdr_hourly', engine_supabase, if_exists='replace', index=False)
print(f"   ✅ Uploaded {len(df):,} records")

# 4. Verifikasi
print("\n📊 Verification:")
with engine_supabase.connect() as conn:
    count = conn.execute(text("SELECT COUNT(*) FROM cdr_hourly")).fetchone()[0]
    print(f"   Records in Supabase: {count:,}")
    
    # Cek sample
    sample = conn.execute(text("SELECT * FROM cdr_hourly LIMIT 3")).fetchall()
    print(f"\n📋 Sample data:")
    for row in sample:
        print(f"   {row}")

print("\n" + "="*60)
print("🎉 EXPORT TO SUPABASE COMPLETED!")
print("="*60)

# Tampilkan connection string untuk Streamlit secrets
print("\n📋 COPY THIS FOR STREAMLIT SECRETS:")
print("-"*50)
print(f"SUPABASE_URL = \"{SUPABASE_URL}\"")
print("-"*50)