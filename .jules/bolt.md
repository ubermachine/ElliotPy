
## 2024-05-18 - Safe Pandas to NumPy Caching
**Learning:** When replacing Pandas `.iloc` with NumPy arrays using `.values`, time series / date columns might return `numpy.datetime64` instead of standard `pandas.Timestamp` or `datetime.datetime`. This can break downstream code relying on `datetime` methods.
**Action:** When caching `Date` columns as NumPy arrays, use `.dt.to_pydatetime()` if the column is a datetime type (e.g. `pd.api.types.is_datetime64_any_dtype`), otherwise fallback to `.values`.
