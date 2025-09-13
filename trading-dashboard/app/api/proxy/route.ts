import { NextRequest, NextResponse } from "next/server";

// Proxies requests to the backend API to avoid CORS in the browser.
// Reads base URL and optional API key from env.

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

function join(base: string, path: string) {
  if (!base) return path;
  const b = base.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${b}${p}`;
}

export async function GET(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path") || "/";
  const url = new URL(join(API_BASE, path));
  // forward query params except `path`
  req.nextUrl.searchParams.forEach((v, k) => {
    if (k !== "path") url.searchParams.set(k, v);
  });

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      // Propagate content-type for JSON endpoints
      "Accept": "application/json",
    },
    cache: "no-store",
  });
  const body = await res.arrayBuffer();
  return new NextResponse(body, {
    status: res.status,
    headers: res.headers,
  });
}

export async function POST(req: NextRequest) {
  const path = req.nextUrl.searchParams.get("path") || "/";
  const url = new URL(join(API_BASE, path));
  // forward query params except `path`
  req.nextUrl.searchParams.forEach((v, k) => {
    if (k !== "path") url.searchParams.set(k, v);
  });

  const body = await req.arrayBuffer();
  const res = await fetch(url.toString(), {
    method: "POST",
    headers: {
      "Content-Type": req.headers.get("content-type") || "application/json",
      ...(API_KEY ? { "X-API-Key": API_KEY } : {}),
      "Accept": "application/json",
    },
    body,
    cache: "no-store",
  });
  const buf = await res.arrayBuffer();
  return new NextResponse(buf, { status: res.status, headers: res.headers });
}

