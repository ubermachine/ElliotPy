import unittest
import pandas as pd
import numpy as np
from backend.institutional_engine import VolumeProfileEngine, PointAndFigureEngine
from backend.wave_engine import DailyElliottWaveEngine

class TestEngines(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n_rows = 1000
        dates = pd.date_range('2020-01-01', periods=n_rows)
        closes = np.cumsum(np.random.randn(n_rows)) + 100
        highs = closes + np.random.rand(n_rows) * 2
        lows = closes - np.random.rand(n_rows) * 2
        opens = closes + np.random.randn(n_rows) * 0.5

        self.df = pd.DataFrame({
            'Date': dates,
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes
        })

    def test_vp(self):
        vp = VolumeProfileEngine(self.df)
        res = vp.calculate_profile()
        self.assertTrue(len(res) > 0)

    def test_pnf(self):
        pnf = PointAndFigureEngine(self.df)
        cols = pnf.calculate_pnf()
        self.assertTrue(len(cols) > 0)

    def test_ewe(self):
        ewe = DailyElliottWaveEngine(self.df)
        p, a = ewe.run_analysis()
        self.assertTrue(len(p) > 0)

if __name__ == '__main__':
    unittest.main()
