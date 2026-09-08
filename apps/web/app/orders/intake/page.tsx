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
} from "@/app/components/ui";
import { getJob, intakeOrder } from "@/lib/api";

const EXAMPLES = [
  "pak mau 3 sak semen tiga roda sama 2 kaleng cat putih avitex",
  "pesen 20 sak semen gresik, 10 batang besi 12mm, 5 lembar triplek 9mm",
  "bang triplek 9mm ready? harganya berapa ya",
];

const STATUS_LABEL: Record<string, string> = {
  queued: "Menunggu antrean…",
  processing: "AI sedang menguraikan pesan…",
  done: "Selesai",
  error: "Gagal",
};

export default function IntakePage() {
  const router = useRouter();
  const [customer, setCustomer] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("");

  const busy = jobId !== null;

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;

    async function poll() {
      try {
        const job = await getJob(jobId!);
        if (stopped) return;
        setProgress(job.progress);
        setStatusText(STATUS_LABEL[job.status] ?? job.status);

        if (job.status === "done" && job.result_ref) {
          router.push(`/orders/${job.result_ref}`);
          return;
        }
        if (job.status === "error") {
          setError(job.error ?? "Job gagal diproses.");
          setJobId(null);
          return;
        }
        setTimeout(poll, 2000);
      } catch (e) {
        if (stopped) return;
        setError(String(e));
        setJobId(null);
      }
    }

    poll();
    return () => {
      stopped = true;
    };
  }, [jobId, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!customer.trim() || !message.trim()) {
      setError("Isi nama pelanggan dan pesan.");
      return;
    }
    try {
      const { job_id } = await intakeOrder({
        customer_name: customer.trim(),
        body: message.trim(),
      });
      setProgress(0);
      setStatusText(STATUS_LABEL.queued);
      setJobId(job_id);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <PageShell>
      <BackLink href="/orders" />
      <PageHeader eyebrow="AI" title="Intake Order" />

      <Card className="p-5">
        {busy ? (
          <div className="space-y-3 py-4">
            <p className="text-sm font-medium text-ink-2">{statusText}</p>
            <div className="h-2 w-full overflow-hidden rounded-pill bg-surface-2">
              <div
                className="h-full rounded-pill bg-accent transition-all duration-500"
                style={{ width: `${Math.max(progress, 8)}%` }}
              />
            </div>
            <p className="text-xs text-ink-4">
              Jangan tutup halaman ini — proses AI bisa 30–60 detik.
            </p>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-5">
            <p className="text-sm text-ink-3">
              Tempel pesan pelanggan apa adanya. Gemma lokal menguraikannya menjadi
              order.
            </p>

            <Field label="Nama Pelanggan">
              <input
                className={inputClass + " w-full"}
                value={customer}
                onChange={(e) => setCustomer(e.target.value)}
              />
            </Field>

            <div>
              <Field label="Pesan Pelanggan">
                <textarea
                  rows={4}
                  className={inputClass + " w-full resize-y"}
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="mau 3 sak semen…"
                />
              </Field>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {EXAMPLES.map((ex, i) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setMessage(ex)}
                    className="rounded-md border border-hair bg-[rgba(17,24,39,0.03)] px-2 py-0.5 text-xs text-ink-3 transition-colors hover:text-ink"
                  >
                    contoh {i + 1}
                  </button>
                ))}
              </div>
            </div>

            {error ? (
              <p className="whitespace-pre-wrap rounded-input bg-bad-soft p-3 text-sm text-bad">
                {error}
              </p>
            ) : null}

            <Button type="submit" variant="primary">
              Proses dengan AI
            </Button>
          </form>
        )}
      </Card>
    </PageShell>
  );
}
