import Link from "next/link";

import { getOrders } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OrdersPage() {
  const data = await getOrders();

  return (
    <main className="mx-auto max-w-3xl p-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Order ({data.total})</h1>
        <Link
          href="/orders/new"
          className="rounded bg-black px-3 py-1.5 text-sm text-white"
        >
          + Buat Order
        </Link>
      </div>

      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2">ID</th>
            <th>Pelanggan</th>
            <th>Status</th>
            <th>Item</th>
            <th>Dibuat</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((o) => (
            <tr key={o.id} className="border-b">
              <td className="py-2">
                <Link href={`/orders/${o.id}`} className="text-blue-600 underline">
                  {o.id}
                </Link>
              </td>
              <td>{o.customer_name}</td>
              <td>{o.status}</td>
              <td>{o.item_count}</td>
              <td>{new Date(o.created_at).toLocaleString("id-ID")}</td>
            </tr>
          ))}
          {data.items.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 text-center text-gray-400">
                Belum ada order
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </main>
  );
}
