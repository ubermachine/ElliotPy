
## 2024-05-24 - Optimize backend loop performance
**Learning:** Pandas `.iterrows()` is a major performance bottleneck for backend processing engines (like Volume Profile and Point & Figure) that iterate through row values.
**Action:** Always pre-fetch DataFrame columns into NumPy arrays using `.values` and iterate over those arrays (e.g., using `zip`) instead of `.iterrows()`. Use vectorized `np.log` directly on the entire array rather than calling it per row iteration for mathematical transformations.
