"use client";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { apiGet } from "@/lib/api";
export function Topbar() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => apiGet("/api/v1/diag/health"),
  });
  const { data: ready } = useQuery({
    queryKey: ["ready"],
    queryFn: () => apiGet("/api/v1/diag/ready"),
  });
  return (
    <header className="flex items-center justify-between border-b p-3">
      <div className="font-medium">My Trading Command Center</div>
      <div className="flex gap-2">
        <Badge variant={health?.ok ? "default" : "destructive"}>
          health: {health?.status ?? "unknown"}
        </Badge>
        <Badge variant={ready?.ready ? "default" : "destructive"}>
          ready: {String(ready?.ready ?? false)}
        </Badge>
      </div>
    </header>
  );
}
