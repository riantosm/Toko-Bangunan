import Link from "next/link";
import { notFound } from "next/navigation";

import { getOrder } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const order = await getOrder(id);
  if (!order) notFound();

  return (
    <main className="mx-auto max-w-3xl p-6">
      <Link href="/orders" className="text-sm text-blue-600 underline">
        &larr; kembali
      </Link>
      <h1 className="mt-2 text-xl font-semibold">Order #{order.id}</h1>
      <p className="text-gray-600">
        {order.customer_name} &middot; {order.status} &middot;{" "}
        {new Date(order.created_at).toLocaleString("id-ID")}
      </p>

      <table className="mt-4 w-full border-collapse text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500">
            <th className="py-2">Produk (ID)</th>
            <th>Jumlah</th>
            <th>Satuan</th>
          </tr>
        </thead>
        <tbody>
          {order.items.map((it) => (
            <tr key={it.id} className="border-b">
              <td className="py-2">{it.product_id}</td>
              <td>{it.quantity}</td>
              <td>{it.unit}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
