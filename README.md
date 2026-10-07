# Nestlé Product Range Analysis

Descriptive analysis of Nestlé's product range using Open Food Facts data
(Python, DuckDB, SQL).

**Status:** work in progress.

## Question
What does Nestlé's food product range look like in Open Food Facts: how are
nutrition values, Nutri-Score and NOVA distributed across categories and countries?

## Data
Open Food Facts (ODbL license). See DATA_SOURCE.md. The raw data file is not
stored in this repository.

## Product selection
A product is included if it has a brand tag starting with `nestle`, or a tag from
the reviewed brand list in `sql/brands.txt`. Decisions are explained in
`sql/brands_decisions.md`.

## Disclaimer
Independent analysis. Not affiliated with or endorsed by Nestlé.
