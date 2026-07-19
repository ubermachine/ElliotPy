## 2025-02-18 - Pandas iloc bottleneck in tight loops
**Learning:** Calling `.iloc` inside hot loops in Pandas is extremely slow due to indexing overhead, causing massive bottlenecks in algorithms like Elliott Wave calculations.
**Action:** When working with algorithmic iterations in Python data science projects, always extract the `.values` (NumPy arrays) outside the loop and index against the arrays directly.
