import duckdb

con = duckdb.connect()
P = "data/raw/food.parquet"

cols = con.sql(f"DESCRIBE SELECT * FROM '{P}'").df()
cols["short_type"] = cols["column_type"].str.slice(0, 60)
print(cols[["column_name", "short_type"]].to_string(index=False))
