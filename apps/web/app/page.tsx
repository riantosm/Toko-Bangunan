import { ButtonLink, Card, PageShell } from "@/app/components/ui";

export default function Home() {
  return (
    <PageShell>
      <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-4">
        Latihan Fullstack
      </p>
      <h1 className="text-3xl font-semibold tracking-tight text-ink">
        Toko Bangunan — AI Order Intake
      </h1>
      <p className="mt-3 max-w-xl text-ink-3">
        Terima pesanan dalam bentuk teks bebas, biarkan AI lokal menguraikannya
        menjadi order terstruktur, lalu pantau alur persetujuannya.
      </p>

      <div className="mt-6 flex gap-3">
        <ButtonLink href="/orders" variant="primary">
          Lihat Order
        </ButtonLink>
        <ButtonLink href="/orders/intake">Intake AI</ButtonLink>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-3">
        {[
          { k: "1", t: "Intake", d: "Teks pelanggan → JSON terstruktur (Gemma lokal)." },
          { k: "2", t: "Cocokkan", d: "Nama barang dipetakan ke katalog via trigram." },
          { k: "3", t: "Review", d: "Order ragu ditandai untuk dicek manusia." },
        ].map((s) => (
          <Card key={s.k} className="p-4">
            <p className="font-mono text-xs text-ink-4">0{s.k}</p>
            <p className="mt-1 font-medium text-ink">{s.t}</p>
            <p className="mt-1 text-sm text-ink-3">{s.d}</p>
          </Card>
        ))}
      </div>
    </PageShell>
  );
}
