"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import {
  BackLink,
  Button,
  Card,
  Field,
  PageHeader,
  PageShell,
  inputClass,
  selectClass,
} from "@/app/components/ui";
import { createOrder, getProducts, type Product } from "@/lib/api";

type Row = { product_id: number; quantity: number };

export default function NewOrderPage() {
  const router = useRouter();
  const [products, setProducts] = useState<Product[]>([]);
  const [customer, setCustomer] = useState("");
  const [rows, setRows] = useState<Row[]>([{ product_id: 0, quantity: 1 }]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch((e) => setError(String(e)));
  }, []);

  function updateRow(i: number, patch: Partial<Row>) {
    setRows((r) => r.map((row, idx) => (idx === i ? { ...row, ...patch } : row)));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const items = rows.filter((r) => r.product_id > 0 && r.quantity > 0);
    if (!customer.trim() || items.length === 0) {
      setError("Isi nama pelanggan dan minimal 1 item.");
      return;
    }
    setSaving(true);
    try {
      const order = await createOrder({ customer_name: customer.trim(), items });
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(String(err));
      setSaving(false);
    }
  }

  return (
    <PageShell>
      <BackLink href="/orders" />
      <PageHeader eyebrow="Manual" title="Buat Order" />

      <Card className="p-5">
        <form onSubmit={submit} className="space-y-5">
          <Field label="Nama Pelanggan">
            <input
              className={inputClass + " w-full"}
              value={customer}
              onChange={(e) => setCustomer(e.target.value)}
            />
          </Field>

          <div className="space-y-2">
            <span className="block text-sm font-medium text-ink-2">Item</span>
            {rows.map((row, i) => (
              <div key={i} className="flex gap-2">
                <select
                  className={selectClass + " min-w-0 flex-1"}
                  value={row.product_id}
                  onChange={(e) =>
                    updateRow(i, { product_id: Number(e.target.value) })
                  }
                >
                  <option value={0}>— pilih produk —</option>
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.unit})
                    </option>
                  ))}
                </select>
                <input
                  type="number"
                  min={1}
                  aria-label="Jumlah"
                  className={inputClass + " w-20 shrink-0"}
                  value={row.quantity}
                  onChange={(e) =>
                    updateRow(i, { quantity: Number(e.target.value) })
                  }
                />
                {rows.length > 1 ? (
                  <Button
                    type="button"
                    onClick={() =>
                      setRows((r) => r.filter((_, idx) => idx !== i))
                    }
                    className="shrink-0 px-3"
                  >
                    &times;
                  </Button>
                ) : null}
              </div>
            ))}
            <button
              type="button"
              onClick={() => setRows((r) => [...r, { product_id: 0, quantity: 1 }])}
              className="text-sm font-medium text-accent hover:underline"
            >
              + tambah item
            </button>
          </div>

          {error ? (
            <p className="whitespace-pre-wrap rounded-input bg-bad-soft p-3 text-sm text-bad">
              {error}
            </p>
          ) : null}

          <Button type="submit" variant="primary" disabled={saving}>
            {saving ? "Menyimpan…" : "Simpan Order"}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
