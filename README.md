# Toko Bangunan — AI Order Intake & SLA Dashboard

Aplikasi web fullstack: sebuah toko bangunan menerima pesanan dalam bentuk
**teks bebas** (seperti chat WhatsApp), sebuah **LLM lokal** menguraikannya menjadi
order terstruktur, order berjalan lewat **workflow persetujuan berjenjang** dengan
pencatatan durasi, dan manajemen memantau **dashboard SLA**.

- **`apps/web`** — frontend Next.js 16 (App Router, React 19, Tailwind v4)
- **`apps/api`** — backend FastAPI (Python 3.12, async SQLAlchemy 2.0)

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
9. [Roadmap](#roadmap)

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
  - **`middleware.ts`** — cek keberadaan cookie (coarse check); verifikasi asli tetap di FastAPI.
  - Server Component gate via `requireToken()` / `requireRole()`; tombol **Keluar** di nav.

### Fondasi lintas fitur
- **Desain sistem** (`apps/web/app/globals.css` + `apps/web/app/components/ui.tsx`): tema **light**, token Tailwind v4 `@theme`, hairline border, satu aksen violet, primitif bersama (`Card`, `Button`, `Badge`, `Table`, `Field`, …).
- **Migrasi** semua lewat Alembic (autogenerate + edit manual untuk `pg_trgm` & generated column).
- **Git**: commit kecil, *Conventional Commits* (`feat:`, `fix:`, `test:`, `chore:`).
- **Docker Compose** untuk infrastruktur (Postgres, Redis); app dijalankan langsung di host saat dev.

---

## Arsitektur

```
                       ┌───────────────────────────┐
   Staff / Manajer     │   Next.js 16 (App Router)  │
   ───────────────────>│   - /login (JWT → cookie) │
                       │   - /orders, /dashboard    │  Server Components
                       │   - middleware guard       │  ambil data di server
                       └────────────┬──────────────┘
                                    │ HTTPS REST  (Authorization: Bearer <jwt>)
                                    v
                       ┌───────────────────────────┐
                       │   FastAPI (Python, async) │
                       │   - /auth  /orders        │
                       │   - /workflow  /metrics   │
                       │   - get_current_user dep  │
                       └───┬───────────┬──────────┬┘
        enqueue job        │           │          │  async SQLAlchemy
                           v           │          v
                 ┌──────────────┐      │   ┌──────────────┐
                 │ Worker (ARQ) │──────┼──>│ PostgreSQL 16│
                 │ - LLM parse  │      │   │ + pg_trgm    │
                 │ - match prod │      │   │ + generated  │
                 └──────┬───────┘      │   │   column     │
                        │ HTTP         │   └──────────────┘
                        v              │
                 ┌──────────────┐   ┌──┴───────────┐
                 │ Ollama       │   │ Redis        │
                 │ gemma3:4b/1b │   │ (broker ARQ) │
                 └──────────────┘   └──────────────┘
```

**Protokol antar komponen**

| Dari | Ke | Cara |
|---|---|---|
| Browser | Next.js | HTTPS; data diambil di Server Component |
| Next.js | FastAPI | HTTPS REST, header `Authorization: Bearer <jwt>` |
| FastAPI | PostgreSQL | connection pool async (`asyncpg`) |
| FastAPI | Worker | enqueue job lewat Redis (ARQ) |
| Worker | Ollama | HTTP `localhost:11434` (`/api/chat`, JSON mode) |
| Worker | PostgreSQL | session async terpisah (bukan konteks request) |

---

## Tech Stack

| Layer | Teknologi |
|---|---|
| Frontend | Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 (`@theme`) · Recharts |
| Backend | FastAPI · Python 3.12 · Pydantic v2 · pydantic-settings |
| ORM / Migrasi | SQLAlchemy 2.0 (async) · Alembic |
| Database | PostgreSQL 16 (+ ekstensi `pg_trgm`, generated column) |
| Queue / Worker | ARQ · Redis 7 |
| LLM lokal | Ollama · Gemma 3 (`gemma3:4b` atau `gemma3:1b`) |
| Auth | PyJWT (HS256) · Argon2 (`argon2-cffi`) |
| Testing | pytest · pytest-asyncio · httpx (`ASGITransport`) |
| Kualitas | Ruff · mypy · ESLint · TypeScript strict |
| Infrastruktur | Docker Compose |
| Package manager | `uv` (Python) · `pnpm` (JS) |

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
│   │   │   ├── orders/
│   │   │   │   ├── page.tsx          # daftar (RSC)
│   │   │   │   ├── order-row.tsx     # baris klik-penuh (client)
│   │   │   │   ├── new/page.tsx      # form manual (client)
│   │   │   │   ├── intake/page.tsx   # form AI + progress (client)
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx      # detail (RSC)
│   │   │   │       └── workflow.tsx  # alur persetujuan (client)
│   │   │   └── dashboard/
│   │   │       ├── page.tsx          # RSC
│   │   │       └── charts.tsx        # Recharts (client)
│   │   ├── lib/
│   │   │   ├── api.ts                # klien REST (Bearer otomatis)
│   │   │   ├── auth.ts               # cookie session (client)
│   │   │   └── guard.ts              # requireToken / requireRole (server)
│   │   └── middleware.ts             # coarse auth guard
│   └── api/                          # FastAPI
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   │   ├── config.py         # pydantic-settings
│       │   │   ├── db.py             # engine + session async
│       │   │   ├── security.py       # JWT + Argon2
│       │   │   └── deps.py           # get_current_user / require_role
│       │   ├── models/               # SQLAlchemy: user, product, order,
│       │   │                         #   job, processed_request, workflow
│       │   ├── schemas/              # Pydantic request/response
│       │   ├── repositories/         # query DB
│       │   ├── services/             # order, extraction, matching,
│       │   │                         #   workflow, metrics
│       │   ├── routers/              # auth, orders, products, jobs,
│       │   │                         #   workflow, metrics
│       │   ├── workers/              # ARQ: tasks, settings, queue
│       │   └── prompts/
│       ├── alembic/versions/         # migrasi
│       ├── scripts/                  # seed_* + try_* (eksplorasi)
│       └── tests/
├── docker-compose.yml                # db + redis
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
uv run python -m scripts.seed_demo         # data demo untuk dashboard

# database test
cd ../.. && docker compose exec db psql -U toko -d tokobangunan -c "CREATE DATABASE tokobangunan_test;"

# frontend
cd apps/web && pnpm install
```

### Jalankan (4 proses)

| Terminal | Perintah | Untuk |
|---|---|---|
| 1 | `docker compose up` | Postgres + Redis |
| 2 | `cd apps/api && uv run uvicorn app.main:app --reload --port 8000` | API — `localhost:8000/docs` |
| 3 | `cd apps/api && uv run arq app.workers.settings.WorkerSettings` | Worker (job intake) |
| 4 | `cd apps/web && pnpm dev` | Web — `localhost:3000` |

(+ Ollama harus jalan: `brew services start ollama`.)

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
| `step_types` | id, name, seq, default_sla_minutes |
| `workflow_steps` | id, order_id → orders (CASCADE), step_type_id, seq, assignee_id, assigned_at, completed_at, outcome, sla_target_minutes, **`elapsed_minutes` (generated)** |

---

## Daftar Endpoint

| Method | Path | Auth | Keterangan |
|---|---|---|---|
| `GET` | `/health`, `/health/db` | publik | health check |
| `POST` | `/auth/login` | publik | email+password → JWT |
| `GET` | `/auth/me` | login | profil user aktif |
| `POST` | `/orders` | login | buat order manual → `201` |
| `GET` | `/orders` | login | daftar berpaginasi |
| `GET` | `/orders/{id}` | login | detail |
| `POST` | `/orders/intake` | login | teks bebas → job → `202 {job_id}` |
| `POST` | `/orders/{id}/confirm` | login | `draft → confirmed`, buat langkah |
| `GET` | `/orders/{id}/steps` | login | daftar langkah workflow |
| `POST` | `/workflow-steps/{id}/complete` | login | selesaikan langkah |
| `GET` | `/products` | login | katalog produk |
| `GET` | `/jobs/{id}` | login | status job (polling) |
| `GET` | `/metrics/summary` · `/step-durations` · `/daily` · `/aging` | **manager** | agregasi dashboard |

---

## Testing

```bash
cd apps/api && uv run pytest -q
```

- **22 test**: `test_orders`, `test_intake`, `test_workflow`, `test_metrics`, `test_auth`.
- Database test terpisah (`tokobangunan_test`), tabel dibuat sekali, di-`TRUNCATE` sebelum tiap test.
- HTTP diuji lewat `httpx.AsyncClient` + `ASGITransport` (tanpa menyalakan server).
- LLM & queue **di-mock** dalam test (`monkeypatch`, `AsyncMock`) — test menguji logika aplikasi, bukan AI.
- Fixture `client` sudah "login" sebagai manager; `anon_client` untuk menguji jalur `401`.

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
| 7 | API hardening — rate limiting + error envelope + requestId | ⬜ |
| 8 | Laporan harian terjadwal (APScheduler → email) | ⬜ |
| 9 | PostgreSQL performance lab — `EXPLAIN (ANALYZE, BUFFERS)`, index, partisi, CTE | ⬜ |
| 10 | CI (GitHub Actions — lint + test) | ⬜ |
| 11 | Evaluasi akurasi AI (gold set, metrik F1) | ⬜ |
| 12 | Deploy cloud (Vercel + Cloud Run) | ⬜ |
