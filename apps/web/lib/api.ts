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
}): Promise<Order> {
  const res = await fetch(`${API}/orders/intake`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error((await res.text()) || `POST /orders/intake -> ${res.status}`);
  }
  return res.json();
}
