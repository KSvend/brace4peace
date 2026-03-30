import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.IRIS_BACKEND_URL || "http://localhost:8000";
const API_KEY = process.env.B4P_API_KEY || "";

export async function GET(request: NextRequest) {
  const reviewer = request.nextUrl.searchParams.get("reviewer") || "";
  const limit = request.nextUrl.searchParams.get("limit") || "20";
  const offset = request.nextUrl.searchParams.get("offset") || "0";
  const res = await fetch(
    `${BACKEND}/posts/blind-review-queue?reviewer=${reviewer}&limit=${limit}&offset=${offset}`,
    { headers: { "X-API-Key": API_KEY } }
  );
  const data = await res.json();
  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const res = await fetch(`${BACKEND}/posts/blind-annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  return NextResponse.json(data);
}
