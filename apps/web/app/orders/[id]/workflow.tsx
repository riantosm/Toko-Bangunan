"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Badge, Button } from "@/app/components/ui";
import {
  completeStep,
  confirmOrder,
  getSteps,
  type WorkflowStep,
} from "@/lib/api";

export function OrderWorkflow({
  orderId,
  status,
}: {
  orderId: number;
  status: string;
}) {
  const router = useRouter();
  const [steps, setSteps] = useState<WorkflowStep[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setSteps(await getSteps(orderId));
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => {
    if (status !== "draft") load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId, status]);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      await load();
      router.refresh();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  if (status === "draft") {
    return (
      <div className="mt-8">
        <Button
          variant="primary"
          disabled={busy}
          onClick={() => run(() => confirmOrder(orderId))}
        >
          {busy ? "Memproses…" : "Konfirmasi Order"}
        </Button>
        {error ? <p className="mt-2 text-sm text-bad">{error}</p> : null}
      </div>
    );
  }

  return (
    <section className="mt-8">
      <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-ink-4">
        Alur Persetujuan
      </h2>
      {error ? <p className="mb-3 text-sm text-bad">{error}</p> : null}
      <ol className="space-y-2">
        {(steps ?? []).map((s) => {
          const state = s.completed_at
            ? "done"
            : s.assigned_at
              ? "active"
              : "pending";
          const breached =
            s.elapsed_minutes != null &&
            s.elapsed_minutes > s.sla_target_minutes;

          return (
            <li
              key={s.id}
              className="flex items-center justify-between gap-3 rounded-card border border-hair bg-surface p-4"
            >
              <div>
                <p className="font-medium text-ink">
                  {s.seq}. {s.step_type_name}
                </p>
                <p className="mt-0.5 text-xs text-ink-4">
                  {state === "done"
                    ? `selesai · ${s.elapsed_minutes ?? "?"} mnt / target ${s.sla_target_minutes} mnt`
                    : state === "active"
                      ? `menunggu tindakan · target ${s.sla_target_minutes} mnt`
                      : "belum aktif"}
                  {breached ? " · ⚠ lewat SLA" : ""}
                </p>
              </div>

              {state === "done" ? (
                <Badge tone={s.outcome === "rejected" ? "bad" : "good"}>
                  {s.outcome}
                </Badge>
              ) : state === "active" ? (
                <div className="flex shrink-0 gap-2">
                  <Button
                    variant="primary"
                    disabled={busy}
                    onClick={() => run(() => completeStep(s.id, "approved"))}
                  >
                    Setujui
                  </Button>
                  <Button
                    disabled={busy}
                    onClick={() => run(() => completeStep(s.id, "rejected"))}
                  >
                    Tolak
                  </Button>
                </div>
              ) : (
                <Badge tone="muted">menunggu</Badge>
              )}
            </li>
          );
        })}
      </ol>
    </section>
  );
}
