"""
ETL Pipeline for Telecom Italy Dataset (Subset Version)
Indosat Ooredoo Data Science Portfolio
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import os
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelecomETL:
    """
    ETL Pipeline untuk data CDR Telecom Italia
    Optimized untuk subset kecil (500 grid, 14 hari)
    """
    
    def __init__(self, data_path: str, db_url: str = None):
        self.data_path = data_path
        self.db_url = db_url or 'postgresql:///indosat_db?host=localhost'
        self.engine = None
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.engine = create_engine(self.db_url)
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
    
    def create_tables(self):
        """Create tables matching the exact structure of our data"""
        with self.engine.connect() as conn:
            # Drop existing tables (if any)
            conn.execute(text("DROP TABLE IF EXISTS cdr_hourly CASCADE;"))
            conn.execute(text("DROP TABLE IF EXISTS grid_cells CASCADE;"))
            conn.commit()
            
            # Create grid_cells table
            conn.execute(text("""
                CREATE TABLE grid_cells (
                    square_id INTEGER PRIMARY KEY
                )
            """))
            
            # Create cdr_hourly table with columns that MATCH our DataFrame
            conn.execute(text("""
                CREATE TABLE cdr_hourly (
                    id SERIAL PRIMARY KEY,
                    square_id INTEGER REFERENCES grid_cells(square_id),
                    hour TIMESTAMP,
                    sms_in DOUBLE PRECISION DEFAULT 0,
                    sms_out DOUBLE PRECISION DEFAULT 0,
                    call_in DOUBLE PRECISION DEFAULT 0,
                    call_out DOUBLE PRECISION DEFAULT 0,
                    internet_traffic DOUBLE PRECISION
                )
            """))
            conn.commit()
            
            logger.info("✅ Tables created successfully with correct schema")
    
    def load_sample_data(self, n_grids: int = 500, n_days: int = 14):
        """Load data from CSV and aggregate to hourly"""
        logger.info(f"Loading sample data: {n_grids} grids, {n_days} days")
        
        filepath = os.path.join(self.data_path, 'sms-call-internet-mi-2013-11-01_parsed.csv')
        
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return None
        
        logger.info(f"Reading file: {filepath}")
        
        # Read CSV
        df = pd.read_csv(filepath)
        df = df.rename(columns={
            'SquareID': 'square_id',
            'Timestamp': 'timestamp',
            'InternetTraffic': 'internet_traffic'
        })
        
        # Convert timestamp to hour (floor to hour)
        df['hour'] = pd.to_datetime(df['timestamp'], unit='ms').dt.floor('h')
        
        # Add dummy columns for SMS and Call (since this dataset only has internet)
        df['sms_in'] = 0
        df['sms_out'] = 0
        df['call_in'] = 0
        df['call_out'] = 0
        
        # Select only columns needed for database
        df = df[['square_id', 'hour', 'sms_in', 'sms_out', 'call_in', 'call_out', 'internet_traffic']]
        
        # Aggregate by square_id and hour (in case there are multiple records per hour)
        df = df.groupby(['square_id', 'hour'], as_index=False).agg({
            'sms_in': 'sum',
            'sms_out': 'sum', 
            'call_in': 'sum',
            'call_out': 'sum',
            'internet_traffic': 'sum'
        })
        
        # Sample grids
        unique_grids = df['square_id'].unique()
        if len(unique_grids) > n_grids:
            selected_grids = np.random.choice(unique_grids, size=n_grids, replace=False)
            df = df[df['square_id'].isin(selected_grids)]
            logger.info(f"   Sampled {n_grids} grids")
        
        # Filter days
        min_date = df['hour'].max() - pd.Timedelta(days=n_days)
        df = df[df['hour'] >= min_date]
        
        logger.info(f"✅ Loaded {len(df)} records")
        logger.info(f"   Grid cells: {df['square_id'].nunique()}")
        logger.info(f"   Date range: {df['hour'].min()} to {df['hour'].max()}")
        
        return df
    
    def insert_to_db(self, df: pd.DataFrame):
        """Insert data to database - only use columns that exist in table"""
        
        # Select only columns that exist in the database table
        columns_to_insert = ['square_id', 'hour', 'sms_in', 'sms_out', 
                            'call_in', 'call_out', 'internet_traffic']
        
        # Ensure column exist before insert
        df_insert = df[columns_to_insert].copy()
        
        # Insert grid cells first (if not exists)
        with self.engine.connect() as conn:
            for square_id in df_insert['square_id'].unique():
                conn.execute(
                    text("INSERT INTO grid_cells (square_id) VALUES (:sid) ON CONFLICT DO NOTHING"),
                    {"sid": int(square_id)}
                )
            conn.commit()
        
        # Insert hourly data in chunks
        chunksize = 10000
        for i in range(0, len(df_insert), chunksize):
            chunk = df_insert.iloc[i:i+chunksize]
            chunk.to_sql('cdr_hourly', self.engine, if_exists='append', index=False)
            logger.info(f"   Inserted chunk {i//chunksize + 1}/{(len(df_insert)//chunksize)+1}")
        
        logger.info(f"✅ Inserted {len(df_insert)} records to cdr_hourly")
    
    def run_complete_pipeline(self, n_grids: int = 500, n_days: int = 14):
        """Run complete ETL pipeline"""
        
        logger.info("="*50)
        logger.info("🚀 STARTING ETL PIPELINE")
        logger.info("="*50)
        
        # Step 1: Connect to database
        if not self.connect_db():
            return False
        
        # Step 2: Create tables
        self.create_tables()
        
        # Step 3: Load sample data
        df = self.load_sample_data(n_grids=n_grids, n_days=n_days)
        
        if df is None or len(df) == 0:
            logger.error("❌ No data loaded")
            return False
        
        # Step 4: Insert to database
        self.insert_to_db(df)
        
        # Step 5: Verification
        with self.engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM cdr_hourly")).fetchone()[0]
            grid_count = conn.execute(text("SELECT COUNT(*) FROM grid_cells")).fetchone()[0]
            
        logger.info("="*50)
        logger.info("🎉 ETL PIPELINE COMPLETED")
        logger.info("="*50)
        logger.info(f"📊 Database summary:")
        logger.info(f"   Grid cells: {grid_count}")
        logger.info(f"   Hourly records: {count}")
        logger.info(f"   Date range: {df['hour'].min()} to {df['hour'].max()}")
        
        return True

if __name__ == "__main__":
    # Konfigurasi
    DATA_PATH = "data/raw/"  # Sesuaikan dengan lokasi raw data Anda
    DB_URL = "postgresql:///indosat_db?host=localhost"
    
    # Jalankan ETL
    etl = TelecomETL(data_path=DATA_PATH, db_url=DB_URL)
    etl.run_complete_pipeline(n_grids=500, n_days=14)