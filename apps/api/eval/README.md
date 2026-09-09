# Evaluasi Akurasi Ekstraksi AI

Mengukur kualitas `extract_order()` (LLM lokal → JSON order) supaya perubahan
prompt / model bisa dibandingkan dengan **angka**, bukan perasaan.

## Isi

| File | Fungsi |
|---|---|
| `gold.jsonl` | 30 contoh pesan + anotasi manual (`expected`) — bahasa Indonesia informal, typo, sinonim satuan, kata bilangan |
| `metrics.py` | skoring murni (tanpa panggil model) — `score_example`, `aggregate` |
| `run.py` | jalankan model ke semua contoh, cetak tabel, simpan `results/<timestamp>.json` |
| `results/` | hasil tiap run (di-*gitignore* kecuali `.gitkeep`) |

## Menjalankan

```bash
uv run python -m eval.run                  # seluruh gold set (~8 mnt di gemma3:4b)
uv run python -m eval.run --limit 5         # smoke test cepat
uv run python -m eval.run --model gemma3:1b # A/B model lain
```

Butuh Ollama menyala + model ter-*pull*.

## Metrik

| Metrik | Arti |
|---|---|
| **JSON validity rate** | % balasan yang lolos skema Pydantic (setelah maks. 2 percobaan) |
| **intent accuracy / macro-F1** | ketepatan klasifikasi `order` / `inquiry` / `complaint` |
| **intent P/R/F1 per kelas** | precision–recall–F1 tiap intent (support = jumlah di gold) |
| **order exact match** | seluruh ekstraksi (intent + semua item persis) benar |
| **item P/R/F1** | item dianggap benar bila nama cocok (SequenceMatcher ≥ 0.6) **dan** unit **dan** quantity benar |
| **unit / qty accuracy** | ketepatan field pada pasangan item yang ter-*align* |
| **qty MAE** | rata-rata selisih mutlak quantity |
| **hallucination rate** | item hasil model yang tidak ada padanannya di gold ÷ total item model |

## Regression testing prompt

1. Catat skor sekarang (`results/<timestamp>.json` menyimpan `prompt_hash`).
2. Ubah `app/prompts/extract_order.txt`.
3. Jalankan `eval.run` lagi → bandingkan `aggregate` dua file.
4. `prompt_hash` berubah → jelas versi mana yang menghasilkan skor mana.
