WITH rolling AS (
    SELECT
        *,
        avg(value) OVER (
            PARTITION BY region, age_group, season
            ORDER BY season_week
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS trailing_3wk,
        avg(value) OVER (
            PARTITION BY region, age_group, season
            ORDER BY season_week
            ROWS BETWEEN 5 PRECEDING AND 3 PRECEDING
        ) AS previous_3wk,
        count(*) OVER (
            PARTITION BY region, age_group, season
            ORDER BY season_week
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS trailing_count,
        count(*) OVER (
            PARTITION BY region, age_group, season
            ORDER BY season_week
            ROWS BETWEEN 5 PRECEDING AND 3 PRECEDING
        ) AS previous_count
    FROM flusurv
),
scored AS (
    SELECT
        current.*,
        CASE
            WHEN current.trailing_count = 3 AND current.previous_count = 3
            THEN current.trailing_3wk - current.previous_3wk
        END AS momentum_3wk,
        (
            SELECT count(*)
            FROM flusurv historical
            WHERE historical.region = current.region
              AND historical.age_group = current.age_group
              AND historical.season_week = current.season_week
              AND historical.season_start BETWEEN current.season_start - 10
                                                  AND current.season_start - 1
        ) AS historical_n,
        (
            SELECT avg(CASE WHEN historical.value <= current.value THEN 1.0 ELSE 0.0 END)
            FROM flusurv historical
            WHERE historical.region = current.region
              AND historical.age_group = current.age_group
              AND historical.season_week = current.season_week
              AND historical.season_start BETWEEN current.season_start - 10
                                                  AND current.season_start - 1
        ) * 100 AS historical_percentile
    FROM rolling current
)
SELECT * EXCLUDE (trailing_count, previous_count)
FROM scored
ORDER BY region, age_group, week_ending
