import pandas as pd
from backend.wave_engine import DailyElliottWaveEngine, Pivot
import datetime
from backend.data_manager import DataManager

dm = DataManager()
df, _ = dm.fetch_data("SI=F", force_refresh=False)
engine = DailyElliottWaveEngine(df, use_log_scale=False)
pivots_t1 = engine.run_adaptive_zigzag(1.5)

print("Total pivots:", len(pivots_t1))
if pivots_t1:
    print("Last pivot:", pivots_t1[-1].time)

waves = engine._fallback_sequential(pivots_t1, 0, len(pivots_t1), "Primary")
print("Total waves:", len(waves))
if waves:
    print("Last wave ends at:", waves[-1].end_pivot.time)
    print("Last 10 waves:")
    for w in waves[-10:]:
        print(f"  {w.start_pivot.time} -> {w.end_pivot.time} | Label: {w.label}")
