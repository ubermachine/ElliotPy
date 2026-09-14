## 2024-05-24 - Pandas iloc Bottleneck in Tight Loops
**Learning:** Using pandas `.iloc` inside tight loops in backend engines causes significant overhead (~70% of execution time in wave_engine).
**Action:** Pre-fetch columns as NumPy arrays using `.values` and cache them on the class instance. For Date columns, use `.dt.to_pydatetime()` if it's a datetime type to ensure standard Python datetime objects are returned instead of `numpy.datetime64`.
