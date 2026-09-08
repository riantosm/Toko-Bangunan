import { notFound } from "next/navigation";

import {
  BackLink,
  Badge,
  Card,
  PageShell,
  Table,
  Td,
  Th,
} from "@/app/components/ui";
import { getOrder } from "@/lib/api";

import { OrderWorkflow } from "./workflow";

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
    <PageShell>
      <BackLink href="/orders" />

      <div className="mb-6 flex items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">
          Order #{order.id}
        </h1>
        {order.needs_review ? <Badge tone="warn">perlu review</Badge> : null}
      </div>

      <Card className="mb-6 grid gap-3 p-5 sm:grid-cols-3">
        <Meta label="Pelanggan" value={order.customer_name} />
        <Meta label="Status" value={order.status} />
        <Meta
          label="Dibuat"
          value={new Date(order.created_at).toLocaleString("id-ID")}
        />
        {order.intent ? (
          <Meta label="Intent (AI)" value={order.intent} />
        ) : null}
        {order.extraction_confidence != null ? (
          <Meta
            label="Confidence (AI)"
            value={`${Math.round(order.extraction_confidence * 100)}%`}
          />
        ) : null}
      </Card>

      <Table>
        <thead>
          <tr>
            <Th>Produk</Th>
            <Th>Teks asli</Th>
            <Th>Jumlah</Th>
            <Th>Satuan</Th>
            <Th>Skor</Th>
          </tr>
        </thead>
        <tbody>
          {order.items.map((it) => (
            <tr key={it.id}>
              <Td>
                {it.product_id != null ? (
                  `#${it.product_id}`
                ) : (
                  <Badge tone="bad">tak dikenal</Badge>
                )}
              </Td>
              <Td className="text-ink-3">{it.raw_name ?? "—"}</Td>
              <Td>{it.quantity}</Td>
              <Td>{it.unit}</Td>
              <Td className="text-ink-3">
                {it.matched_score != null ? it.matched_score.toFixed(2) : "—"}
              </Td>
            </tr>
          ))}
        </tbody>
      </Table>

      <OrderWorkflow orderId={order.id} status={order.status} />
    </PageShell>
  );
}

function Meta({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-ink-4">{label}</p>
      <p className="mt-0.5 text-ink">{value}</p>
    </div>
  );
}
