import duckdb

con = duckdb.connect("nestle.duckdb")
MIN_N = 20

def run(title, sql, filename):
    df = con.sql(sql).df()
    print(f"\n=== {title} ===")
    print(df.to_string(index=False))
    df.to_csv(f"outputs/{filename}", index=False)

run("Products per category", """
    SELECT category, count(*) AS products,
           round(100.0*count(*)/sum(count(*)) OVER (), 1) AS pct_of_range
    FROM nestle_cat GROUP BY 1 ORDER BY 2 DESC
""", "q1_products_per_category.csv")

def stat(col, digits):
    return f"""
      count({col}) AS n_{col},
      CASE WHEN count({col}) >= {MIN_N} THEN round(median({col}), {digits}) END AS {col}_median,
      CASE WHEN count({col}) >= {MIN_N} THEN round(quantile_cont({col}, 0.25), {digits}) END AS {col}_p25,
      CASE WHEN count({col}) >= {MIN_N} THEN round(quantile_cont({col}, 0.75), {digits}) END AS {col}_p75"""

run("Sugar per 100 g by category (median and middle half; shown if n >= 20)",
    f"SELECT category, {stat('sugars', 1)} FROM nestle_cat GROUP BY 1 ORDER BY 1",
    "q2_sugar_by_category.csv")
run("Salt per 100 g by category",
    f"SELECT category, {stat('salt', 2)} FROM nestle_cat GROUP BY 1 ORDER BY 1",
    "q3_salt_by_category.csv")
run("Saturated fat per 100 g by category",
    f"SELECT category, {stat('sat_fat', 1)} FROM nestle_cat GROUP BY 1 ORDER BY 1",
    "q4_satfat_by_category.csv")
run("Energy (kcal per 100 g) by category",
    f"SELECT category, {stat('kcal', 0)} FROM nestle_cat GROUP BY 1 ORDER BY 1",
    "q5_energy_by_category.csv")

run("Nutri-Score by category (share of graded products)", """
    SELECT category, upper(nutriscore_grade) AS grade, count(*) AS products,
           round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY category), 1) AS pct_of_graded
    FROM nestle_cat WHERE nutriscore_grade IS NOT NULL
    GROUP BY 1, 2 ORDER BY 1, 2
""", "q6_nutriscore_by_category.csv")

run("NOVA group by category (share of products with a NOVA group)", """
    SELECT category, nova_group, count(*) AS products,
           round(100.0*count(*)/sum(count(*)) OVER (PARTITION BY category), 1) AS pct_of_nova
    FROM nestle_cat WHERE nova_group IS NOT NULL
    GROUP BY 1, 2 ORDER BY 1, 2
""", "q7_nova_by_category.csv")

run("Top 15 countries by number of products (excluding 'world')", """
    SELECT country, count(*) AS products FROM (
        SELECT unnest(countries_tags) AS country FROM nestle_cat)
    WHERE country <> 'en:world'
    GROUP BY 1 ORDER BY 2 DESC LIMIT 15
""", "q8_top_countries.csv")

run("Products per brand", """
    SELECT brand, count(*) AS products FROM nestle_cat GROUP BY 1 ORDER BY 2 DESC
""", "q9_products_per_brand.csv")
