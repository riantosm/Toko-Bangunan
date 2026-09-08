import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Toko Bangunan",
  description: "AI order intake & SLA dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="border-b border-hair">
          <div className="mx-auto flex w-full max-w-3xl items-center justify-between px-5 py-3">
            <Link href="/" className="text-sm font-semibold tracking-tight text-ink">
              Toko&nbsp;Bangunan
            </Link>
            <nav className="flex gap-5 text-sm text-ink-3">
              <Link href="/orders" className="transition-colors hover:text-ink">
                Order
              </Link>
            </nav>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
