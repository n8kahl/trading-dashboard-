import { wsStore } from "./store";
import { toast } from "sonner";

export function connectWS(baseUrl: string) {
  const url = baseUrl.replace(/^http/, "ws") + "/ws";
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
