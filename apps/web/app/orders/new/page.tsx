"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

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
    <main className="mx-auto max-w-xl p-6">
      <h1 className="mb-4 text-xl font-semibold">Buat Order</h1>
      <form onSubmit={submit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium">Nama Pelanggan</label>
          <input
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium">Item</label>
          {rows.map((row, i) => (
            <div key={i} className="flex gap-2">
              <select
                className="flex-1 rounded border px-2 py-2 text-sm"
                value={row.product_id}
                onChange={(e) =>
                  updateRow(i, { product_id: Number(e.target.value) })
                }
              >
                <option value={0}>-- pilih produk --</option>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.unit})
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                className="w-24 rounded border px-2 py-2 text-sm"
                value={row.quantity}
                onChange={(e) =>
                  updateRow(i, { quantity: Number(e.target.value) })
                }
              />
              {rows.length > 1 && (
                <button
                  type="button"
                  onClick={() => setRows((r) => r.filter((_, idx) => idx !== i))}
                  className="rounded border px-2 text-sm"
                >
                  &times;
                </button>
              )}
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setRows((r) => [...r, { product_id: 0, quantity: 1 }])
            }
            className="text-sm text-blue-600 underline"
          >
            + tambah item
          </button>
        </div>

        {error && (
          <p className="whitespace-pre-wrap rounded bg-red-50 p-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {saving ? "Menyimpan..." : "Simpan Order"}
        </button>
      </form>
    </main>
  );
}
