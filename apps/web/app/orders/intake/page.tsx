"use client";

import { useState } from "react";
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
import { intakeOrder } from "@/lib/api";

const EXAMPLES = [
  "pak mau 3 sak semen tiga roda sama 2 kaleng cat putih avitex",
  "pesen 20 sak semen gresik, 10 batang besi 12mm, 5 lembar triplek 9mm",
  "bang triplek 9mm ready? harganya berapa ya",
];

export default function IntakePage() {
  const router = useRouter();
  const [customer, setCustomer] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!customer.trim() || !message.trim()) {
      setError("Isi nama pelanggan dan pesan.");
      return;
    }
    setLoading(true);
    try {
      const order = await intakeOrder({
        customer_name: customer.trim(),
        body: message.trim(),
      });
      router.push(`/orders/${order.id}`);
    } catch (err) {
      setError(String(err));
      setLoading(false);
    }
  }

  return (
    <PageShell>
      <BackLink href="/orders" />
      <PageHeader eyebrow="AI" title="Intake Order" />

      <Card className="p-5">
        <p className="mb-5 text-sm text-ink-3">
          Tempel pesan pelanggan apa adanya. Gemma lokal menguraikannya menjadi
          order. Proses bisa memakan beberapa detik.
        </p>

        <form onSubmit={submit} className="space-y-5">
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

          <Button type="submit" variant="primary" disabled={loading}>
            {loading ? "Memproses (AI)…" : "Proses dengan AI"}
          </Button>
        </form>
      </Card>
    </PageShell>
  );
}
