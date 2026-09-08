import { ButtonLink, PageShell } from "@/app/components/ui";

export default function NotFound() {
  return (
    <PageShell>
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-4">404</p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
        Halaman tidak ditemukan
      </h1>
      <p className="mt-2 text-ink-3">Tautan mungkin salah, atau datanya sudah dihapus.</p>
      <ButtonLink href="/orders" variant="primary" className="mt-5">
        Ke daftar order
      </ButtonLink>
    </PageShell>
  );
}
