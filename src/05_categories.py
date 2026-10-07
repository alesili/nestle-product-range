import duckdb

con = duckdb.connect("nestle.duckdb")

# Rule 1: keywords in product name or category tags (first match wins)
rules = [
 ("Breakfast cereals", r"\b(cereals?|muesli|granola|cornflakes|corn flakes)\b"),
 ("Coffee & creamers", r"\b(coffee|espresso|latte|cappuccino|creamers?|mocha)\b"),
 ("Chocolate & confectionery", r"\b(chocolates?|confectioner(y|ies)|candy|candies|wafers?|biscuits?|cookies?)\b"),
 ("Infant & young child nutrition", r"\b(baby|infant|toddler|purees?|formula|stage [1-4])\b"),
 ("Culinary & meals", r"\b(soups?|sauces?|noodles?|bouillon|seasoning|pasta|pizza|meals?|dressing|mayonnaise|ketchup|gravy|stock|ravioli|tortellini)\b"),
 ("Dairy & milk drinks", r"\b(milk|yogh?urt|dairy|ice cream|malt|cocoa powder)\b"),
 ("Beverages", r"\b(water|juice|beverages?|drinks?|tea)\b"),
]

# Rule 2: default category by brand, used only if rule 1 finds nothing
brand_default = {
 "nescafe": "Coffee & creamers", "nespresso": "Coffee & creamers",
 "dolce-gusto": "Coffee & creamers", "coffee-mate": "Coffee & creamers",
 "maggi": "Culinary & meals", "thomy": "Culinary & meals",
 "buitoni": "Culinary & meals", "garden-gourmet": "Culinary & meals",
 "herta": "Culinary & meals",
 "gerber": "Infant & young child nutrition", "cerelac": "Infant & young child nutrition",
 "cailler": "Chocolate & confectionery",
 "nido": "Dairy & milk drinks", "ninho": "Dairy & milk drinks",
 "molico": "Dairy & milk drinks", "nescau": "Dairy & milk drinks",
 "nesquik": "Dairy & milk drinks", "milo": "Dairy & milk drinks",
}

content_case = "CASE\n" + "".join(
    f"  WHEN regexp_matches(txt, '{p}') THEN '{c}'\n" for c, p in rules) + "  ELSE NULL END"
brand_case = "CASE brand\n" + "".join(
    f"  WHEN '{b}' THEN '{c}'\n" for b, c in brand_default.items()) + "  ELSE NULL END"

con.sql(f"""
CREATE OR REPLACE TABLE nestle_cat AS
SELECT *,
  coalesce(content_cat, brand_cat, 'Unclassified') AS category,
  CASE WHEN content_cat IS NOT NULL THEN 'name/category keywords'
       WHEN brand_cat IS NOT NULL THEN 'brand default'
       ELSE 'none' END AS category_source
FROM (
  SELECT *, {content_case} AS content_cat, {brand_case} AS brand_cat
  FROM (
    SELECT *,
      lower(coalesce(name, '') || ' ' ||
            replace(replace(coalesce(array_to_string(categories_tags, ' '), ''), '-', ' '), ':', ' ')) AS txt
    FROM nestle_flat
  )
)
""")

print("PRODUCTS PER CATEGORY (and how many have energy values)")
print(con.sql("""
    SELECT category, count(*) AS products, count(kcal) AS with_energy
    FROM nestle_cat GROUP BY 1 ORDER BY 2 DESC
""").df().to_string(index=False))

print("\nHOW PRODUCTS WERE CLASSIFIED")
print(con.sql("""
    SELECT category_source, count(*) AS products,
           round(100.0*count(*)/(SELECT count(*) FROM nestle_cat), 1) AS pct
    FROM nestle_cat GROUP BY 1 ORDER BY 2 DESC
""").df().to_string(index=False))

print("\nUNCLASSIFIED: with and without a product name")
print(con.sql("""
    SELECT count(*) AS unclassified, count(name) AS with_name
    FROM nestle_cat WHERE category = 'Unclassified'
""").df().to_string(index=False))

print("\nSAMPLE OF UNCLASSIFIED NAMES (30)")
print(con.sql("""
    SELECT brand, name FROM nestle_cat
    WHERE category = 'Unclassified' AND name IS NOT NULL
    USING SAMPLE 30 ROWS
""").df().to_string(index=False))

con.sql("""COPY (SELECT category, category_source, count(*) AS products
               FROM nestle_cat GROUP BY 1, 2 ORDER BY 1, 2)
           TO 'outputs/category_counts.csv' (HEADER)""")
