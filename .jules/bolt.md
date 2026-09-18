## 2024-05-19 - Pandas .iloc performance in tight loops
**Learning:** Pandas `.iloc` is extremely slow when used inside tight `for` loops (like in the ZigZag calculation). Converting DataFrame columns to NumPy arrays and iterating over those instead yields a ~50x speedup in execution time.
**Action:** When a high-frequency loop requires sequential access to data, always pre-fetch the required Pandas columns as NumPy arrays (`df['Col'].values`) and cache them. Replace `.idxmax()` and `.idxmin()` with `np.argmax()` and `np.argmin()` on array slices.
