## 2024-07-25 - Avoid Pandas `.iloc` in Tight Loops
**Learning:** In the backend data processing (e.g., wave_engine.py), using Pandas `.iloc` in tight loops causes significant performance bottlenecks. Converting a pandas Series to a NumPy array via `.values` before the loop and iterating through the array yields a ~160x speed improvement for data access.
**Action:** When writing or reviewing code that iterates over rows element-by-element, pre-fetch columns as NumPy arrays using `.values` and cache them on the class instance to maximize efficiency.
