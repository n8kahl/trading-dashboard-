"use client";

import { useEffect, useRef, useState } from "react";

export type SseStatus = "idle" | "connecting" | "open" | "closed";

export function useEventSource(url: string, deps: any[] = []) {
  const [status, setStatus] = useState<SseStatus>("idle");
  const [messages, setMessages] = useState<any[]>([]);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    setStatus("connecting");
    // Close any existing connection first
    if (esRef.current) { esRef.current.close(); esRef.current = null; }
    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setStatus("open");
    es.onerror = () => {
      setStatus("closed");
    };
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        setMessages(prev => [data, ...prev].slice(0, 50));
      } catch {
        // Heartbeats or malformed payloads ignored
      }
    };
    return () => { es.close(); esRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { status, messages };
}

