## 2024-05-23 - Pandas iloc bottleneck in tight loops
**Learning:** Pandas `.iloc` lookups inside tight loops (like in the `run_adaptive_zigzag` logic) cause massive performance bottlenecks.
**Action:** When working with large DataFrames in performance-critical sections (e.g. `backend/wave_engine.py`), always pre-fetch the columns as NumPy arrays using `.values` in the initialization phase and iterate over those arrays natively instead.
