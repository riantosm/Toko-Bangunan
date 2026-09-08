"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { DailyPoint, StepDuration } from "@/lib/api";

const axisTick = { fontSize: 11, fill: "var(--color-ink-3)" };
const tooltipStyle = {
  background: "var(--color-surface)",
  border: "1px solid var(--color-hair)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--color-ink)",
};

export function StepDurationChart({ data }: { data: StepDuration[] }) {
  const rows = data.map((d) => ({
    name: d.step_type,
    "rata-rata": Number(d.avg_minutes),
    p90: Number(d.p90),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 4, right: 8, left: -12, bottom: 4 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-hair)"
            vertical={false}
          />
          <XAxis dataKey="name" tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis tick={axisTick} tickLine={false} axisLine={false} width={44} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--color-hair)" }} />
          <Bar dataKey="rata-rata" fill="var(--color-accent)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="p90" fill="var(--color-ink-4)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function SlaTrendChart({ data }: { data: DailyPoint[] }) {
  const rows = data.map((d) => ({
    day: d.day.slice(5),
    "SLA %": Number(d.sla_met_pct),
  }));

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={rows} margin={{ top: 4, right: 8, left: -12, bottom: 4 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-hair)"
            vertical={false}
          />
          <XAxis dataKey="day" tick={axisTick} tickLine={false} axisLine={false} />
          <YAxis
            domain={[0, 100]}
            tick={axisTick}
            tickLine={false}
            axisLine={false}
            width={44}
          />
          <Tooltip contentStyle={tooltipStyle} />
          <Line
            type="monotone"
            dataKey="SLA %"
            stroke="var(--color-accent)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
