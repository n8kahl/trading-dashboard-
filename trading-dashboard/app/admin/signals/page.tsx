"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";

export default function Page() {
  const q = useQuery({ queryKey: ["signals"], queryFn: () => apiGet("/api/v1/admin/signals?limit=20") });
  return (
    <div>
      <h1 className="text-xl font-semibold mb-3">Recent Signals</h1>
      <pre className="text-xs bg-muted p-3 rounded">{q.isLoading ? "Loading..." : JSON.stringify(q.data, null, 2)}</pre>
    </div>
  );
}
