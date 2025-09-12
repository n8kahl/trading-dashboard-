"use client"
import { useQuery } from "@tanstack/react-query"
import { apiGet } from "../lib/api"
import { HealthSchema, ReadySchema } from "../lib/zod"

export function Topbar() {
  const health = useQuery({
    queryKey: ["health"],
    queryFn: async () => {
      const start = performance.now()
      const data = await apiGet("/api/v1/diag/health", HealthSchema)
      const latency = performance.now() - start
      return { ...data, latency }
    },
  })

  const ready = useQuery({
    queryKey: ["ready"],
    queryFn: () => apiGet("/api/v1/diag/ready", ReadySchema),
  })

  return (
    <header className="flex items-center justify-between bg-gray-950 px-4 py-2 border-b border-gray-800">
      <div className="flex items-center space-x-2">
        <span className={`text-sm ${health.data?.status === "ok" ? "text-green-400" : "text-red-400"}`}>
          Health: {health.data?.status ?? "..."}
        </span>
        <span className="text-sm">{health.data ? `${health.data.latency.toFixed(0)}ms` : ""}</span>
        <span className={`text-sm ${ready.data?.status === "ok" ? "text-green-400" : "text-red-400"}`}>
          Ready: {ready.data?.status ?? "..."}
        </span>
      </div>
      <div className="text-sm text-gray-400">API: Connected</div>
    </header>
  )
}
