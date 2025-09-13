import { wsStore } from "./store";
import { toast } from "sonner";

function buildWsUrl(): string {
  const key = process.env.NEXT_PUBLIC_API_KEY || "";
  const wsBase = process.env.NEXT_PUBLIC_WS_BASE || ""; // full ws(s)://host[:port][/path]
  const apiBase = process.env.NEXT_PUBLIC_API_BASE || ""; // http(s)://host
  // Prefer explicit WS base
  let url: string;
  if (wsBase) {
    url = wsBase;
  } else if (apiBase) {
    // derive wss://host/ws from https://host
    const u = new URL(apiBase);
    u.protocol = u.protocol.replace("http", "ws");
    u.pathname = "/ws";
    url = u.toString();
  } else if (typeof window !== "undefined") {
    url = window.location.origin.replace(/^http/, "ws") + "/ws";
  } else {
    url = "ws://localhost/ws";
  }
  if (key) {
    const sep = url.includes("?") ? "&" : "?";
    url += `${sep}api_key=${encodeURIComponent(key)}`;
  }
  return url;
}

export function connectWS() {
  const url = buildWsUrl();
  let socket: WebSocket | null = null;
  let retry = 1000;

  const connect = () => {
    socket = new WebSocket(url);
    socket.onopen = () => {
      wsStore.setState({ connected: true });
      retry = 1000;
    };
    socket.onclose = () => {
      wsStore.setState({ connected: false });
      setTimeout(connect, retry);
      retry = Math.min(retry * 2, 10000);
    };
    socket.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        switch (msg.type) {
          case "positions":
            wsStore.setState({ positions: msg.items });
            break;
          case "orders":
            wsStore.setState({ orders: msg.items });
            break;
          case "risk":
            wsStore.setState({ risk: msg.state });
            break;
          case "alert":
            toast(msg.msg);
            wsStore.setState({ alerts: [...wsStore.getState().alerts, msg] });
            break;
          case "price":
            wsStore.setState({ prices: { ...wsStore.getState().prices, [msg.symbol]: msg.last } });
            break;
        }
      } catch {
        /* ignore */
      }
    };
  };
  connect();
}
