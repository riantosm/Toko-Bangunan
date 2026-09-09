# PostgreSQL Performance Lab

Sandbox untuk belajar membaca `EXPLAIN (ANALYZE, BUFFERS)` dan membuktikan efek
index dengan angka. **Terpisah dari skema aplikasi** — tabel `order_events` di
sini tidak ada di models/Alembic, hanya dipakai untuk eksperimen.

## Isi

| File | Fungsi |
|---|---|
| `seed.py` | drop+create `order_events`, bulk-load via asyncpg `COPY`, `ANALYZE` |
| `queries.sql` | query lambat + varian index, tiap blok diawali `EXPLAIN (ANALYZE, BUFFERS)` |
| `NOTES.md` | tabel hasil sebelum/sesudah: skenario · waktu · buffers · node plan |

## Menjalankan

```bash
# 1 juta baris (default); naikkan bila mau
uv run python -m db_lab.seed --rows 1000000

# jalankan eksperimen (butuh psql)
docker compose exec -T db psql -U toko -d tokobangunan -f - < db_lab/queries.sql
```

## Skema `order_events`

```
id            bigint  PK (identity)
order_id      bigint          -- 1..300_000
customer_id   integer         -- 1..20_000
department_id smallint        -- 1..4
event_type    text            -- created|confirmed|step_done|delivered|rejected
amount        numeric(12,2)
created_at    timestamptz     -- tersebar ~730 hari terakhir
```
