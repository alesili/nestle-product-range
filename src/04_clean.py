import duckdb
import pandas as pd

con = duckdb.connect("nestle.duckdb")
brands = [l.strip() for l in open("sql/brands.txt") if l.strip()]

def nut(name):
    return "list_filter(nutriments, x -> x.name = '" + name + "')[1].\"100g\""

raw = con.sql("SELECT count(*) FROM nestle_raw").fetchone()[0]
distinct = con.sql("SELECT count(DISTINCT code) FROM nestle_raw").fetchone()[0]
print(f"Rows in nestle_raw: {raw:,} | distinct barcodes: {distinct:,}\n")

con.sql(f"""
CREATE OR REPLACE TABLE nestle_flat AS
SELECT
  code,
  coalesce(list_filter(product_name, x -> x.lang = 'main')[1]."text",
           product_name[1]."text") AS name,
  CASE WHEN coalesce(list_filter(brands_tags, b -> list_contains({brands!r}, b))[1], 'nestle')
            IN ('coffee-mate','coffeemate') THEN 'coffee-mate'
       ELSE coalesce(list_filter(brands_tags, b -> list_contains({brands!r}, b))[1], 'nestle')
  END AS brand,
  match_rule,
  categories_tags,
  countries_tags,
  nutriscore_grade,
  nova_group,
  additives_n,
  {nut('energy-kcal')} AS kcal,
  {nut('sugars')} AS sugars,
  {nut('fat')} AS fat,
  {nut('saturated-fat')} AS sat_fat,
  {nut('salt')} AS salt,
  {nut('proteins')} AS protein,
  {nut('fiber')} AS fiber
FROM nestle_raw
QUALIFY row_number() OVER (PARTITION BY code ORDER BY code) = 1
""")

flat = con.sql("SELECT count(*) FROM nestle_flat").fetchone()[0]
log = [("duplicate barcodes removed", raw - flat)]

rules = [
 ("kcal",     "kcal < 0 OR kcal > 900"),
 ("sugars",   "sugars < 0 OR sugars > 100"),
 ("fat",      "fat < 0 OR fat > 100"),
 ("sat_fat",  "sat_fat < 0 OR sat_fat > 100 OR sat_fat > fat"),
 ("salt",     "salt < 0 OR salt > 100"),
 ("protein",  "protein < 0 OR protein > 100"),
 ("fiber",    "fiber < 0 OR fiber > 100"),
 ("nutriscore_grade",
    "nutriscore_grade IS NOT NULL AND nutriscore_grade NOT IN ('a','b','c','d','e')"),
 ("nova_group",
    "nova_group IS NOT NULL AND nova_group NOT IN (1,2,3,4)"),
]
for col, cond in rules:
    n = con.sql(f"SELECT count(*) FROM nestle_flat WHERE {cond}").fetchone()[0]
    con.sql(f"UPDATE nestle_flat SET {col} = NULL WHERE {cond}")
    log.append((f"{col}: set to missing (impossible or unknown value)", n))

log_df = pd.DataFrame(log, columns=["step", "rows_affected"])
print("CLEANING LOG")
print(log_df.to_string(index=False))
log_df.to_csv("outputs/cleaning_log.csv", index=False)

cols = ["name","kcal","sugars","fat","sat_fat","salt","protein","fiber",
        "nutriscore_grade","nova_group"]
parts = [f"round(100.0*count({c})/count(*),1) AS {c}" for c in cols]
parts.append("round(100.0*sum(CASE WHEN len(categories_tags)>0 THEN 1 ELSE 0 END)/count(*),1) AS categories_tags")
parts.append("round(100.0*sum(CASE WHEN len(countries_tags)>0 THEN 1 ELSE 0 END)/count(*),1) AS countries_tags")
comp = con.sql(f"SELECT count(*) AS products, {', '.join(parts)} FROM nestle_flat").df().T
comp.columns = ["value"]
print("\nCOMPLETENESS (% of products with a value; first row = number of products)")
print(comp.to_string())
comp.to_csv("outputs/completeness.csv")

print("\nPRODUCTS PER BRAND")
print(con.sql("SELECT brand, count(*) AS products FROM nestle_flat GROUP BY 1 ORDER BY 2 DESC").df().to_string(index=False))
