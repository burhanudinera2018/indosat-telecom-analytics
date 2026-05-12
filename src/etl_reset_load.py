"""
Reset Database and Load ALL 30 Days of Milan Telecom Data
Indosat Ooredoo Data Science Portfolio
"""

import pandas as pd
import numpy as np
import os
import glob
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("="*60)
print("🚀 RESET & LOAD: 30 DAYS OF REAL DATA (1-30 NOV 2013)")
print("="*60)

# Koneksi ke database
engine = create_engine('postgresql:///indosat_db?host=localhost')

# Step 1: Drop existing tables
print("\n🗄️ Resetting database (dropping old tables)...")
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS cdr_hourly CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS grid_cells CASCADE;"))
    conn.commit()
logger.info("✅ Old tables dropped")

# Step 2: Create fresh tables
print("\n📋 Creating fresh tables...")
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE grid_cells (
            square_id INTEGER PRIMARY KEY
        )
    """))
    conn.execute(text("""
        CREATE TABLE cdr_hourly (
            id SERIAL PRIMARY KEY,
            square_id INTEGER REFERENCES grid_cells(square_id),
            hour TIMESTAMP,
            internet_traffic FLOAT,
            sms_in INTEGER DEFAULT 0,
            sms_out INTEGER DEFAULT 0,
            call_in INTEGER DEFAULT 0,
            call_out INTEGER DEFAULT 0
        )
    """))
    conn.commit()
logger.info("✅ Fresh tables created")

# Step 3: Find all CSV files
print("\n📁 Finding all CSV files...")
csv_files = glob.glob('data/raw/sms-call-internet-mi-2013-11-*.csv')
csv_files.sort()
print(f"   Found {len(csv_files)} CSV files (1-30 November 2013)")

# Step 4: Process each file
print("\n📊 Processing and loading data...")

all_grids = set()
total_records = 0

for file_idx, filepath in enumerate(csv_files):
    logger.info(f"Processing {os.path.basename(filepath)} ({file_idx+1}/{len(csv_files)})")
    
    # Read CSV
    df = pd.read_csv(filepath)
    
    # Rename columns
    df = df.rename(columns={
        'SquareID': 'square_id',
        'Timestamp': 'timestamp',
        'InternetTraffic': 'internet_traffic'
    })
    
    # Convert timestamp to hour
    df['hour'] = pd.to_datetime(df['timestamp'], unit='ms').dt.floor('h')
    
    # Add dummy columns
    df['sms_in'] = 0
    df['sms_out'] = 0
    df['call_in'] = 0
    df['call_out'] = 0
    
    # Select needed columns
    df = df[['square_id', 'hour', 'internet_traffic', 'sms_in', 'sms_out', 'call_in', 'call_out']]
    
    # Aggregate by square_id and hour
    df = df.groupby(['square_id', 'hour'], as_index=False).agg({
        'internet_traffic': 'sum',
        'sms_in': 'sum',
        'sms_out': 'sum',
        'call_in': 'sum',
        'call_out': 'sum'
    })
    
    # Collect unique grid IDs
    all_grids.update(df['square_id'].unique())
    
    # Insert grid cells (if new)
    for grid_id in df['square_id'].unique():
        with engine.connect() as conn:
            conn.execute(
                text("INSERT INTO grid_cells (square_id) VALUES (:sid) ON CONFLICT DO NOTHING"),
                {"sid": int(grid_id)}
            )
            conn.commit()
    
    # Insert hourly data
    df.to_sql('cdr_hourly', engine, if_exists='append', index=False)
    
    total_records += len(df)
    logger.info(f"   ✅ Inserted {len(df)} records (total so far: {total_records:,})")

# Step 5: Verification
print("\n📊 VERIFICATION:")
df_check = pd.read_sql("""
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT square_id) as unique_grids,
        MIN(hour) as first_hour,
        MAX(hour) as last_hour,
        COUNT(DISTINCT DATE(hour)) as total_days
    FROM cdr_hourly
""", engine)

print(f"   Total records: {df_check['total_records'].iloc[0]:,}")
print(f"   Unique grids: {df_check['unique_grids'].iloc[0]}")
print(f"   Date range: {df_check['first_hour'].iloc[0]} to {df_check['last_hour'].iloc[0]}")
print(f"   Total days: {df_check['total_days'].iloc[0]}")

print("\n" + "="*60)
print("🎉 RESET & LOAD COMPLETED!")
print("="*60)