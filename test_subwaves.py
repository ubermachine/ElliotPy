import pandas as pd
from backend.wave_engine import DailyElliottWaveEngine, Pivot
import datetime
from backend.data_manager import DataManager

dm = DataManager()
df, _ = dm.fetch_data("SI=F", force_refresh=False)
engine = DailyElliottWaveEngine(df, use_log_scale=False)
pivots_t1 = engine.run_adaptive_zigzag(1.5)
pivots_t2 = engine.run_adaptive_zigzag(1.5 * 0.5)

waves = engine._sequential_label(pivots_t1, "Primary")
for w in waves:
    engine._recursive_subdivide(w, pivots_t2, depth=2)

print("Last 5 Primary waves and their sub-waves:")
for w in waves[-5:]:
    print(f"Primary {w.label}: {w.start_pivot.time} -> {w.end_pivot.time}, sub_waves: {len(w.sub_waves)}")
    for sw in w.sub_waves:
        print(f"  Sub {sw.degree} {sw.label}: {sw.start_pivot.time} -> {sw.end_pivot.time}, sub_waves: {len(sw.sub_waves)}")
