import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

con = duckdb.connect("nestle.duckdb")
OUT = "outputs/charts/"
MIN_N = 20
SRC = "Source: Open Food Facts (ODbL), snapshot 5 Oct 2026. Independent analysis, not affiliated with Nestlé."
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

def save(fig, name):
    fig.text(0.01, 0.01, SRC, fontsize=7, color="gray")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT + name, dpi=150)
    plt.close(fig)
    print("saved", name)

# 1. Products per category
df = con.sql("SELECT category, count(*) AS n FROM nestle_cat GROUP BY 1 ORDER BY 2").df()
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(df.category, df.n, color="#4C72B0")
for i, v in enumerate(df.n):
    ax.text(v + 6, i, f"{v:,}", va="center")
ax.set_xlabel("Number of products")
ax.set_title(f"Nestlé products in Open Food Facts, by category (n = {df.n.sum():,})")
save(fig, "01_products_per_category.png")

# 2-4. Box plots of nutrients
def box(col, xlabel, name, title):
    d = con.sql(f"SELECT category, {col} AS v FROM nestle_cat WHERE {col} IS NOT NULL").df()
    sizes = d.groupby("category")["v"].size()
    med = d.groupby("category")["v"].median()
    order = sorted([c for c in sizes.index if sizes[c] >= MIN_N], key=lambda c: med[c])
    data = [d.loc[d.category == c, "v"].values for c in order]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.boxplot(data, orientation="horizontal", showfliers=False, patch_artist=True,
               boxprops=dict(facecolor="#C6D8EC"),
               medianprops=dict(color="#C44E52", linewidth=2))
    ax.set_yticks(range(1, len(order) + 1))
    ax.set_yticklabels([f"{c}\n(n={sizes[c]})" for c in order])
    ax.set_xlabel(xlabel + "\nBox = middle half of products, line = median, outliers hidden. Categories with fewer than 20 values omitted.")
    ax.set_title(title)
    save(fig, name)

box("sugars", "Sugars, g per 100 g (or 100 ml) as listed", "02_sugar_by_category.png", "Sugar content by category")
box("salt", "Salt, g per 100 g (or 100 ml) as listed", "03_salt_by_category.png", "Salt content by category")
box("sat_fat", "Saturated fat, g per 100 g (or 100 ml) as listed", "04_satfat_by_category.png", "Saturated fat content by category")

# 5-6. Stacked bars for labels
def stacked(query, groups, colors, legend_title, name, title):
    d = con.sql(query).df()
    piv = d.pivot(index="category", columns="g", values="n").fillna(0)
    for g in groups:
        if g not in piv.columns:
            piv[g] = 0
    piv = piv[groups]
    tot = piv.sum(axis=1)
    keep = tot[tot >= MIN_N].index
    piv, tot = piv.loc[keep], tot.loc[keep]
    share = piv.div(tot, axis=0) * 100
    share = share.loc[share[groups[:2]].sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9, 5.5))
    left = [0.0] * len(share)
    for g in groups:
        vals = share[g].values
        ax.barh(range(len(share)), vals, left=left, color=colors[g], label=g)
        left = [l + v for l, v in zip(left, vals)]
    ax.set_yticks(range(len(share)))
    ax.set_yticklabels([f"{c}\n(n={int(tot[c])})" for c in share.index])
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of products that have this label. Categories with fewer than 20 labelled products omitted.")
    ax.legend(title=legend_title, ncol=len(groups), loc="upper center",
              bbox_to_anchor=(0.5, -0.14), frameon=False)
    ax.set_title(title)
    save(fig, name)

stacked("""SELECT category, upper(nutriscore_grade) AS g, count(*) AS n
           FROM nestle_cat WHERE nutriscore_grade IS NOT NULL GROUP BY 1, 2""",
        list("ABCDE"),
        {"A": "#038141", "B": "#85BB2F", "C": "#FECB02", "D": "#EE8100", "E": "#E63E11"},
        "Nutri-Score grade", "05_nutriscore_by_category.png",
        "Nutri-Score grades in the data, by category")

stacked("""SELECT category, CAST(nova_group AS VARCHAR) AS g, count(*) AS n
           FROM nestle_cat WHERE nova_group IS NOT NULL GROUP BY 1, 2""",
        ["1", "2", "3", "4"],
        {"1": "#D9E4F2", "2": "#A9C1E0", "3": "#6E93C4", "4": "#2F5C99"},
        "NOVA group", "06_nova_by_category.png",
        "NOVA groups in the data, by category")

# 7. Countries
d = con.sql("""SELECT country, count(*) AS n FROM (
                 SELECT unnest(countries_tags) AS country FROM nestle_cat)
               WHERE country <> 'en:world' GROUP BY 1 ORDER BY 2 DESC LIMIT 15""").df()
d["country"] = d.country.str.replace("en:", "").str.replace("-", " ").str.title()
d = d.iloc[::-1]
fig, ax = plt.subplots(figsize=(9, 5.5))
ax.barh(d.country, d.n, color="#4C72B0")
for i, v in enumerate(d.n):
    ax.text(v + 4, i, f"{v:,}", va="center")
ax.set_xlabel("Number of products listing the country in Open Food Facts")
ax.set_title("Top 15 countries by number of listed products")
save(fig, "07_top_countries.png")
