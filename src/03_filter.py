import duckdb

con = duckdb.connect("nestle.duckdb")
P = "data/raw/food.parquet"
brands = [l.strip() for l in open("sql/brands.txt") if l.strip()]

con.sql(f"""
    CREATE OR REPLACE TABLE nestle_raw AS
    SELECT *,
      CASE WHEN len(list_filter(brands_tags, b -> b LIKE 'nestle%')) > 0
           THEN 'nestle_tag' ELSE 'brand_list' END AS match_rule
    FROM '{P}'
    WHERE len(list_filter(brands_tags, b -> b LIKE 'nestle%')) > 0
       OR len(list_filter(brands_tags, b -> list_contains({brands!r}, b))) > 0
""")

print("Total Nestle products:",
      con.sql("SELECT count(*) FROM nestle_raw").fetchone()[0])
print("\nBy match rule:")
print(con.sql("SELECT match_rule, count(*) AS products FROM nestle_raw GROUP BY 1").df().to_string(index=False))

print("\nProducts added by the brand list, per tag:")
print(con.sql(f"""
    SELECT brand, count(*) AS products FROM (
      SELECT unnest(list_filter(brands_tags, b -> list_contains({brands!r}, b))) AS brand
      FROM nestle_raw WHERE match_rule = 'brand_list')
    GROUP BY 1 ORDER BY 2 DESC
""").df().to_string(index=False))

print("\nTop 10 countries:")
print(con.sql("""
    SELECT country, count(*) AS products FROM (
      SELECT unnest(countries_tags) AS country FROM nestle_raw)
    GROUP BY 1 ORDER BY 2 DESC LIMIT 10
""").df().to_string(index=False))
