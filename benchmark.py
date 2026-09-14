import time
import pandas as pd
import numpy as np
from backend.wave_engine import DailyElliottWaveEngine

# Generate mock data
np.random.seed(42)
days = 5000
dates = pd.date_range(start='2020-01-01', periods=days)
close = np.cumprod(1 + np.random.normal(0, 0.01, days)) * 100
high = close * (1 + np.abs(np.random.normal(0, 0.005, days)))
low = close * (1 - np.abs(np.random.normal(0, 0.005, days)))
open_p = close * (1 + np.random.normal(0, 0.002, days))

df = pd.DataFrame({
    'Date': dates,
    'Open': open_p,
    'High': high,
    'Low': low,
    'Close': close
})

start = time.time()
engine = DailyElliottWaveEngine(df)
engine.run_analysis()
end = time.time()
print(f"Time taken: {end - start:.4f} seconds")
