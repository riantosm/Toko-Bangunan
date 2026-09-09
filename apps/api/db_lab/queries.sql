-- PostgreSQL Performance Lab — order_events (1,000,000 rows)
-- Run:  docker compose exec -T db psql -U toko -d tokobangunan -f - < db_lab/queries.sql
-- Each scenario: measure BEFORE (no index) -> add index -> measure AFTER.
-- Numbers captured in NOTES.md.

\timing on
\pset pager off

-- reset lab indexes so the script is repeatable
DROP INDEX IF EXISTS ix_oe_cust_created;
DROP INDEX IF EXISTS ix_oe_type_created;
DROP INDEX IF EXISTS ix_oe_rejected_created;
DROP INDEX IF EXISTS ix_oe_created;
DROP INDEX IF EXISTS ix_oe_created_incl;
ANALYZE order_events;

-- =====================================================================
-- Scenario A — composite index: equality column first, range column last
-- "riwayat 90 hari terakhir untuk 1 pelanggan"
-- =====================================================================
\echo '--- A1 BEFORE (seq scan) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT id, order_id, event_type, amount, created_at
FROM order_events
WHERE customer_id = 12345
  AND created_at >= now() - interval '90 days'
ORDER BY created_at DESC
LIMIT 20;

CREATE INDEX ix_oe_cust_created ON order_events (customer_id, created_at DESC);

\echo '--- A2 AFTER (composite index) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT id, order_id, event_type, amount, created_at
FROM order_events
WHERE customer_id = 12345
  AND created_at >= now() - interval '90 days'
ORDER BY created_at DESC
LIMIT 20;

\echo '--- A3 wrong column order: (created_at, customer_id) — range column first ---'
DROP INDEX ix_oe_cust_created;
CREATE INDEX ix_oe_created_cust ON order_events (created_at, customer_id);
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT id, order_id, event_type, amount, created_at
FROM order_events
WHERE customer_id = 12345
  AND created_at >= now() - interval '90 days'
ORDER BY created_at DESC
LIMIT 20;
DROP INDEX ix_oe_created_cust;
CREATE INDEX ix_oe_cust_created ON order_events (customer_id, created_at DESC);

-- =====================================================================
-- Scenario B — partial index: only index the rare rows we query
-- "rekap penolakan 30 hari terakhir" (event_type = 'rejected' ~ 6%)
-- =====================================================================
\echo '--- B1 BEFORE (seq scan) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT count(*), coalesce(sum(amount), 0)
FROM order_events
WHERE event_type = 'rejected'
  AND created_at >= now() - interval '30 days';

\echo '--- B2 AFTER full index (event_type, created_at) ---'
CREATE INDEX ix_oe_type_created ON order_events (event_type, created_at);
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT count(*), coalesce(sum(amount), 0)
FROM order_events
WHERE event_type = 'rejected'
  AND created_at >= now() - interval '30 days';

\echo '--- B3 AFTER partial index WHERE event_type = rejected ---'
CREATE INDEX ix_oe_rejected_created ON order_events (created_at)
    WHERE event_type = 'rejected';
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT count(*), coalesce(sum(amount), 0)
FROM order_events
WHERE event_type = 'rejected'
  AND created_at >= now() - interval '30 days';

\echo '--- index sizes (full vs partial) ---'
SELECT indexrelname, pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname = 'order_events'
  AND indexrelname IN ('ix_oe_type_created', 'ix_oe_rejected_created')
ORDER BY indexrelname;

DROP INDEX ix_oe_type_created;
DROP INDEX ix_oe_rejected_created;

-- =====================================================================
-- Scenario C — covering index (INCLUDE) -> Index Only Scan
-- "total & jumlah transaksi per department untuk rentang tanggal"
-- =====================================================================
\echo '--- C1 BEFORE plain index on (created_at): Index Scan + heap fetch ---'
CREATE INDEX ix_oe_created ON order_events (created_at);
ANALYZE order_events;
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT department_id, count(*), sum(amount)
FROM order_events
WHERE created_at >= now() - interval '14 days'
GROUP BY department_id;
DROP INDEX ix_oe_created;

\echo '--- C2 AFTER covering index INCLUDE (department_id, amount): Index Only Scan ---'
CREATE INDEX ix_oe_created_incl ON order_events (created_at)
    INCLUDE (department_id, amount);
VACUUM ANALYZE order_events;   -- set visibility map so Index Only Scan skips the heap
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT department_id, count(*), sum(amount)
FROM order_events
WHERE created_at >= now() - interval '14 days'
GROUP BY department_id;
DROP INDEX ix_oe_created_incl;

-- =====================================================================
-- Scenario D — keyset pagination vs deep OFFSET
-- =====================================================================
\echo '--- D1 deep OFFSET (scans + throws away 500k rows) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT id, order_id, created_at
FROM order_events
ORDER BY id
LIMIT 20 OFFSET 500000;

\echo '--- D2 keyset (seek straight to the page) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
SELECT id, order_id, created_at
FROM order_events
WHERE id > 500000
ORDER BY id
LIMIT 20;

-- =====================================================================
-- Scenario E — CTE + window function (analytic query on lab data)
-- "3 pelanggan teratas berdasarkan total nilai transaksi, per bulan"
-- =====================================================================
\echo '--- E CTE + RANK() OVER (PARTITION BY month) ---'
EXPLAIN (ANALYZE, BUFFERS, TIMING OFF)
WITH monthly AS (
    SELECT date_trunc('month', created_at) AS month,
           customer_id,
           sum(amount)  AS total,
           count(*)     AS events
    FROM order_events
    WHERE event_type IN ('confirmed', 'delivered')
    GROUP BY 1, 2
),
ranked AS (
    SELECT month, customer_id, total, events,
           rank() OVER (PARTITION BY month ORDER BY total DESC) AS rnk
    FROM monthly
)
SELECT month, customer_id, total, events, rnk
FROM ranked
WHERE rnk <= 3
ORDER BY month DESC, rnk;

\echo '--- E (actual result, top 3 per month, last 6 months) ---'
WITH monthly AS (
    SELECT date_trunc('month', created_at) AS month,
           customer_id,
           sum(amount)  AS total,
           count(*)     AS events
    FROM order_events
    WHERE event_type IN ('confirmed', 'delivered')
    GROUP BY 1, 2
),
ranked AS (
    SELECT month, customer_id, total, events,
           rank() OVER (PARTITION BY month ORDER BY total DESC) AS rnk
    FROM monthly
)
SELECT to_char(month, 'YYYY-MM') AS month, customer_id,
       round(total) AS total, events, rnk
FROM ranked
WHERE rnk <= 3
ORDER BY month DESC, rnk
LIMIT 18;

-- clean up
DROP INDEX IF EXISTS ix_oe_cust_created;
