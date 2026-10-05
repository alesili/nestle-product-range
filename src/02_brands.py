import duckdb

con = duckdb.connect()
P = "data/raw/food.parquet"

# A. Products with a brand tag starting with 'nestle'
n = con.sql(f"""
    SELECT count(*) FROM '{P}'
    WHERE len(list_filter(brands_tags, b -> b LIKE 'nestle%')) > 0
""").fetchone()[0]
print(f"A. Products with a brand tag starting with 'nestle': {n:,}\n")

# B. Other brand tags that appear together with 'nestle' on the same product
co = con.sql(f"""
    SELECT tag, count(*) AS products
    FROM (
        SELECT unnest(brands_tags) AS tag
        FROM '{P}'
        WHERE len(list_filter(brands_tags, b -> b LIKE 'nestle%')) > 0
    )
    GROUP BY tag ORDER BY products DESC LIMIT 80
""").df()
print("B. Brand tags found on products tagged 'nestle' (top 60):")
print(co.head(60).to_string(index=False))
co.to_csv("data/processed/brands_cooccurring.csv", index=False)

# C. Candidate brands counted by exact tag, over the whole database
cands = ["nespresso", "nescafe", "nesquik", "kitkat", "maggi", "buitoni",
         "herta", "thomy", "cailler", "smarties", "after-eight",
         "quality-street", "milo", "nido", "gerber", "cerelac", "perrier",
         "san-pellegrino", "vittel", "garden-gourmet", "aero", "nan"]
cand = con.sql(f"""
    SELECT tag, count(*) AS products
    FROM (SELECT unnest(brands_tags) AS tag FROM '{P}')
    WHERE tag IN {tuple(cands)}
    GROUP BY tag ORDER BY products DESC
""").df()
print("\nC. Candidate brand tags in the whole database:")
print(cand.to_string(index=False))
cand.to_csv("data/processed/brands_candidates.csv", index=False)

# D. Nutrient names used in Nestle products (to check names like sugars, salt)
nut = con.sql(f"""
    SELECT x.name AS nutrient, count(*) AS n
    FROM (SELECT unnest(nutriments) AS x FROM '{P}'
          WHERE list_contains(brands_tags, 'nestle'))
    GROUP BY 1 ORDER BY 2 DESC LIMIT 25
""").df()
print("\nD. Most common nutrient names in Nestle products:")
print(nut.to_string(index=False))
