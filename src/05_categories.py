import duckdb

con = duckdb.connect("nestle.duckdb")

# Priority 1: brands whose products clearly belong to one category
strong_brand = {
 "nescafe": "Coffee & creamers", "nespresso": "Coffee & creamers",
 "dolce-gusto": "Coffee & creamers", "coffee-mate": "Coffee & creamers",
 "maggi": "Culinary & meals", "thomy": "Culinary & meals",
 "buitoni": "Culinary & meals", "garden-gourmet": "Culinary & meals",
 "herta": "Culinary & meals",
 "gerber": "Infant & young child nutrition", "cerelac": "Infant & young child nutrition",
 "cailler": "Chocolate & confectionery",
}

# Priority 2: keywords in product name or category tags (accents removed, first match wins)
rules = [
 ("Chocolate & confectionery", r"\b(toll house|after eight|bar one|abuelita|bertie beetle|freckles|truffles?)\b"),
 ("Breakfast cereals", r"\b(cereals?|cereales|cereais|cereale|muesli|musli|granola|cornflakes|corn flakes|chocapic|cheerios|trix|golden grahams|shreddies|cookie crisp|cini minis|honey star)\b"),
 ("Health & clinical nutrition", r"\b(boost|nutren|peptamen|optifast|resource|thicken\w*|beneprotein|health science)\b"),
 ("Coffee & creamers", r"\b(coffees?|cafe|kaffee|kaffe|espresso|latte|cappuccino|creamers?|mocha|nescafe|nespresso|dolce gusto|coffee mate)\b"),
 ("Chocolate & confectionery", r"\b(chocolat\w*|schokolade|cioccolato|confectioner\w*|candy|candies|wafers?|biscuits?|biscoito|cookies?|kitkat|kit kat|munch|smarties|quality street|aero|crunch|milkybar|caramel\w*|toffee|bonbons?|brownies?|cake)\b"),
 ("Infant & young child nutrition", r"\b(baby|infant|toddler|purees?|formula|stage [1-4]|lactogen|nestum|follow on|growing up|gerber|cerelac|beba|batita|aptamil|opti.?pro)\b"),
 ("Culinary & meals", r"\b(soups?|soupe|sopa|suppe|zuppa|sauces?|salsa|noodles?|bouillon|seasoning|pasta|pizza|meals?|dressing|mayonnaise|ketchup|gravy|stock|ravioli|tortellini|tortelloni|maggi|herta|buitoni|thomy|garden gourmet|sausages?|nuggets?|cubes?|hot pockets?|bowls?|arroz|rice)\b"),
 ("Dairy & milk drinks", r"\b(milk|leche|lait|leite|latte|yogh?urt|iogurte|dairy|ice ?cream|icecream|helado|glace|malt|cocoa|cacao|cream|crema|condensed|evaporated|milo|nesquik|nido|ninho|molico|nescau|buttermilk|bear brand|acti v|breakfast essentials)\b"),
 ("Beverages", r"\b(water|agua|eau|wasser|juice|jugo|jus|beverages?|bebida|drinks?|tea|soda|lemonade|smoothie|shake)\b"),
]

# Priority 3: weak brand defaults (brands whose products vary)
weak_brand = {
 "nido": "Dairy & milk drinks", "ninho": "Dairy & milk drinks",
 "molico": "Dairy & milk drinks", "nescau": "Dairy & milk drinks",
 "nesquik": "Dairy & milk drinks", "milo": "Dairy & milk drinks",
}

def brand_case(d):
    return "CASE brand\n" + "".join(f"  WHEN '{b}' THEN '{c}'\n" for b, c in d.items()) + "  ELSE NULL END"

content_case = "CASE\n" + "".join(
    f"  WHEN regexp_matches(txt, '{p}') THEN '{c}'\n" for c, p in rules) + "  ELSE NULL END"

con.sql(f"""
CREATE OR REPLACE TABLE nestle_cat AS
SELECT *,
  coalesce(strong_cat, content_cat, weak_cat, 'Unclassified') AS category,
  CASE WHEN strong_cat IS NOT NULL THEN 'brand (clear)'
       WHEN content_cat IS NOT NULL THEN 'name/category keywords'
       WHEN weak_cat IS NOT NULL THEN 'brand (default)'
       ELSE 'none' END AS category_source
FROM (
  SELECT *, {brand_case(strong_brand)} AS strong_cat,
            {content_case} AS content_cat,
            {brand_case(weak_brand)} AS weak_cat
  FROM (
    SELECT *,
      lower(strip_accents(coalesce(name, '') || ' ' ||
            replace(replace(coalesce(array_to_string(categories_tags, ' '), ''), '-', ' '), ':', ' '))) AS txt
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

con.sql("SELECT setseed(0.42)")
print("\nSPOT CHECK: 3 random products per category (keyword-classified)")
print(con.sql("""
    SELECT category, brand, name FROM nestle_cat
    WHERE category_source = 'name/category keywords' AND name IS NOT NULL
    QUALIFY row_number() OVER (PARTITION BY category ORDER BY random()) <= 3
    ORDER BY category
""").df().to_string(index=False))

con.sql("""COPY (SELECT brand, name, countries_tags[1] AS first_country
               FROM nestle_cat
               WHERE category = 'Unclassified' AND name IS NOT NULL
               ORDER BY brand, name)
           TO 'data/processed/unclassified_names.csv' (HEADER)""")

con.sql("""COPY (SELECT category, category_source, count(*) AS products
               FROM nestle_cat GROUP BY 1, 2 ORDER BY 1, 2)
           TO 'outputs/category_counts.csv' (HEADER)""")
