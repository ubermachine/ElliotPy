from backend.wave_engine import DailyElliottWaveEngine
from backend.data_manager import DataManager

dm = DataManager()
df, _ = dm.fetch_data("SI=F", force_refresh=False)

engine = DailyElliottWaveEngine(df, use_log_scale=True)
primary, _ = engine.run_analysis(1.5)

motives = [w for w in primary if w.wave_type == 'motive']
print(f'Total waves in primary count: {len(primary)}')
print(f'Motive waves found: {len(motives)}')
for w in motives[-5:]:
    print(f'{w.label} from {w.start_pivot.time} to {w.end_pivot.time}')
