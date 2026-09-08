"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { Badge, Td } from "@/app/components/ui";
import type { OrderListRow } from "@/lib/api";

export function OrderRow({
  order,
  createdLabel,
}: {
  order: OrderListRow;
  createdLabel: string;
}) {
  const router = useRouter();
  const href = `/orders/${order.id}`;

  return (
    <tr
      onClick={() => router.push(href)}
      className="cursor-pointer transition-colors hover:bg-[rgba(17,24,39,0.03)]"
    >
      <Td>
        <Link
          href={href}
          onClick={(e) => e.stopPropagation()}
          className="text-ink hover:text-accent"
        >
          #{order.id}
        </Link>
      </Td>
      <Td>
        <span className="flex items-center gap-2">
          {order.customer_name}
          {order.needs_review ? <Badge tone="warn">perlu review</Badge> : null}
        </span>
      </Td>
      <Td>{order.status}</Td>
      <Td>{order.item_count}</Td>
      <Td className="text-ink-3">{createdLabel}</Td>
    </tr>
  );
}
