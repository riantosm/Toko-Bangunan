"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Button, Card, Field, PageShell, inputClass } from "@/app/components/ui";
import { login } from "@/lib/api";
import { setSession } from "@/lib/auth";

function LoginForm() {
  const router = useRouter();
  const next = useSearchParams().get("next") || "/orders";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const s = await login(email.trim(), password);
      setSession(s);
      router.replace(next);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    }
  }

  return (
    <Card className="mx-auto mt-10 max-w-sm p-6">
      <h1 className="text-lg font-semibold text-ink">Masuk</h1>
      <p className="mt-1 mb-5 text-sm text-ink-3">Toko Bangunan — panel internal</p>

      <form onSubmit={submit} className="space-y-4">
        <Field label="Email">
          <input
            type="email"
            autoComplete="username"
            className={inputClass + " w-full"}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </Field>
        <Field label="Password">
          <input
            type="password"
            autoComplete="current-password"
            className={inputClass + " w-full"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </Field>

        {error ? (
          <p className="rounded-input bg-bad-soft p-2.5 text-sm text-bad">{error}</p>
        ) : null}

        <Button type="submit" variant="primary" disabled={busy} className="w-full">
          {busy ? "Memproses…" : "Masuk"}
        </Button>
      </form>

      <p className="mt-4 text-xs text-ink-4">
        Demo: <code>staff@toko.test / staff123</code> ·{" "}
        <code>manajer@toko.test / manajer123</code>
      </p>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <PageShell>
      <Suspense>
        <LoginForm />
      </Suspense>
    </PageShell>
  );
}
