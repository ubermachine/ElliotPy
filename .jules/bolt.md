
## 2025-09-15 - [Pandas .iloc Loop Bottleneck in WaveEngine]
**Learning:** Using `.iloc` inside tight loops in core algorithms (like `run_adaptive_zigzag`) causes severe performance bottlenecks due to Pandas indexing overhead.
**Action:** When working on tight algorithms traversing series data, cache the columns as NumPy arrays (e.g. `self._close = self.df['Close'].values`) ahead of time. Use `.dt.to_pydatetime()` if extracting from a datetime column to maintain standard Python datetime types.
