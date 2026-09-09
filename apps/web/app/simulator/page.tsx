"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  BackLink,
  Button,
  Card,
  Field,
  PageHeader,
  PageShell,
  inputClass,
} from "@/app/components/ui";
import { getConversationMessages, simulatorSend, type WaMessage } from "@/lib/api";

const EXAMPLES = [
  "pak mau 3 sak semen tiga roda sama 2 kaleng cat putih avitex",
  "tambah 5 batang besi 12mm",
  "konfirmasi",
];

export default function SimulatorPage() {
  const [waId, setWaId] = useState("6281234567890");
  const [name, setName] = useState("Pak Budi");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<WaMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const threadRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      const rows = await getConversationMessages(waId);
      setMessages(rows);
      setWaiting((w) => (w && rows.at(-1)?.direction === "out" ? false : w));
    } catch {
      /* ignore transient */
    }
  }, [waId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 2000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages]);

  async function send() {
    if (!message.trim() || !waId.trim()) return;
    setSending(true);
    setError(null);
    try {
      await simulatorSend({ wa_id: waId.trim(), name: name.trim(), body: message.trim() });
      setMessage("");
      setWaiting(true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <PageShell>
      <BackLink href="/orders" />
      <PageHeader
        eyebrow="Dev tool"
        title="Simulator WhatsApp"
        action={
          <span className="text-xs text-ink-4">
            payload palsu → webhook (HMAC) → worker
          </span>
        }
      />

      <div className="grid gap-4 md:grid-cols-[1fr_1.2fr]">
        <Card className="space-y-4 p-4">
          <div className="grid grid-cols-2 gap-2">
            <Field label="Nama">
              <input
                className={inputClass + " w-full"}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </Field>
            <Field label="Nomor (wa_id)">
              <input
                className={inputClass + " w-full"}
                value={waId}
                onChange={(e) => setWaId(e.target.value)}
              />
            </Field>
          </div>
          <Field label="Pesan pelanggan">
            <textarea
              rows={3}
              className={inputClass + " w-full resize-y"}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="mau 3 sak semen…"
            />
          </Field>
          <div className="flex flex-wrap gap-1.5">
            {EXAMPLES.map((ex, i) => (
              <button
                key={ex}
                type="button"
                onClick={() => setMessage(ex)}
                className="rounded-md border border-hair bg-[rgba(17,24,39,0.03)] px-2 py-0.5 text-xs text-ink-3 hover:text-ink"
              >
                contoh {i + 1}
              </button>
            ))}
          </div>
          {error ? (
            <p className="rounded-input bg-bad-soft p-2.5 text-sm text-bad">{error}</p>
          ) : null}
          <Button variant="primary" onClick={send} disabled={sending}>
            {sending ? "Mengirim…" : "Kirim sebagai pelanggan"}
          </Button>
        </Card>

        <Card className="flex h-[28rem] flex-col p-0">
          <div ref={threadRef} className="flex-1 space-y-2 overflow-y-auto p-4">
            {messages.length === 0 ? (
              <p className="pt-8 text-center text-sm text-ink-4">
                Belum ada pesan untuk nomor ini.
              </p>
            ) : null}
            {messages.map((m) => (
              <div
                key={m.id}
                className={
                  m.direction === "in" ? "flex justify-end" : "flex justify-start"
                }
              >
                <div
                  className={
                    "max-w-[80%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm " +
                    (m.direction === "in"
                      ? "bg-accent text-accent-ink"
                      : "border border-hair bg-surface-2 text-ink")
                  }
                >
                  {m.body}
                </div>
              </div>
            ))}
            {waiting ? (
              <div className="flex justify-start">
                <div className="rounded-2xl border border-hair bg-surface-2 px-3 py-2 text-sm text-ink-4">
                  AI sedang memproses… (~30 dtk)
                </div>
              </div>
            ) : null}
          </div>
        </Card>
      </div>
    </PageShell>
  );
}
