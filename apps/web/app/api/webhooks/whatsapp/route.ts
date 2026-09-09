import crypto from "node:crypto";

import { NextResponse, type NextRequest } from "next/server";

const VERIFY_TOKEN = process.env.WHATSAPP_VERIFY_TOKEN ?? "";
const APP_SECRET = process.env.WHATSAPP_APP_SECRET ?? "";
const INTERNAL_SECRET = process.env.INTERNAL_API_SECRET ?? "";
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// GET — Meta webhook verification handshake (runs once on setup).
export function GET(req: NextRequest) {
  const p = req.nextUrl.searchParams;
  if (
    p.get("hub.mode") === "subscribe" &&
    p.get("hub.verify_token") === VERIFY_TOKEN
  ) {
    return new NextResponse(p.get("hub.challenge") ?? "", { status: 200 });
  }
  return new NextResponse("forbidden", { status: 403 });
}

function verifySignature(raw: string, header: string | null): boolean {
  if (!header || !APP_SECRET) return false;
  const expected =
    "sha256=" +
    crypto.createHmac("sha256", APP_SECRET).update(raw).digest("hex");
  const a = Buffer.from(header);
  const b = Buffer.from(expected);
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}

type WaMessage = {
  wa_id: string;
  body: string;
  name_hint: string;
  wa_message_id: string | null;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractMessages(payload: any): WaMessage[] {
  const out: WaMessage[] = [];
  for (const entry of payload?.entry ?? []) {
    for (const change of entry?.changes ?? []) {
      const value = change?.value ?? {};
      const nameByWaId: Record<string, string> = {};
      for (const c of value.contacts ?? []) {
        if (c?.wa_id) nameByWaId[c.wa_id] = c?.profile?.name ?? "";
      }
      for (const m of value.messages ?? []) {
        if (m?.type !== "text") continue;
        out.push({
          wa_id: m.from,
          body: m.text?.body ?? "",
          name_hint: nameByWaId[m.from] ?? "",
          wa_message_id: m.id ?? null,
        });
      }
    }
  }
  return out;
}

export async function POST(req: NextRequest) {
  const raw = await req.text();

  if (!verifySignature(raw, req.headers.get("x-hub-signature-256"))) {
    return NextResponse.json(
      { error: { code: "bad_signature", message: "invalid signature" } },
      { status: 401 },
    );
  }

  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return NextResponse.json({ error: { code: "bad_json" } }, { status: 400 });
  }

  const messages = extractMessages(payload);
  await Promise.all(
    messages.map((m) =>
      fetch(`${API}/internal/wa-message`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Internal-Secret": INTERNAL_SECRET,
        },
        body: JSON.stringify(m),
      }).catch(() => undefined),
    ),
  );

  // Meta only needs a fast 200.
  return NextResponse.json({ received: messages.length });
}
