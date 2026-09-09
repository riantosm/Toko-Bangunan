# Hasil — EXPLAIN (ANALYZE, BUFFERS)

Dataset: `order_events`, **1.000.000 baris**, 100 MB. PostgreSQL 16 (container).
Angka dari `db_lab/queries.sql`. `Buffers` = `shared hit + read` (1 buffer = 8 KB);
metrik paling stabil karena waktu eksekusi ikut kondisi cache. Timing dimatikan
per-node (`TIMING OFF`), yang dicatat adalah **Execution Time** total.

---

## A — Composite index: kolom equality dulu, kolom range terakhir

Query: 20 event terakhir untuk 1 pelanggan dalam 90 hari.
`WHERE customer_id = 12345 AND created_at >= now() - '90 days' ORDER BY created_at DESC LIMIT 20`

| # | Index | Plan | Exec time | Buffers |
|---|---|---|---:|---:|
| A1 | *(tidak ada)* | Parallel Seq Scan, `Rows Removed by Filter: 999 994` | 32.8 ms | 10 114 |
| A2 | `(customer_id, created_at DESC)` | Bitmap Index Scan → Bitmap Heap Scan | **0.21 ms** | **9** |
| A3 | `(created_at, customer_id)` | Index Scan Backward, `Index Cond` pakai range dulu | 7.6 ms | 486 |

**Kesimpulan:** A2 vs A1 → **~150× lebih cepat**, buffer 10 114 → 9. A3
membuktikan **urutan kolom penting**: dengan range di depan, index tetau harus
menelusuri semua entri rentang 90 hari lalu menyaring `customer_id` (486 buffer,
7.6 ms) — 50× lebih lambat dari A2 walau "ada index".

---

## B — Partial index: hanya indeks baris yang memang di-query

Query: rekap 30 hari untuk `event_type = 'rejected'` (~6% baris).
`SELECT count(*), sum(amount) WHERE event_type = 'rejected' AND created_at >= now() - '30 days'`

| # | Index | Plan | Exec time | Buffers | Ukuran index |
|---|---|---|---:|---:|---:|
| B1 | *(tidak ada)* | Parallel Seq Scan | 25.0 ms | 10 000 | — |
| B2 | `(event_type, created_at)` penuh | Bitmap Heap Scan | 15.4 ms | 2 209 | **36 MB** |
| B3 | `(created_at) WHERE event_type = 'rejected'` | Bitmap Heap Scan | **1.7 ms** | 2 203 | **1.3 MB** |

**Kesimpulan:** B3 vs B2 → index **27× lebih kecil** (1.3 MB vs 36 MB) untuk
jumlah buffer baca yang sama. Index kecil = lebih banyak muat di cache, lebih
murah di-maintain saat `INSERT`/`UPDATE`, dan `autovacuum` lebih ringan. Cocok
saat query selalu memfilter nilai yang sama (status, flag, "belum selesai").

---

## C — Covering index (`INCLUDE`) → Index Only Scan

Query: total & jumlah transaksi per department, rentang 14 hari.
`SELECT department_id, count(*), sum(amount) WHERE created_at >= now() - '14 days' GROUP BY department_id`

| # | Index | Plan | Exec time | Buffers | Heap Fetches |
|---|---|---|---:|---:|---:|
| C1 | `(created_at)` biasa | Bitmap Heap Scan (baca heap untuk `amount`, `department_id`) | 24.2 ms | 8 586 | — |
| C2 | `(created_at) INCLUDE (department_id, amount)` | **Index Only Scan** | **2.6 ms** | **99** | **0** |

**Kesimpulan:** C2 vs C1 → **~9× lebih cepat**, buffer 8 586 → 99. Semua kolom
yang dibutuhkan ada di dalam index (`INCLUDE`), jadi PostgreSQL tidak perlu
menyentuh tabel sama sekali (`Heap Fetches: 0`). Perlu `VACUUM` supaya
*visibility map* ter-set — kalau tabel banyak baris "kotor", Heap Fetches naik
dan keuntungannya hilang.

---

## D — Keyset pagination vs deep OFFSET

| # | Query | Plan | Exec time | Buffers | Baris dibaca |
|---|---|---|---:|---:|---:|
| D1 | `ORDER BY id LIMIT 20 OFFSET 500000` | Index Scan, buang 500 000 baris | 58.3 ms | 6 357 | 500 020 |
| D2 | `WHERE id > 500000 ORDER BY id LIMIT 20` | Index Scan | **0.03 ms** | **7** | 20 |

**Kesimpulan:** `OFFSET` tetap **membaca lalu membuang** semua baris yang
dilewati — makin dalam halaman, makin lambat (linier). Keyset ("ambil setelah
id/created_at terakhir") **loncat langsung** lewat index: konstan, ~2 000× lebih
cepat di halaman ke-25.000. → diterapkan ke `GET /orders` di 10.3.

---

## E — CTE + window function (query analitik "SQL kompleks")

"3 pelanggan dengan total nilai transaksi tertinggi, per bulan" —
`WITH monthly AS (GROUP BY month, customer_id) , ranked AS (RANK() OVER (PARTITION BY month ORDER BY total DESC)) SELECT ... WHERE rnk <= 3`

- Plan: `Seq Scan` (filter `event_type IN (...)`, ~34% baris lolos) → `Sort`
  (external merge, **Disk: 10 MB**) → `GroupAggregate` (245 341 grup) →
  `Incremental Sort` (manfaatkan `month` yang sudah terurut) → `WindowAgg`
  dengan **`Run Condition: rank() <= 3`** (PG 15+ menghentikan window lebih awal) → `Sort`.
- Execution Time: **930 ms**, JIT aktif.
- **Cara mempercepat:** naikkan `work_mem` (mis. `SET work_mem = '64MB'`) supaya
  sort besar tidak tumpah ke disk; `date_trunc` bisa dibuat index ekspresi bila
  query ini sering dipakai. Tanpa itu pun 1 juta baris → 245k grup → ranking
  selesai < 1 detik.
- Hasil nyata (cuplikan): tiap bulan memunculkan 3 `customer_id` teratas dengan
  `total` dan `events` — lihat output `queries.sql` blok E.

---

## Ringkasan 3+ optimasi (kriteria "Selesai bila")

| Optimasi | Sebelum | Sesudah | Faktor |
|---|---:|---:|---:|
| Composite index (equality→range) | 32.8 ms / 10 114 buf | 0.21 ms / 9 buf | ~150× |
| Partial index (index 27× lebih kecil) | 36 MB index | 1.3 MB index | 27× lebih ramping |
| Covering index → Index Only Scan | 24.2 ms / 8 586 buf | 2.6 ms / 99 buf | ~9× |
| Keyset pagination vs OFFSET 500k | 58.3 ms / 6 357 buf | 0.03 ms / 7 buf | ~2000× |
