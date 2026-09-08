"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { clearSession, readCookie } from "@/lib/auth";

export function UserMenu() {
  const router = useRouter();
  const [info, setInfo] = useState<{ name: string; role: string } | null>(null);

  // read after mount to avoid hydration mismatch (server can't see the cookie value)
  useEffect(() => {
    const name = readCookie("name");
    const role = readCookie("role");
    if (name && role) setInfo({ name, role });
  }, []);

  if (!info) return null;

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="hidden text-ink-4 sm:inline">
        {info.name} · {info.role}
      </span>
      <button
        type="button"
        onClick={() => {
          clearSession();
          router.replace("/login");
          router.refresh();
        }}
        className="text-ink-3 transition-colors hover:text-ink"
      >
        Keluar
      </button>
    </div>
  );
}
