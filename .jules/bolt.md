## 2024-05-15 - Pandas Iterrows Performance Anti-Pattern
**Learning:** Iterating through rows using `.iterrows()` in pandas is extremely slow due to the creation of Series objects for each row.
**Action:** Replace `.iterrows()` with direct iteration over NumPy arrays retrieved with `.values` for substantial (4-8x) speedups, particularly inside nested loops or frequent method calls.
