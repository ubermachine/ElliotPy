
## 2024-05-18 - Avoid Pandas .iloc in tight loops
**Learning:** In backend data processing (`wave_engine.py`), using Pandas `.iloc` inside tight loops (like calculating the adaptive Zig-Zag over 10,000 bars) causes massive performance bottlenecks.
**Action:** Always pre-fetch columns as NumPy arrays using `.values` and cache them on the class instance to significantly speed up row-by-row iteration (e.g., 2.3s down to 0.02s in benchmark).
