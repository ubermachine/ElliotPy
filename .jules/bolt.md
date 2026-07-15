## 2024-05-24 - Pandas iloc bottleneck in wave engine loops
**Learning:** The `DailyElliottWaveEngine` heavily relies on tight row-by-row iteration (e.g., `run_adaptive_zigzag`). Using Pandas `.iloc` inside these loops introduces massive overhead (2.6s for 10k rows).
**Action:** Always extract Pandas columns to NumPy arrays via `.values` during initialization (`__init__`) and index those arrays directly in tight loops. This simple change yields a nearly 100x speedup in this specific application.
