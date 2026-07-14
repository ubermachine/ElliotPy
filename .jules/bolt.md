## 2024-05-20 - [Performance] Removing pd.DataFrame.iloc in tight loops
**Learning:** Using `pandas.DataFrame.iloc` in loops in python is extremely slow compared to pre-extracting the numpy arrays using `.values`.
**Action:** Always pre-fetch columns as NumPy arrays using `.values` and index those directly instead of `iloc` in tight loops.
