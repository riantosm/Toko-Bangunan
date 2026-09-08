import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

/*
  Shared UI primitives. Every page composes these so the app stays visually
  consistent with DESIGN_SYSTEM.md (run light here — see globals.css). New
  screens should reach for these first instead of re-styling raw elements.
*/

export function PageShell({ children }: { children: ReactNode }) {
  return <main className="mx-auto w-full max-w-3xl px-5 py-10">{children}</main>;
}

export function BackLink({
  href,
  children = "kembali",
}: {
  href: string;
  children?: ReactNode;
}) {
  return (
    <Link
      href={href}
      className="mb-4 inline-flex items-center gap-1.5 text-sm text-ink-3 transition-colors hover:text-ink"
    >
      <span aria-hidden>&larr;</span>
      {children}
    </Link>
  );
}

export function PageHeader({
  eyebrow,
  title,
  action,
}: {
  eyebrow?: string;
  title: string;
  action?: ReactNode;
}) {
  return (
    <header className="mb-7 flex items-end justify-between gap-4">
      <div>
        {eyebrow ? (
          <p className="mb-1.5 font-mono text-[11px] uppercase tracking-[0.18em] text-ink-4">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
      </div>
      {action}
    </header>
  );
}

export function Card({
  className = "",
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={
        "rounded-card border border-hair bg-surface shadow-[0_1px_2px_rgba(17,24,39,0.04),0_6px_16px_rgba(17,24,39,0.04)] " +
        className
      }
    >
      {children}
    </div>
  );
}

type ButtonVariant = "primary" | "ghost";

const buttonBase =
  "inline-flex items-center justify-center gap-1.5 rounded-pill px-4 py-2 text-sm font-medium transition-colors disabled:pointer-events-none disabled:opacity-50";

function buttonClass(variant: ButtonVariant) {
  if (variant === "primary") {
    return `${buttonBase} bg-accent text-accent-ink hover:bg-accent/90`;
  }
  return `${buttonBase} border border-hair bg-[rgba(17,24,39,0.03)] text-ink hover:bg-[rgba(17,24,39,0.06)]`;
}

export function Button({
  variant = "ghost",
  className = "",
  ...props
}: ComponentProps<"button"> & { variant?: ButtonVariant }) {
  return <button className={`${buttonClass(variant)} ${className}`} {...props} />;
}

export function ButtonLink({
  variant = "ghost",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: ButtonVariant }) {
  return <Link className={`${buttonClass(variant)} ${className}`} {...props} />;
}

type Tone = "muted" | "warn" | "bad" | "good";

export function Badge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  const tones: Record<Tone, string> = {
    muted: "bg-[rgba(17,24,39,0.06)] text-ink-2",
    warn: "bg-warn-soft text-warn",
    bad: "bg-bad-soft text-bad",
    good: "bg-good-soft text-good",
  };
  return (
    <span
      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-ink-2">{label}</span>
      {children}
    </label>
  );
}

/* base field styling — add your own width (`w-full`, `flex-1`, `w-20`, …) */
export const inputClass =
  "rounded-input border border-hair bg-surface px-3 py-2 text-sm text-ink placeholder:text-ink-4 outline-none transition-colors focus:border-hair-2";

export const selectClass = `${inputClass} select-field cursor-pointer`;

export function EmptyRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan} className="py-10 text-center text-sm text-ink-4">
        {children}
      </td>
    </tr>
  );
}

export function Table({ children }: { children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-card border border-hair bg-surface">
      <table className="w-full border-collapse text-sm [&_tbody_tr:last-child_td]:border-b-0">
        {children}
      </table>
    </div>
  );
}

export function Th({ children }: { children: ReactNode }) {
  return (
    <th className="border-b border-hair bg-[rgba(17,24,39,0.02)] px-4 py-2.5 text-left text-xs font-medium uppercase tracking-wide text-ink-4">
      {children}
    </th>
  );
}

export function Td({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <td className={`border-b border-hair px-4 py-3 text-ink-2 ${className}`}>{children}</td>
  );
}
