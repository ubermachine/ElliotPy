import time
import pandas as pd
import numpy as np
from backend.institutional_engine import VolumeProfileEngine, PointAndFigureEngine
from backend.wave_engine import DailyElliottWaveEngine

# Generate some mock data
np.random.seed(42)
n_rows = 5000
dates = pd.date_range('2020-01-01', periods=n_rows)
closes = np.cumsum(np.random.randn(n_rows)) + 100
highs = closes + np.random.rand(n_rows) * 2
lows = closes - np.random.rand(n_rows) * 2
opens = closes + np.random.randn(n_rows) * 0.5

df = pd.DataFrame({
    'Date': dates,
    'Open': opens,
    'High': highs,
    'Low': lows,
    'Close': closes
})

start = time.time()
vp = VolumeProfileEngine(df)
vp.calculate_profile()
vp_time = time.time() - start

start = time.time()
pnf = PointAndFigureEngine(df)
cols = pnf.calculate_pnf()
pnf.calculate_signals_and_targets(cols)
pnf_time = time.time() - start

start = time.time()
ewe = DailyElliottWaveEngine(df)
ewe.run_analysis()
ewe_time = time.time() - start

print(f"VP Time: {vp_time:.4f}s")
print(f"PNF Time: {pnf_time:.4f}s")
print(f"EWE Time: {ewe_time:.4f}s")
