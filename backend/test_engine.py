import unittest
import pandas as pd
import numpy as np
import datetime
from backend.data_manager import DataManager
from backend.wave_engine import DailyElliottWaveEngine, Pivot

class TestDataPipeline(unittest.TestCase):
    def setUp(self):
        self.dm = DataManager(db_path="test_cache.db", parquet_dir="test_data")

    def test_insufficient_data_rejection(self):
        # Create a mock dataframe with fewer than 1250 bars
        dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(100)]
        mock_df = pd.DataFrame({
            'Date': dates,
            'Open': np.random.uniform(10, 20, 100),
            'High': np.random.uniform(20, 30, 100),
            'Low': np.random.uniform(5, 10, 100),
            'Close': np.random.uniform(10, 20, 100),
            'Volume': np.random.randint(1000, 5000, 100)
        })
        
        with self.assertRaises(ValueError):
            self.dm._preprocess_data(mock_df)

    def test_cleaning_gaps(self):
        # Create mock data with 1300 bars and some NaNs
        dates = [datetime.date(2020, 1, 1) + datetime.timedelta(days=i) for i in range(1300)]
        closes = [float(100 + i * 0.1) for i in range(1300)]
        
        # Inject NaN values (consecutive 2 and consecutive 3)
        closes[50] = np.nan
        closes[51] = np.nan
        
        closes[100] = np.nan
        closes[101] = np.nan
        closes[102] = np.nan
        
        mock_df = pd.DataFrame({
            'Date': dates,
            'Open': closes,
            'High': closes,
            'Low': closes,
            'Close': closes,
            'Volume': [1000] * 1300
        })
        
        cleaned = self.dm._preprocess_data(mock_df)
        
        # The row at 50, 51 should be forward-filled (so they are not NaNs)
        self.assertFalse(np.isnan(cleaned['Close'].iloc[50]))
        # The rows around index 100, 101, 102 should be deleted since it was a 3-day gap
        # Total length should be less than 1300 - 3 (since we dropped the 3-day gap rows)
        self.assertTrue(len(cleaned) < 1300)

class TestWaveEngine(unittest.TestCase):
    def test_impulse_rules_verification(self):
        # Construct mock pivots that form a PERFECT bullish impulse
        # P0=10 (LOW), P1=20 (HIGH), P2=15 (LOW, retrace 50% - valid), 
        # P3=35 (HIGH, extension - valid), P4=28 (LOW, no overlap with P1=20 - valid),
        # P5=42 (HIGH, wave 5 - valid)
        pivots = [
            Pivot(index=0, price=10.0, log_price=np.log(10.0), type_str="LOW", time=None),
            Pivot(index=10, price=20.0, log_price=np.log(20.0), type_str="HIGH", time=None),
            Pivot(index=20, price=15.0, log_price=np.log(15.0), type_str="LOW", time=None),
            Pivot(index=45, price=35.0, log_price=np.log(35.0), type_str="HIGH", time=None),
            Pivot(index=60, price=28.0, log_price=np.log(28.0), type_str="LOW", time=None),
            Pivot(index=75, price=42.0, log_price=np.log(42.0), type_str="HIGH", time=None),
        ]
        
        # Create a mock dataframe for engine initialization
        dates = [datetime.date(2020, 1, 1) + datetime.timedelta(days=i) for i in range(100)]
        closes = list(np.linspace(10, 45, 100))
        mock_df = pd.DataFrame({
            'Date': dates,
            'Open': closes,
            'High': closes,
            'Low': closes,
            'Close': closes,
            'Volume': [1000] * 100
        })
        
        engine = DailyElliottWaveEngine(mock_df, use_log_scale=False)
        is_valid, checklist = engine.verify_impulse_rules(pivots)
        self.assertTrue(is_valid)

    def test_impulse_overlap_invalidation(self):
        # Construct mock pivots where Wave 4 overlaps Wave 1
        # P0=10, P1=20, P2=15, P3=35, P4=18 (LOW, overlaps P1=20 - INVALID!), P5=30
        pivots = [
            Pivot(index=0, price=10.0, log_price=np.log(10.0), type_str="LOW", time=None),
            Pivot(index=10, price=20.0, log_price=np.log(20.0), type_str="HIGH", time=None),
            Pivot(index=20, price=15.0, log_price=np.log(15.0), type_str="LOW", time=None),
            Pivot(index=40, price=35.0, log_price=np.log(35.0), type_str="HIGH", time=None),
            Pivot(index=50, price=18.0, log_price=np.log(18.0), type_str="LOW", time=None),
            Pivot(index=60, price=30.0, log_price=np.log(30.0), type_str="HIGH", time=None),
        ]
        
        dates = [datetime.date(2020, 1, 1) + datetime.timedelta(days=i) for i in range(100)]
        closes = list(np.linspace(10, 45, 100))
        mock_df = pd.DataFrame({
            'Date': dates,
            'Open': closes,
            'High': closes,
            'Low': closes,
            'Close': closes,
            'Volume': [1000] * 100
        })
        
        engine = DailyElliottWaveEngine(mock_df, use_log_scale=False)
        is_valid, checklist = engine.verify_impulse_rules(pivots)
        self.assertFalse(is_valid)

if __name__ == '__main__':
    unittest.main()
