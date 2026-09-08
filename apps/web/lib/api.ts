const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Product = {
  id: number; sku: string; name: string; unit: string; price: string; stock_qty: number;
};
export type OrderListRow = {
  id: number; customer_name: string; status: string; needs_review: boolean;
  item_count: number; created_at: string;
};
export type OrderList = {
  items: OrderListRow[]; total: number; page: number; size: number;
};
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
  id: string;
  type: string;
  status: "queued" | "processing" | "done" | "error";
  progress: number;
  result_ref: string | null;
  error: string | null;
};

export async function getOrders(): Promise<OrderList> {
  const res = await fetch(`${API}/orders`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /orders -> ${res.status}`);
  return res.json();
}

export async function getOrder(id: string): Promise<Order | null> {
  const res = await fetch(`${API}/orders/${id}`, { cache: "no-store" });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`GET /orders/${id} -> ${res.status}`);
  return res.json();
}

export async function getProducts(): Promise<Product[]> {
  const res = await fetch(`${API}/products`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /products -> ${res.status}`);
  return res.json();
}

export async function createOrder(payload: {
  customer_name: string;
  items: { product_id: number; quantity: number }[];
}): Promise<Order> {
  const res = await fetch(`${API}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error((await res.text()) || `POST /orders -> ${res.status}`);
  return res.json();
}

export async function intakeOrder(payload: {
  customer_name: string;
  body: string;
}): Promise<{ job_id: string }> {
  const res = await fetch(`${API}/orders/intake`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error((await res.text()) || `POST /orders/intake -> ${res.status}`);
  }
  return res.json();
}

export async function getJob(id: string): Promise<Job> {
  const res = await fetch(`${API}/jobs/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /jobs/${id} -> ${res.status}`);
  return res.json();
}

export type WorkflowStep = {
  id: number;
  order_id: number;
  seq: number;
  step_type_name: string;
  assigned_at: string | null;
  completed_at: string | null;
  outcome: string | null;
  sla_target_minutes: number;
  elapsed_minutes: number | null;
};

export async function getSteps(orderId: string | number): Promise<WorkflowStep[]> {
  const res = await fetch(`${API}/orders/${orderId}/steps`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /orders/${orderId}/steps -> ${res.status}`);
  return res.json();
}

export async function confirmOrder(orderId: number): Promise<void> {
  const res = await fetch(`${API}/orders/${orderId}/confirm`, { method: "POST" });
  if (!res.ok) throw new Error((await res.text()) || `confirm -> ${res.status}`);
}

export async function completeStep(stepId: number, outcome: string): Promise<void> {
  const res = await fetch(`${API}/workflow-steps/${stepId}/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ outcome }),
  });
  if (!res.ok) throw new Error((await res.text()) || `complete -> ${res.status}`);
}

// ---- metrics ----

export type MetricsSummary = {
  orders_total: number;
  orders_done: number;
  wip: number;
  sla_met_pct: number | null;
};
export type StepDuration = {
  step_type: string;
  n: number;
  avg_minutes: string;
  p50: string;
  p90: string;
  breached: number;
};
export type DailyPoint = { day: string; steps_done: number; sla_met_pct: string };
export type AgingRow = {
  order_id: number;
  customer_name: string;
  current_step: string;
  waiting_minutes: string;
  sla_target_minutes: number;
};

async function metricsFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${API}/metrics/${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`GET /metrics/${path} -> ${res.status}`);
  return res.json();
}

export const getSummary = (days: number) =>
  metricsFetch<MetricsSummary>(`summary?days=${days}`);
export const getStepDurations = (days: number) =>
  metricsFetch<StepDuration[]>(`step-durations?days=${days}`);
export const getDaily = (days: number) =>
  metricsFetch<DailyPoint[]>(`daily?days=${days}`);
export const getAging = () => metricsFetch<AgingRow[]>("aging");
