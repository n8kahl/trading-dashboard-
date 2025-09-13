"use client";

import { useEffect } from "react";
import { apiGet } from "@/src/lib/api";
import { wsStore } from "@/src/lib/store";

export default function BootSnapshot() {
  useEffect(() => {
    (async () => {
      try {
        const s: any = await apiGet("/api/v1/stream/state");
        const positions = (s?.positions) ?? [];
        const orders = (s?.orders) ?? [];
        const risk = s?.risk ?? null;
        wsStore.setState({ positions, orders, risk });
      } catch {
        // ignore snapshot errors in UI boot
      }
    })();
  }, []);
  return null;
}

