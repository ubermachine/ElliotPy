## 2024-05-17 - Pandas iloc is a performance killer in tight loops
**Learning:** Using `pandas.DataFrame.iloc` inside a tight iterative loop (like the adaptive zig-zag calculation iterating over thousands of rows) adds immense overhead, making calculations surprisingly slow.
**Action:** Always pre-fetch columns as NumPy arrays using `.values` and iterate over those arrays instead of using `.iloc` when performance is critical in a tight loop.
