import pandas as pd
from backend.wave_engine import DailyElliottWaveEngine, Pivot
import datetime
from backend.data_manager import DataManager

dm = DataManager()
df, _ = dm.fetch_data("SI=F", force_refresh=False)
engine = DailyElliottWaveEngine(df, use_log_scale=True)
primary_count, alternates = engine.run_analysis(min_move_mult=0.90)

print(f"Primary count length: {len(primary_count)}")
if len(primary_count) > 0:
    for w in primary_count[-5:]:
        print(f"Wave: {w.label} from {w.start_pivot.time} to {w.end_pivot.time}")
else:
    print("Primary count is empty!!")
