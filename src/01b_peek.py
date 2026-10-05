import duckdb

con = duckdb.connect()
P = "data/raw/food.parquet"

row = con.sql(f"""
    SELECT code, product_name, brands, brands_tags, categories_tags,
           countries_tags, nutriscore_grade, nova_group
    FROM '{P}'
    WHERE list_contains(brands_tags, 'nestle')
    LIMIT 1
""").df().T
print(row.to_string())

nutr = con.sql(f"""
    SELECT nutriments
    FROM '{P}'
    WHERE list_contains(brands_tags, 'nestle') AND len(nutriments) > 0
    LIMIT 1
""").fetchone()[0]
print("\nFirst 3 nutriment entries:")
for item in nutr[:3]:
    print(item)
