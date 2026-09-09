import crypto from "node:crypto";

import { NextResponse, type NextRequest } from "next/server";

const APP_SECRET = process.env.WHATSAPP_APP_SECRET ?? "";

// Dev-only: pretend to be Meta. Builds a Cloud-API-shaped payload, signs it with
// the same app secret, and posts it to our own /api/webhooks/whatsapp — so the
// simulator exercises the real webhook path (HMAC check + payload parsing).
export async function POST(req: NextRequest) {
  const { wa_id, name, body } = await req.json();
  if (typeof wa_id !== "string" || typeof body !== "string" || !wa_id || !body) {
    return NextResponse.json(
      { error: "wa_id and body are required" },
      { status: 400 },
    );
  }

  const payload = {
    entry: [
      {
        changes: [
          {
            value: {
              contacts: [{ wa_id, profile: { name: name ?? "" } }],
              messages: [
                {
                  from: wa_id,
                  type: "text",
                  text: { body },
                  id: `wamid.SIM${Date.now()}`,
                },
              ],
            },
          },
        ],
      },
    ],
  };
  const raw = JSON.stringify(payload);
  const sig =
    "sha256=" +
    crypto.createHmac("sha256", APP_SECRET).update(raw).digest("hex");

  const res = await fetch(new URL("/api/webhooks/whatsapp", req.nextUrl.origin), {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Hub-Signature-256": sig },
    body: raw,
  });

  return NextResponse.json({ forwarded: res.status }, { status: res.ok ? 200 : 502 });
}
