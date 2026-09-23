
## 2024-05-18 - Avoid iterrows in pandas tight loops
**Learning:** Pandas `.iterrows()` is exceptionally slow, significantly impacting algorithms in `VolumeProfileEngine` and `PointAndFigureEngine` which iterate row-by-row.
**Action:** Always pre-fetch columns as NumPy arrays using `.values` and vectorize operations like `np.log` where possible for massive performance gains, which matched up with existing knowledge base.
