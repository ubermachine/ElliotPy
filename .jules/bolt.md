## 2026-07-16 - Pandas .iloc Bottleneck in Tight Loops
**Learning:** Using Pandas `.iloc` for scalar access inside tight loops (like the `run_adaptive_zigzag` logic iterating over every bar) introduces massive overhead.
**Action:** Always pre-fetch required Pandas DataFrame columns as NumPy arrays using `.values` (e.g., `self.df['Close'].values`) and access elements via standard array indexing when iterating row-by-row.
