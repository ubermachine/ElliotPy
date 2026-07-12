import os
import pytest
import pandas as pd
from backend.data_manager import DataManager

# We point to the local market-data-lake for testing purposes
# The implementation will look at this directory when running locally.
LOCAL_LAKE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "market-data-lake", "data"))

def test_data_manager_loads_from_lake():
    """Verify that DataManager loads the data from the data lake instead of yfinance/local sqlite."""
    # Temporarily remove any local caches if they exist to ensure we read from lake
    db_file = "test_cache.db"
    parquet_dir = "test_parquet_data"
    
    if os.path.exists(db_file):
        os.remove(db_file)
        
    dm = DataManager(db_path=db_file, parquet_dir=parquet_dir)
    
    # We load TCS.NS
    df, use_log = dm.fetch_data("TCS.NS")
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) >= 1250
    assert list(df.columns) == ["Date", "Open", "High", "Low", "Close", "Volume"]
    
    # Verify that the test database was NOT created or remains empty,
    # and no test_parquet_data files were created, because we shouldn't be caching locally.
    # (Unless we decide that we don't need sqlite/local parquet folders at all in DataManager!)
    if os.path.exists(db_file):
        # If it was created, it shouldn't contain the data
        import duckdb
        conn = duckdb.connect(db_file)
        try:
            res = conn.execute("SELECT count(*) FROM price_history").fetchone()[0]
            assert res == 0, "Local DB should be empty when streaming from remote lake"
        finally:
            conn.close()
        os.remove(db_file)
        
    # Clean up test directories
    if os.path.exists(parquet_dir):
        import shutil
        shutil.rmtree(parquet_dir)
