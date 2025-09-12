"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { HealthZ, ReadyZ } from "@/lib/zod";

export default function Page() {
  const health = useQuery({ queryKey: ["health"], queryFn: () => apiGet("/api/v1/diag/health", HealthZ) });
  const ready  = useQuery({ queryKey: ["ready"],  queryFn: () => apiGet("/api/v1/diag/ready", ReadyZ) });
  const routes = useQuery({ queryKey: ["routes"], queryFn: () => apiGet("/router-status") });

  return (
    <div className="grid gap-4">
      <pre className="text-xs bg-muted p-3 rounded">{JSON.stringify(health.data, null, 2)}</pre>
      <pre className="text-xs bg-muted p-3 rounded">{JSON.stringify(ready.data, null, 2)}</pre>
      <pre className="text-xs bg-muted p-3 rounded">{JSON.stringify(routes.data, null, 2)}</pre>
    </div>
  );
}
