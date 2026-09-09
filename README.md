# Toko Bangunan — AI Order Intake & SLA Dashboard

Aplikasi web fullstack: sebuah toko bangunan menerima pesanan dalam bentuk
**teks bebas** (seperti chat WhatsApp), sebuah **LLM lokal** menguraikannya menjadi
order terstruktur, order berjalan lewat **workflow persetujuan berjenjang** dengan
pencatatan durasi, dan manajemen memantau **dashboard SLA**.

- **`apps/web`** — frontend Next.js 16 (App Router, React 19, Tailwind v4)
- **`apps/api`** — backend FastAPI (Python 3.12, async SQLAlchemy 2.0)

> **Status:** Fase 0–12 selesai — demo lokal lengkap & berjalan end-to-end (Docker + Ollama).
> 42 test backend + Vitest hijau, CI aktif. Fase 13 (deploy cloud) ditunda, opsional.

---

## Roadmap

| # | Bagian | Status |
|---|---|---|
| 0 | Setup — Docker, Alembic, FastAPI + Next skeleton | ✅ |
| 1 | Order CRUD (REST, layering, tests) | ✅ |
| 2 | AI Intake (Ollama, structured output, fuzzy match) | ✅ |
| 3 | Async jobs (ARQ + Redis, polling, idempotensi) | ✅ |
| 4 | Workflow + SLA (state machine, generated column) | ✅ |
| 5 | Dashboard SLA (agregasi SQL, Recharts) | ✅ |
| 6 | Auth (JWT + role, middleware, login/logout) | ✅ |
| 7 | API hardening — rate limiting + error envelope + requestId + middleware JWT signature | ✅ |
| 8 | Kanal WhatsApp — webhook + HMAC, auto-reply, state percakapan, simulator; departments/workflow_types | ✅ |
| 9 | Laporan harian terjadwal (APScheduler → PDF → email) + abstraksi `TaskQueue` | ✅ |
| 10 | PostgreSQL performance lab — `EXPLAIN (ANALYZE, BUFFERS)`, index, CTE/window; keyset pagination | ✅ |
| 11 | CI (GitHub Actions — 2 job: api ruff/mypy/pytest, web typecheck/lint/vitest/build) | ✅ |
| 12 | Evaluasi akurasi AI (gold set 30, harness metrik F1/MAE/halusinasi) | ✅ |
| 13 | Deploy cloud (Vercel + Cloud Run) + WhatsApp Cloud API + Cloud Tasks | ⏸️ opsional — ditunda |

**Status: Fase 0–12 selesai** ✅ — cakupan proyek (demo lokal) sudah lengkap dan
berjalan end-to-end (Docker + Ollama). Fase 13 (deploy cloud) sengaja ditunda:
titik ganti-nya sudah disiapkan di kode — `TaskQueue` (`CloudTasksQueue` sketsa),
`MessageChannel` (`WhatsAppChannel` siap pakai bila `WHATSAPP_TOKEN` diisi),
env-driven config — jadi bisa diaktifkan kapan saja tanpa mengubah kode bisnis.

---

## Daftar Isi

1. [Ringkasan Fitur](#ringkasan-fitur)
2. [Arsitektur](#arsitektur)
3. [Tech Stack](#tech-stack)
4. [Struktur Proyek](#struktur-proyek)
5. [Menjalankan (Development)](#menjalankan-development)
6. [Model Data](#model-data)
7. [Daftar Endpoint](#daftar-endpoint)
8. [Testing](#testing)

---

## Ringkasan Fitur

### 1. Order manual (CRUD)
- `POST /orders`, `GET /orders` (berpaginasi), `GET /orders/{id}`.
- Pola berlapis: **router → service → repository**. Router tidak tahu SQL, service memegang aturan bisnis.
- Relasi 1-ke-banyak `orders` → `order_items` (`ON DELETE CASCADE`).
- Frontend: halaman daftar (baris bisa diklik penuh), form buat order, halaman detail.

### 2. AI Intake — teks bebas menjadi order terstruktur
- Endpoint `POST /orders/intake` menerima pesan mentah pelanggan.
- **Ekstraksi**: LLM lokal (**Ollama + Gemma 3**, tanpa biaya token) diminta membalas JSON sesuai skema (`format: json`), lalu divalidasi **Pydantic**; gagal → retry 1× → tandai `needs_review`.
- **Pencocokan produk**: nama barang dari AI dicocokkan ke katalog memakai ekstensi **`pg_trgm`** (`similarity()`), skor di bawah ambang → `product_id = NULL`.
- **Guardrail `needs_review`** aktif bila: `confidence < 0.6`, ada item tak dikenal, atau `intent != "order"`.
- Prompt disimpan di file terpisah (`app/prompts/extract_order.txt`) — mudah diubah & dibandingkan versinya.

### 3. Background jobs (async)
- Intake tidak memblok HTTP: endpoint balas **`202 Accepted` + `job_id`** seketika; pekerjaan berat dijalankan **proses worker terpisah** (**ARQ + Redis**).
- Tabel `jobs` menyimpan `status` (`queued → processing → done | error`) dan `progress`.
- Frontend: setelah submit, **polling** `GET /jobs/{id}` tiap 2 detik, menampilkan progress bar, lalu auto-redirect ke order saat `done`.
- **Idempotensi**: header `Idempotency-Key` + tabel `processed_requests` — submit ganda tidak membuat 2 order.

### 4. Workflow persetujuan + SLA
- Order `draft → confirmed` otomatis membuat 3 `workflow_steps` (Verifikasi Stok → Approval Manajer → Konfirmasi Pembayaran), tiap langkah punya target SLA.
- Menyelesaikan langkah (`approved` / `rejected`) mengisi `completed_at` dan mengaktifkan langkah berikutnya; langkah terakhir → order `done`, penolakan → `rejected`.
- **`elapsed_minutes`** = *generated column* PostgreSQL (`GENERATED ALWAYS AS ... STORED`) — dihitung otomatis dari `completed_at - assigned_at`.
- Semua timestamp `timestamptz` (setelah migrasi khusus dari `timestamp` biasa).
- Frontend: alur persetujuan interaktif di halaman detail order.

### 5. Dashboard SLA
- Halaman `/dashboard` = **React Server Component**, mengambil 4 endpoint metrics paralel (`Promise.all`).
- **Agregasi dilakukan di SQL**: `GROUP BY`, `date_trunc('day', ...)`, `percentile_cont(0.9) WITHIN GROUP (...)`, `COUNT(*) FILTER (WHERE ...)`.
- Isi:
  - **KPI cards** — order masuk, selesai, WIP, % SLA terpenuhi.
  - **Bar chart** durasi per langkah (rata-rata & p90).
  - **Line chart** tren % SLA terpenuhi per hari.
  - **Tabel aging** — order menunggu terlama saat ini, ditandai bila lewat SLA.
- Filter rentang (7/30/90 hari) via URL `?days=` (`searchParams`).
- Chart pakai **Recharts** dengan warna dari CSS variable design system.

### 6. Autentikasi (JWT + role)
- `POST /auth/login` — verifikasi password **Argon2**, terbitkan **JWT** (HS256, klaim `sub`/`role`/`exp`/`iss`).
- Dependency FastAPI: `get_current_user` (verifikasi penuh) dan `require_role("manager", ...)`.
- Proteksi per-router: `/metrics/*` → hanya `manager`/`admin`; sisanya → semua yang login.
- Frontend:
  - Halaman `/login`, token disimpan di **cookie** (dibaca client *dan* server component).
  - **`middleware.ts`** — verifikasi **signature + `exp` + `iss`** JWT pakai `jose` (Edge-compatible); token dipalsukan/kedaluwarsa → redirect `/login` + hapus cookie.
  - Server Component gate via `requireToken()` / `requireRole()`; tombol **Keluar** di nav.

### 7. API hardening
- **Error envelope seragam** — semua error (`401/403/404/409/422/429/500`) balas `{ "error": { "code", "message", "requestId", "details"? } }` lewat exception handler global; hierarki `ApiError` (`UnauthorizedError`, `NotFoundError`, `RateLimitError`, …).
- **`requestId`** per request (contextvar) → header `X-Request-Id` + muncul di log.
- **Structured logging** — 1 baris JSON per request (`method`, `path`, `status`, `duration_ms`, `request_id`).
- **Rate limiting tanpa Redis** — tabel `rate_counters` + `INSERT … ON CONFLICT DO UPDATE count+1` per window 1 menit. `/orders/intake` dibatasi `settings.rate_limit_intake_per_min` (default 10); balas `429` + `Retry-After` + `X-RateLimit-*`.

### 8. Kanal WhatsApp (chat pelanggan)
- **Webhook = Next.js Route Handler** `app/api/webhooks/whatsapp/route.ts` — `GET` handshake Meta (echo `hub.challenge`); `POST` verifikasi **`X-Hub-Signature-256`** (HMAC-SHA256, `timingSafeEqual`) **sebelum** parsing → `401` kalau salah; forward tiap pesan ke FastAPI `POST /internal/wa-message` (header `X-Internal-Secret`).
- **`conversation_service.handle_incoming`** — simpan pesan → get/create `conversations` (state per `wa_id`) → `"KONFIRMASI"` + draft aktif → `confirm_order` → selain itu `extract_order` + `match_product` → **merge item ke draft order percakapan** → balasan **template deterministik** → kirim via channel.
- **`MessageChannel`** abstract: `MockChannel` (dev — tulis balasan ke `raw_messages`) vs `WhatsAppChannel` (Graph API, hanya jika `WHATSAPP_TOKEN` terisi).
- **`/simulator`** — halaman + route handler `app/api/simulator/send` yang menandatangani payload berbentuk Cloud API lalu POST ke webhook asli → demo end-to-end **tanpa Meta**.
- **`departments` + `workflow_types`** + partial index `workflow_steps (assignee_id, assigned_at) WHERE completed_at IS NULL`; `/metrics/*` menerima `?department_id=`, dashboard punya filter department.

### 9. Laporan harian terjadwal + abstraksi `TaskQueue`
- **`run_daily_report(session, day, *, force)`** — 1 hari: query ringkasan SQL (order masuk/confirmed/done/rejected, langkah selesai & lewat SLA, rata-rata menit, pecahan per jenis langkah) → **PDF** (`reportlab`, Python murni) → **email + lampiran** (`aiosmtplib` async) → ditangkap **Mailpit** (`localhost:8025`).
- **Idempoten per tanggal** — tabel `report_runs` (PK = `report_date`); sudah terkirim → `status: skipped`. `?force=true` untuk kirim ulang manual.
- **Endpoint `POST /internal/nightly-report`** (header `X-Internal-Secret`, opsional `?date=` & `?force=`) — "HTTP worker" yang dipanggil scheduler/Cloud Scheduler.
- **APScheduler di `lifespan` FastAPI** — cron `0 22 * * *` (`Asia/Jakarta`, `misfire_grace_time=1h`) memanggil report; **digerbang `SCHEDULER_ENABLED`** (default `false`) — 1 proses, tanpa worker terpisah.
- **`TaskQueue` ABC** (`app/core/taskqueue.py`) — jawaban **Q3**: `LocalTaskQueue` (push ke ARQ/Redis) dipakai demo & test; `CloudTasksQueue` (sketsa — buat Google Cloud Task yang POST ke HTTP worker) untuk produksi. Call site pakai `get_task_queue().enqueue(name, *args)` sehingga transport bisa ditukar tanpa menyentuh kode bisnis.

### 10. PostgreSQL performance lab + keyset pagination
- **`db_lab/`** — sandbox terpisah dari skema app: `seed.py` memuat **1 juta baris** `order_events` via asyncpg `COPY` (~5 dtk); `queries.sql` menjalankan `EXPLAIN (ANALYZE, BUFFERS)` sebelum/sesudah tiap index; `NOTES.md` mencatat angkanya.
- **4 optimasi terbukti dengan angka**: composite index (equality→range, ~150×), partial index (index 27× lebih kecil), covering index `INCLUDE` → Index Only Scan (~9×), keyset vs `OFFSET 500k` (~2000×). Plus 1 query analitik **CTE + `RANK() OVER (PARTITION BY month)`** ("3 pelanggan teratas per bulan").
- **Diterapkan ke app** — `GET /orders` pindah dari `page/offset` ke **keyset** (`?limit=&after=<id>`): balas `{ items, next_cursor }`, PostgreSQL *seek* langsung lewat `orders_pkey` (tanpa `OFFSET`), biaya rata berapa pun dalamnya halaman. Frontend punya tombol "Muat lebih banyak →".

### 11. CI (GitHub Actions)
- **`.github/workflows/ci.yml`** — jalan tiap `push` ke `main` & tiap PR, 2 job paralel:
  - **api** — `services.postgres:16`, `uv sync`, buat DB `tokobangunan_test`, lalu `ruff check` + `mypy` + `pytest`.
  - **web** — `pnpm install --frozen-lockfile`, lalu `tsc --noEmit` + `eslint` + `vitest run` + `next build`.
- **`mypy`** dikonfigurasi (`[tool.mypy]`, override `ignore_missing_imports` untuk `reportlab`/`apscheduler`) — sekarang benar-benar hijau.
- **Vitest** ditambahkan di `apps/web` — unit test murni (`lib/orders.test.ts`: `parseCursor` untuk cursor keyset).
- Branch protection ("wajib 2 check hijau + 1 review sebelum merge") diaktifkan di Settings repo GitHub.

### 12. Evaluasi akurasi AI
- **`apps/api/eval/`** — harness untuk mengukur `extract_order()` supaya perubahan prompt/model bisa dibandingkan dengan angka.
  - `gold.jsonl` — 30 contoh + anotasi manual (typo, sinonim satuan `karung→sak`/`galon→kaleng`, kata bilangan `setengah→0.5`, multi-item, 3 intent).
  - `metrics.py` — skoring **murni & ter-unit-test**: alignment item greedy (SequenceMatcher ≥ 0.6), lalu cek `name`/`unit`/`quantity`.
  - `run.py` — jalankan model ke semua contoh, cetak tabel, simpan `results/<timestamp>.json` (dengan `prompt_hash`).
- **Metrik**: JSON validity rate · intent accuracy & macro-F1 & P/R/F1 per kelas · order exact-match · item P/R/F1 · unit/qty accuracy · **qty MAE** · **hallucination rate**.
- **Regression testing prompt**: `prompt_hash` (SHA-256 dari file prompt) tersimpan di tiap hasil → ubah 1 kalimat prompt, jalankan lagi, diff dua `results/*.json`.
- `uv run python -m eval.run --model gemma3:1b` → A/B model.

### Fondasi lintas fitur
- **Desain sistem** (`apps/web/app/globals.css` + `apps/web/app/components/ui.tsx`): tema **light**, token Tailwind v4 `@theme`, hairline border, satu aksen violet, primitif bersama (`Card`, `Button`, `Badge`, `Table`, `Field`, …).
- **Migrasi** semua lewat Alembic (autogenerate + edit manual untuk `pg_trgm` & generated column).
- **Git**: commit kecil, *Conventional Commits* (`feat:`, `fix:`, `test:`, `chore:`).
- **Docker Compose** untuk infrastruktur (Postgres, Redis); app dijalankan langsung di host saat dev.

---

## Arsitektur

```
   WhatsApp / Meta ─(webhook, HMAC)─┐
                                    v
   Staff / Manajer     ┌───────────────────────────┐
   ───────────────────>│   Next.js 16 (App Router)  │
                       │   - /login, /orders        │  Server Components
                       │   - /dashboard, /simulator │  middleware verifikasi
                       │   - route handlers:        │    signature JWT (jose)
                       │     /api/webhooks/whatsapp  │
                       │     /api/simulator/send     │
                       └────────────┬──────────────┘
                                    │ HTTPS REST (Bearer JWT) · /internal (X-Internal-Secret)
                                    v
                       ┌───────────────────────────┐
   APScheduler ───────>│   FastAPI (Python, async) │
   cron 22:00 (lifespan)│   /auth /orders /workflow  │
   → nightly-report     │   /metrics /internal       │  error envelope + requestId
                       │   /conversations /jobs      │  rate limiter (rate_counters)
                       │   TaskQueue (local ARQ /    │  laporan harian → PDF + email
                       │     Cloud Tasks sketch)     │
                       └───┬───────────┬──────┬───┬─┘
        enqueue job        │           │      │   │ SMTP  ┌──────────────┐
                           v           │      │   └──────>│ Mailpit      │
                 ┌──────────────┐      │      │           │ :8025 (demo) │
                 │ Worker (ARQ) │──────┼──────┤           └──────────────┘
                 │ intake +     │      │      │  async SQLAlchemy
                 │ wa-message   │      │      v
                 └──────┬───────┘      │   ┌──────────────┐
                        │ HTTP         │   │ PostgreSQL 16│
                        v              │   │ + pg_trgm    │
                 ┌──────────────┐   ┌──┴─┐ │ + generated  │
                 │ Ollama       │   │Redis│ │   + partial  │
                 │ gemma3:4b/1b │   │(ARQ)│ │     index    │
                 └──────────────┘   └─────┘ └──────────────┘
```

**Protokol antar komponen**

| Dari | Ke | Cara |
|---|---|---|
| WhatsApp / Meta (atau simulator) | Next.js route handler | webhook `POST`, header `X-Hub-Signature-256` (HMAC-SHA256) |
| Browser | Next.js | HTTPS; data diambil di Server Component; cookie JWT |
| Next.js → FastAPI | REST | `Authorization: Bearer <jwt>` (user) atau `X-Internal-Secret` (`/internal/*`) |
| FastAPI | PostgreSQL | connection pool async (`asyncpg`) |
| FastAPI | Worker | `TaskQueue.enqueue()` → Redis (ARQ) lokal / Cloud Tasks (sketsa) |
| APScheduler (lifespan) | FastAPI | panggil `run_daily_report` tiap 22:00 (`SCHEDULER_ENABLED`) |
| FastAPI | Mailpit / SMTP | `aiosmtplib` — email laporan harian + lampiran PDF |
| Worker | Ollama | HTTP `localhost:11434` (`/api/chat`, JSON mode) |
| Worker | Channel | `MockChannel` (dev) / `WhatsAppChannel` → Graph API |

---

## Tech Stack

| Layer | Teknologi | Alasan |
|---|---|---|
| Frontend | **Next.js 16** (App Router) + **React 19** + **TypeScript** | RSC/SSR, routing modern, type-safety |
| Styling | **Tailwind CSS v4** (`@theme`) + primitif sendiri (`app/components/ui.tsx`) | Design system konsisten, hairline, satu aksen |
| Charting | **Recharts** | Chart dashboard, warna dari CSS variable |
| Backend / API | **Python 3.12** + **FastAPI** | Async native, OpenAPI otomatis, performa tinggi |
| Validasi & config | **Pydantic v2** + **pydantic-settings** | Kontrak data ketat FE–BE, config dari env |
| ORM / Migrasi | **SQLAlchemy 2.0** (async) + **Alembic** | Query kompleks + versioning schema |
| Database | **PostgreSQL 16** (+ ekstensi **`pg_trgm`**, **generated column**, JSONB) | JOIN kompleks, agregasi, indexing, fuzzy match |
| Background jobs | **ARQ** + **Redis 7**, di balik abstraksi **`TaskQueue`** (local ARQ / Cloud Tasks sketch) | Task async, proses worker terpisah, retry, idempotensi; transport bisa ditukar (Q3) |
| Laporan terjadwal | **APScheduler** (cron di `lifespan`) + **reportlab** (PDF) + **aiosmtplib** (SMTP async) + **Mailpit** (dev) | Laporan harian SLA → PDF → email, idempoten per tanggal |
| LLM lokal | **Ollama** + **Gemma 3** (`gemma3:4b` / `gemma3:1b`) | Ekstraksi order **tanpa biaya token** (Q1) |
| Eval AI | harness sendiri (`eval/`) — gold set 30, F1/MAE/hallucination rate, `prompt_hash` | Bandingkan versi prompt/model dengan angka |
| Auth | **PyJWT** (HS256) + **Argon2** (`argon2-cffi`); middleware Next.js verifikasi signature pakai **`jose`** — OAuth/OIDC *(rencana)* | Stateless, standar industri |
| Rate limiting | tabel **`rate_counters`** + `INSERT … ON CONFLICT` (fixed window, tanpa Redis) | `429` + `Retry-After` + `X-RateLimit-*` |
| Observability | **structured logging JSON** + `requestId` (contextvar → `X-Request-Id`) · Sentry *(rencana)* | Korelasi log ↔ response |
| Kanal WhatsApp | **WhatsApp Cloud API** (Meta) shape + webhook **HMAC-SHA256** di Next.js route handler; dev pakai `/simulator` | Chat pelanggan → order otomatis |
| Testing BE | **pytest** + **pytest-asyncio** + **httpx** (`ASGITransport`) — coverage *(rencana)* | Test API & unit tanpa menyalakan server |
| Testing FE | **tsc --noEmit** + **ESLint** + **Vitest** (unit) — Playwright *(rencana)* | Type-check + unit/E2E |
| Kualitas kode | **Ruff** + **mypy** (BE) · **ESLint** + **TypeScript strict** (FE) | Lint & type-check |
| Kontainer | **Docker Compose** (Postgres, Redis) | Infrastruktur dev reproducible |
| Version control | **Git** + **GitHub** — *Conventional Commits* | Riwayat rapi, commit kecil |
| CI/CD | **GitHub Actions** — 2 job (api: ruff/mypy/pytest + Postgres service · web: tsc/eslint/vitest/build) | Lint → type-check → test tiap PR |
| Cloud | **Vercel** (web) + **Cloud Run** (api) + **Cloud SQL** + **Cloud Tasks / Scheduler** *(rencana, Fase 13 — `CloudTasksQueue` sudah disketsakan)* | Sesuai target produksi; demo jalan lokal |
| AI coding assistant | **Claude Code** | Scaffolding, test, review |
| Package manager | **uv** (Python) · **pnpm** (JS) | Cepat, lockfile deterministik |

*Baris bertanda **(rencana)** belum diimplementasikan — lihat [Roadmap](#roadmap).*

---

## Struktur Proyek

```
nextjs_python/
├── apps/
│   ├── web/                          # Next.js
│   │   ├── app/
│   │   │   ├── layout.tsx            # nav + UserMenu
│   │   │   ├── page.tsx              # landing
│   │   │   ├── login/page.tsx
│   │   │   ├── not-found.tsx
│   │   │   ├── components/
│   │   │   │   ├── ui.tsx            # primitif design system
│   │   │   │   └── user-menu.tsx
│   │   │   ├── orders/               # daftar, new, intake, [id] + workflow.tsx
│   │   │   ├── dashboard/            # RSC + charts.tsx (Recharts) + filter dept
│   │   │   ├── simulator/page.tsx    # kirim pesan "sebagai pelanggan" (dev)
│   │   │   └── api/
│   │   │       ├── webhooks/whatsapp/route.ts   # verifikasi HMAC → FastAPI
│   │   │       └── simulator/send/route.ts      # tanda-tangani payload → webhook
│   │   ├── lib/
│   │   │   ├── api.ts                # klien REST (Bearer otomatis) + error envelope
│   │   │   ├── auth.ts               # cookie session (client)
│   │   │   └── guard.ts              # requireToken / requireRole (server)
│   │   └── middleware.ts             # verifikasi signature JWT (jose)
│   └── api/                          # FastAPI
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   │   ├── config.py         # pydantic-settings
│       │   │   ├── db.py             # engine + session async
│       │   │   ├── security.py       # JWT + Argon2
│       │   │   ├── deps.py           # get_current_user / require_role
│       │   │   ├── errors.py         # ApiError hierarchy + handler global
│       │   │   ├── logging.py        # RequestIdMiddleware + JSON logging
│       │   │   ├── ratelimit.py      # rate_limit() dependency (fixed window)
│       │   │   ├── taskqueue.py      # TaskQueue ABC: LocalTaskQueue / CloudTasksQueue
│       │   │   └── scheduler.py      # lifespan + APScheduler cron laporan harian
│       │   ├── models/               # user, product, order, job, workflow,
│       │   │                         #   processed_request, rate_counter, conversation,
│       │   │                         #   raw_message, department, report_run
│       │   ├── channels/             # MessageChannel: base, mock, whatsapp
│       │   ├── reports/              # daily.py — ringkasan → PDF (reportlab) → email
│       │   ├── schemas/              # Pydantic request/response
│       │   ├── repositories/         # query DB
│       │   ├── services/             # order, extraction, matching, workflow,
│       │   │                         #   metrics, conversation
│       │   ├── routers/              # auth, orders, products, jobs, workflow,
│       │   │                         #   metrics, internal, conversations,
│       │   │                         #   departments
│       │   ├── workers/              # ARQ: tasks, settings, queue
│       │   └── prompts/
│       ├── alembic/versions/         # migrasi
│       ├── db_lab/                   # perf lab: seed 1M rows, queries.sql, NOTES.md
│       ├── eval/                     # akurasi AI: gold.jsonl, metrics.py, run.py
│       ├── scripts/                  # seed_* + try_* (eksplorasi)
│       └── tests/
├── .github/workflows/ci.yml          # 2 job: api (ruff/mypy/pytest) · web (tsc/eslint/vitest/build)
├── docker-compose.yml                # db + redis + mailpit
└── README.md
```

---

## Menjalankan (Development)

### Prasyarat
Node 20+ · pnpm · Python 3.12 (via `uv`) · Docker · Ollama

```bash
uv python install 3.12
ollama pull gemma3:4b          # atau gemma3:1b jika RAM terbatas
```

### Setup awal (sekali)

```bash
# infrastruktur
docker compose up -d

# backend
cd apps/api
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed_products
uv run python -m scripts.seed_step_types
uv run python -m scripts.seed_users        # staff@toko.test / manajer@toko.test
uv run python -m scripts.seed_departments  # 3 dept + workflow_type + backfill
uv run python -m scripts.seed_demo         # data demo untuk dashboard

# database test
cd ../.. && docker compose exec db psql -U toko -d tokobangunan -c "CREATE DATABASE tokobangunan_test;"

# frontend
cd apps/web && pnpm install
```

### Jalankan (4 proses)

| Terminal | Perintah | Untuk |
|---|---|---|
| 1 | `docker compose up` | Postgres + Redis + Mailpit (`localhost:8025` = inbox laporan) |
| 2 | `cd apps/api && uv run uvicorn app.main:app --reload --port 8000` | API — `localhost:8000/docs` |
| 3 | `cd apps/api && uv run arq app.workers.settings.WorkerSettings` | Worker (intake + wa-message) |
| 4 | `cd apps/web && pnpm dev` | Web — `localhost:3000` |

(+ Ollama harus jalan: `brew services start ollama`.)

Laporan harian: `SCHEDULER_ENABLED=true` di `.env` mengaktifkan cron 22:00; atau picu manual —
`curl -X POST localhost:8000/internal/nightly-report?force=true -H "X-Internal-Secret: dev-internal-secret"` lalu buka `localhost:8025`.

**Login demo:** `staff@toko.test` / `staff123` · `manajer@toko.test` / `manajer123`

---

## Model Data

| Tabel | Isi ringkas |
|---|---|
| `users` | id, name, email (unik), password_hash (Argon2), role (`staff`/`manager`/`admin`) |
| `products` | id, sku, name, unit, price, stock_qty |
| `orders` | id, customer_name, status (`draft`/`confirmed`/`done`/`rejected`), intent, extraction_confidence, needs_review, created_at, completed_at |
| `order_items` | id, order_id → orders (CASCADE), product_id → products (nullable), raw_name, quantity, unit, matched_score |
| `jobs` | id (uuid), type, status, progress, result_ref, error, created_at, updated_at |
| `processed_requests` | key (Idempotency-Key), response (JSONB), created_at |
| `rate_counters` | bucket_key + window_start (PK), count — fixed-window rate limit |
| `step_types` | id, name, seq, default_sla_minutes |
| `workflow_steps` | id, order_id → orders (CASCADE), step_type_id, seq, assignee_id, assigned_at, completed_at, outcome, sla_target_minutes, **`elapsed_minutes` (generated)**; index `(assignee_id, assigned_at) WHERE completed_at IS NULL` |
| `departments`, `workflow_types` | id, name — dimensi query; `orders.department_id`/`workflow_type_id`, `users.department_id` |
| `conversations` | wa_id (PK), customer_name, active_order_id → orders, context (JSONB), last_message_at |
| `raw_messages` | id, channel, wa_id (index), direction (`in`/`out`), body, wa_message_id, created_at |
| `report_runs` | report_date (PK), sent_at, message_id — jejak laporan harian (idempotensi per tanggal) |

---

## Daftar Endpoint

| Method | Path | Auth | Keterangan |
|---|---|---|---|
| `GET` | `/health`, `/health/db` | publik | health check |
| `POST` | `/auth/login` | publik | email+password → JWT |
| `GET` | `/auth/me` | login | profil user aktif |
| `POST` | `/orders` | login | buat order manual → `201` |
| `GET` | `/orders` | login | daftar — **keyset pagination** `?limit=&after=<id>` → `{ items, next_cursor }` |
| `GET` | `/orders/{id}` | login | detail |
| `POST` | `/orders/intake` | login | teks bebas → job → `202 {job_id}` · **rate-limited** (10/mnt) |
| `POST` | `/orders/{id}/confirm` | login | `draft → confirmed`, buat langkah |
| `GET` | `/orders/{id}/steps` | login | daftar langkah workflow |
| `POST` | `/workflow-steps/{id}/complete` | login | selesaikan langkah |
| `GET` | `/products` · `/departments` | login | katalog · daftar department |
| `GET` | `/jobs/{id}` | login | status job (polling) |
| `GET` | `/conversations/{wa_id}/messages` | login | thread WhatsApp (untuk simulator) |
| `GET` | `/metrics/summary` · `/step-durations` · `/daily` · `/aging` | **manager** | agregasi dashboard; terima `?department_id=` |
| `POST` | `/internal/wa-message` | `X-Internal-Secret` | pesan WhatsApp dari route handler → enqueue |
| `POST` | `/internal/nightly-report` | `X-Internal-Secret` | build+kirim laporan harian; `?date=` `?force=` · idempoten per tanggal |
| `GET`/`POST` | `/api/webhooks/whatsapp` *(Next.js)* | HMAC | handshake Meta · terima pesan (verifikasi `X-Hub-Signature-256`) |

---

## Testing

```bash
cd apps/api && uv run pytest -q          # backend
cd apps/web && pnpm test                 # frontend (vitest)
```

- **42 test backend**: `test_orders` (termasuk keyset pagination), `test_intake`, `test_workflow`, `test_metrics`, `test_auth`, `test_ratelimit`, `test_internal`, `test_conversation`, `test_reports` (idempotensi laporan + PDF), `test_taskqueue` (LocalTaskQueue → ARQ, CloudTasksQueue = sketsa), `test_eval` (skoring metrik ekstraksi).
- **Frontend**: Vitest unit test (`lib/orders.test.ts`). Semua ini dijalankan lagi otomatis di CI (`.github/workflows/ci.yml`).
- Database test terpisah (`tokobangunan_test`), tabel dibuat sekali, di-`TRUNCATE` sebelum tiap test.
- HTTP diuji lewat `httpx.AsyncClient` + `ASGITransport` (tanpa menyalakan server).
- LLM, queue, channel, dan SMTP **di-mock** dalam test (`monkeypatch`, `AsyncMock`) — test menguji logika aplikasi, bukan AI/jaringan.
- Fixture `client` sudah "login" sebagai manager; `anon_client` untuk menguji jalur `401`.
- `ruff check` + `mypy` (BE), `tsc --noEmit` + `eslint` + `next build` (FE) semua lulus.
