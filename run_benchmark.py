import pandas as pd
import numpy as np
import time
from backend.wave_engine import DailyElliottWaveEngine

# Generate dummy data
np.random.seed(42)
n_days = 2000
dates = pd.date_range(start='2010-01-01', periods=n_days, freq='D')
close = np.cumprod(1 + np.random.normal(0, 0.02, n_days)) * 100
high = close * (1 + np.abs(np.random.normal(0, 0.01, n_days)))
low = close * (1 - np.abs(np.random.normal(0, 0.01, n_days)))
open_price = close * (1 + np.random.normal(0, 0.005, n_days))

df = pd.DataFrame({'Date': dates, 'Open': open_price, 'High': high, 'Low': low, 'Close': close})

start = time.time()
for _ in range(10):
    engine = DailyElliottWaveEngine(df)
    engine.run_analysis()
end = time.time()

print(f"Time taken: {end - start:.4f} seconds")
