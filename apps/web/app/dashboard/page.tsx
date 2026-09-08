import {
  Badge,
  ButtonLink,
  Card,
  PageHeader,
  PageShell,
  Table,
  Td,
  Th,
} from "@/app/components/ui";
import {
  getAging,
  getDaily,
  getStepDurations,
  getSummary,
} from "@/lib/api";
import { requireRole } from "@/lib/guard";

import { SlaTrendChart, StepDurationChart } from "./charts";

export const dynamic = "force-dynamic";

const PRESETS = [7, 30, 90];

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string }>;
}) {
  const token = await requireRole("manager", "admin");
  const { days: daysParam } = await searchParams;
  const days = PRESETS.includes(Number(daysParam)) ? Number(daysParam) : 30;

  const [summary, steps, daily, aging] = await Promise.all([
    getSummary(days, token),
    getStepDurations(days, token),
    getDaily(days, token),
    getAging(token),
  ]);

  return (
    <PageShell>
      <PageHeader
        eyebrow="Analytics"
        title="Dashboard SLA"
        action={
          <div className="flex gap-1.5">
            {PRESETS.map((d) => (
              <ButtonLink
                key={d}
                href={`/dashboard?days=${d}`}
                variant={d === days ? "primary" : "ghost"}
              >
                {d}h
              </ButtonLink>
            ))}
          </div>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Kpi label="Order masuk" value={summary.orders_total} />
        <Kpi label="Selesai" value={summary.orders_done} />
        <Kpi label="Berjalan (WIP)" value={summary.wip} />
        <Kpi
          label="SLA terpenuhi"
          value={summary.sla_met_pct != null ? `${summary.sla_met_pct}%` : "—"}
        />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card className="p-4">
          <h2 className="mb-3 text-sm font-medium text-ink">
            Durasi per langkah (menit) — rata-rata &amp; p90
          </h2>
          <StepDurationChart data={steps} />
        </Card>
        <Card className="p-4">
          <h2 className="mb-3 text-sm font-medium text-ink">
            Tren SLA terpenuhi (%) per hari
          </h2>
          <SlaTrendChart data={daily} />
        </Card>
      </div>

      <h2 className="mt-8 mb-3 text-xs font-medium uppercase tracking-wide text-ink-4">
        Order menunggu terlama
      </h2>
      <Table>
        <thead>
          <tr>
            <Th>Order</Th>
            <Th>Pelanggan</Th>
            <Th>Langkah aktif</Th>
            <Th>Menunggu</Th>
          </tr>
        </thead>
        <tbody>
          {aging.map((r) => {
            const over = Number(r.waiting_minutes) > r.sla_target_minutes;
            return (
              <tr key={r.order_id}>
                <Td>#{r.order_id}</Td>
                <Td>{r.customer_name}</Td>
                <Td>{r.current_step}</Td>
                <Td>
                  <span className="flex items-center gap-2">
                    <span className={over ? "text-bad" : ""}>
                      {r.waiting_minutes} mnt
                    </span>
                    {over ? <Badge tone="bad">lewat SLA</Badge> : null}
                  </span>
                </Td>
              </tr>
            );
          })}
          {aging.length === 0 ? (
            <tr>
              <Td>—</Td>
              <Td>tidak ada order menunggu</Td>
              <Td>—</Td>
              <Td>—</Td>
            </tr>
          ) : null}
        </tbody>
      </Table>
    </PageShell>
  );
}

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-card border border-hair bg-surface p-4">
      <p className="text-xs uppercase tracking-wide text-ink-4">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">{value}</p>
    </div>
  );
}
