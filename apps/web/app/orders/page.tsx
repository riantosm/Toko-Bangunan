import {
  ButtonLink,
  EmptyRow,
  PageHeader,
  PageShell,
  Table,
  Th,
} from "@/app/components/ui";
import { getOrders } from "@/lib/api";
import { requireToken } from "@/lib/guard";
import { parseCursor } from "@/lib/orders";

import { OrderRow } from "./order-row";

export const dynamic = "force-dynamic";

export default async function OrdersPage({
  searchParams,
}: {
  searchParams: Promise<{ after?: string }>;
}) {
  const token = await requireToken();
  const { after: afterParam } = await searchParams;
  const after = parseCursor(afterParam);
  const data = await getOrders(after, token);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Daftar"
        title="Order"
        action={
          <div className="flex gap-2">
            <ButtonLink href="/orders/intake" variant="primary">
              Intake AI
            </ButtonLink>
            <ButtonLink href="/orders/new">+ Manual</ButtonLink>
          </div>
        }
      />

      <Table>
        <thead>
          <tr>
            <Th>ID</Th>
            <Th>Pelanggan</Th>
            <Th>Status</Th>
            <Th>Item</Th>
            <Th>Dibuat</Th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((o) => (
            <OrderRow
              key={o.id}
              order={o}
              createdLabel={new Date(o.created_at).toLocaleString("id-ID")}
            />
          ))}
          {data.items.length === 0 ? (
            <EmptyRow colSpan={5}>Belum ada order</EmptyRow>
          ) : null}
        </tbody>
      </Table>

      <div className="mt-4 flex gap-2">
        {after ? <ButtonLink href="/orders">← Awal</ButtonLink> : null}
        {data.next_cursor ? (
          <ButtonLink href={`/orders?after=${data.next_cursor}`}>
            Muat lebih banyak →
          </ButtonLink>
        ) : null}
      </div>
    </PageShell>
  );
}
