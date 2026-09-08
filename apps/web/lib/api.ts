import { readCookie } from "./auth";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Bearer header. Server Components pass `token` explicitly (from cookies());
// client components omit it and we read the cookie.
function auth(token?: string): Record<string, string> {
  const t = token ?? readCookie("access_token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function req<T>(path: string, init: RequestInit, token?: string): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    cache: "no-store",
    ...init,
    headers: { ...(init.headers ?? {}), ...auth(token) },
  });
  if (!res.ok) {
    throw new Error(
      (await res.text()) || `${init.method ?? "GET"} ${path} -> ${res.status}`,
    );
  }
  return res.json() as Promise<T>;
}

// ---- types ----

export type Product = {
  id: number; sku: string; name: string; unit: string; price: string; stock_qty: number;
};
export type OrderListRow = {
  id: number; customer_name: string; status: string; needs_review: boolean;
  item_count: number; created_at: string;
};
export type OrderList = { items: OrderListRow[]; total: number; page: number; size: number };
export type OrderItem = {
  id: number; product_id: number | null; raw_name: string | null;
  quantity: string; unit: string; matched_score: number | null;
};
export type Order = {
  id: number; customer_name: string; status: string;
  intent: string | null; extraction_confidence: number | null; needs_review: boolean;
  created_at: string; items: OrderItem[];
};
export type Job = {
  id: string; type: string;
  status: "queued" | "processing" | "done" | "error";
  progress: number; result_ref: string | null; error: string | null;
};
export type WorkflowStep = {
  id: number; order_id: number; seq: number; step_type_name: string;
  assigned_at: string | null; completed_at: string | null; outcome: string | null;
  sla_target_minutes: number; elapsed_minutes: number | null;
};
export type MetricsSummary = {
  orders_total: number; orders_done: number; wip: number; sla_met_pct: number | null;
};
export type StepDuration = {
  step_type: string; n: number; avg_minutes: string; p50: string; p90: string; breached: number;
};
export type DailyPoint = { day: string; steps_done: number; sla_met_pct: string };
export type AgingRow = {
  order_id: number; customer_name: string; current_step: string;
  waiting_minutes: string; sla_target_minutes: number;
};

// ---- auth ----

export async function login(
  email: string,
  password: string,
): Promise<{ access_token: string; role: string; name: string }> {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (res.status === 401) throw new Error("Email atau password salah.");
  if (!res.ok) throw new Error(`login -> ${res.status}`);
  return res.json();
}

// ---- orders ----

export const getOrders = (token?: string) => req<OrderList>("/orders", {}, token);

export async function getOrder(id: string, token?: string): Promise<Order | null> {
  const res = await fetch(`${API}/orders/${id}`, {
    cache: "no-store",
    headers: auth(token),
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /orders/${id} -> ${res.status}`);
  return res.json();
}

export const getProducts = (token?: string) => req<Product[]>("/products", {}, token);

export const createOrder = (
  payload: { customer_name: string; items: { product_id: number; quantity: number }[] },
  token?: string,
) =>
  req<Order>(
    "/orders",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
    token,
  );

export const intakeOrder = (
  payload: { customer_name: string; body: string },
  token?: string,
) =>
  req<{ job_id: string }>(
    "/orders/intake",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify(payload),
    },
    token,
  );

export const getJob = (id: string, token?: string) => req<Job>(`/jobs/${id}`, {}, token);

// ---- workflow ----

export const getSteps = (orderId: string | number, token?: string) =>
  req<WorkflowStep[]>(`/orders/${orderId}/steps`, {}, token);

export const confirmOrder = (orderId: number, token?: string) =>
  req<{ id: number; status: string }>(
    `/orders/${orderId}/confirm`,
    { method: "POST" },
    token,
  );

export const completeStep = (stepId: number, outcome: string, token?: string) =>
  req<WorkflowStep>(
    `/workflow-steps/${stepId}/complete`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outcome }),
    },
    token,
  );

// ---- metrics ----

export const getSummary = (days: number, token?: string) =>
  req<MetricsSummary>(`/metrics/summary?days=${days}`, {}, token);
export const getStepDurations = (days: number, token?: string) =>
  req<StepDuration[]>(`/metrics/step-durations?days=${days}`, {}, token);
export const getDaily = (days: number, token?: string) =>
  req<DailyPoint[]>(`/metrics/daily?days=${days}`, {}, token);
export const getAging = (token?: string) =>
  req<AgingRow[]>("/metrics/aging", {}, token);
