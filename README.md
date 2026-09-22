# FluView Pulse

FluView Pulse is a reproducible U.S. respiratory surveillance dashboard that asks:

> Where is outpatient respiratory illness increasing this season, and how do
> influenza hospitalization rates differ across age groups?

It combines two CDC surveillance systems without treating them as equivalent:

- **ILINet** — the percentage of outpatient visits meeting the influenza-like
  illness (ILI) definition. ILI is syndromic and is not laboratory-confirmed influenza.
- **FluSurv-NET** — weekly laboratory-confirmed influenza hospitalization rates
  in participating counties across 14 states, covering roughly 10% of the U.S.
  population. It is not a national census.

Both feeds are aggregate, preliminary, and revision-prone. No PHI is used.

**Live dashboard:** [fluview-pulse.onrender.com](https://fluview-pulse.onrender.com)

## What the dashboard shows

The guided overview answers the core surveillance questions with:

1. National ILINet activity against recent seasons
2. Signed three-week momentum ranked across the 10 HHS regions
3. A regional season-week heatmap
4. FluSurv-NET weekly hospitalization rates against recent seasons
5. Latest hospitalization rates by age group
6. Aligned—but deliberately separate—outpatient and hospitalization panels

The Analysis view adds source, season, and geography filters; sortable/filterable
records; methodology context; and CSV export.

## Methods

### Season and time keys

CDC MMWR weeks are assigned to influenza seasons beginning at week 40. The
dashboard defaults to the latest season shared by both sources. Portfolio
screenshots use the latest complete season when the emerging season is too sparse,
and are labeled accordingly.

### Recent momentum

For each source/geography/age series:

```text
momentum = mean(latest 3 reported weeks) - mean(preceding 3 reported weeks)
```

The dashboard ranks signed changes as “largest increases.” It does not create
alert levels, risk scores, forecasts, or statistical significance claims.

### Historical context

The empirical percentile compares an observation with the same season week from
up to 10 prior complete seasons. The available historical sample count is shown
with the percentile. A median/MAD robust z-score is explored in the EDA notebook,
but is not promoted to the dashboard because small samples and unusual seasons
can make standardized thresholds look more precise than they are.

## Data pipeline

```text
CDC downloads/APIs
        ↓
dated, compressed raw snapshots
        ↓
pandas source contracts and normalization
        ↓
DuckDB SQL window and historical models
        ↓
validated Parquet marts
        ↓
Plotly Dash
```

- FluSurv-NET uses the supported CDC Socrata dataset
  [`kvib-3txy`](https://data.cdc.gov/resource/kvib-3txy.json).
- ILINet uses FluView Interactive's undocumented CSV download backend. The
  adapter validates its schema and retains the last valid snapshot on failure.
- Every retrieval is preserved under `data/raw/<source>/` with a checksum sidecar.
- `data/manifest.json` records independent source health, retrieval dates,
  surveillance-through dates, row counts, and generated marts.
- DuckDB models in `sql/models/` produce dashboard-ready Parquet files.

## Repository layout

```text
app/                  Dash application, figures, and responsive styling
data/raw/             Dated source vintages and checksum metadata
data/processed/       Validated source tables and analytical marts
docs/screenshots/     Portfolio-ready chart captures
notebooks/            Executed EDA and methodology checks
scripts/              Convenience entry points
sql/models/           DuckDB analytical SQL
src/fluview/          Ingestion, normalization, and pipeline package
tests/                Contracts, metric tests, and app smoke test
```

## Run locally

Python 3.11+ is required.

```bash
python -m pip install -e ".[dev]"
python -m fluview.pipeline
python -m app.app
```

Open `http://localhost:8050`.

To rebuild marts without network access:

```bash
python -m fluview.pipeline --offline
```

Validation:

```bash
pytest
ruff check .
python -m jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb \
  --output 01_eda.ipynb --output-dir notebooks
```

## Weekly refresh

`.github/workflows/refresh-data.yml` runs on Saturdays after the CDC Friday
publication window and can also be triggered manually. It:

1. refreshes each source independently;
2. preserves the last valid source snapshot if an adapter fails;
3. validates schemas, metrics, and app startup;
4. reports degraded source health in the workflow summary and a GitHub issue; and
5. opens a reviewable data-refresh pull request.

Merging the PR updates the artifacts consumed by the Render deployment.

## Deploy to Render

`render.yaml` defines one free Python web service:

```text
build: pip install .
start: gunicorn --bind 0.0.0.0:$PORT app.app:server
```

The app is read-only and serves committed Parquet artifacts, so it does not rely
on Render's ephemeral filesystem. Free services spin down after 15 minutes of
inactivity; the first request after idle time can take longer.

## Caveats

- Recent values can be revised as providers and surveillance sites report late.
- ILINet provider participation varies by place and week; jurisdiction data may
  not represent the entire population.
- ILINet age counts come from the subset of providers reporting age detail and
  are secondary to the hospitalization age view.
- FluSurv-NET geography reflects participating surveillance sites, not nationwide
  state coverage.
- The two systems have different denominators, coverage, and lag. Parallel trends
  can be compared descriptively but do not establish causality.
- ISO week-derived display dates can differ at rare year boundaries from official
  MMWR date conventions; CDC's supplied week/date fields remain the source of truth.

## Sources

- [CDC FluView overview](https://www.cdc.gov/fluview/overview/index.html)
- [FluView Interactive](https://gis.cdc.gov/grasp/fluview/FluPortalDashboardWidget_ILINet.html)
- [FluSurv-NET methodology](https://www.cdc.gov/fluview/overview/influenza-hospitalization-surveillance.html)
- [RESP-NET Rates and Clinical Data](https://data.cdc.gov/Public-Health-Surveillance/RESP-NET-Rates-and-Clinical-Data/kvib-3txy)

Data are public CDC surveillance aggregates. This project is for descriptive
analytics and portfolio demonstration, not medical guidance.
