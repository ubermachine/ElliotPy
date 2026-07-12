import pandas as pd
import duckdb
import sys
sys.path.append('d:/antigravity_sandbox/ElliotPy')
from backend.institutional_engine import VolumeProfileEngine

conn = duckdb.connect('d:/antigravity_sandbox/ElliotPy/data_cache.db')
df = conn.execute("SELECT * FROM price_history WHERE symbol='SI=F' ORDER BY date DESC LIMIT 63").df()
df = df.rename(columns={'date':'Date', 'open':'Open', 'high':'High', 'low':'Low', 'close':'Close', 'volume':'Volume'})
print(df.head())
vp = VolumeProfileEngine(df, bins=60)
data = vp.calculate_profile()
print(data)
