## 2024-06-25 - Avoid Pandas .iloc in tight loops
**Learning:** Using `pandas.Series.iloc` inside tight calculation loops like `run_adaptive_zigzag` causes significant performance bottlenecks compared to accessing elements of a NumPy array.
**Action:** When a method needs to iterate and perform row-level calculations, pre-fetch columns as NumPy arrays using `.values` inside the constructor or initialization, and use these arrays in the loop.
