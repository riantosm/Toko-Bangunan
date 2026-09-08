import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <h1 className="text-2xl font-bold">Toko Bangunan</h1>
      <p className="mt-2 text-gray-600">Aplikasi latihan order intake.</p>
      <Link
        href="/orders"
        className="mt-4 inline-block rounded bg-black px-4 py-2 text-sm text-white"
      >
        Lihat Order
      </Link>
    </main>
  );
}
