import { useSyncExternalStore } from "react";

type Alert = { level: string; msg: string };
interface State {
  connected: boolean;
  positions: any[];
  orders: any[];
  risk: any;
  alerts: Alert[];
  prices: Record<string, number>;
}

const state: State = {
  connected: false,
  positions: [],
  orders: [],
  risk: null,
  alerts: [],
  prices: {},
};

const listeners = new Set<() => void>();

function setState(partial: Partial<State>) {
  Object.assign(state, partial);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useWS() {
  return useSyncExternalStore(subscribe, () => state.connected, () => state.connected);
}
export function usePositions() {
  return useSyncExternalStore(subscribe, () => state.positions, () => state.positions);
}
export function useOrders() {
  return useSyncExternalStore(subscribe, () => state.orders, () => state.orders);
}
export function useRisk() {
  return useSyncExternalStore(subscribe, () => state.risk, () => state.risk);
}
export function useAlerts() {
  return useSyncExternalStore(subscribe, () => state.alerts, () => state.alerts);
}
export function usePrices() {
  return useSyncExternalStore(subscribe, () => state.prices, () => state.prices);
}

export const wsStore = {
  setState,
  getState: () => state,
};
