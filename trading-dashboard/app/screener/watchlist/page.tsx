"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { WatchlistZ } from "@/lib/zod";

export default function Page() {
  const { data, isLoading } = useQuery({ queryKey: ["watchlist"], queryFn: () => apiGet("/api/v1/screener/watchlist/get", WatchlistZ) });
  return (
    <div>
      <h1 className="text-xl font-semibold mb-3">Watchlist</h1>
      {isLoading ? "Loading..." : (
        <ul className="list-disc ml-5">
          {data?.symbols?.map(s => <li key={s}>{s}</li>)}
        </ul>
      )}
    </div>
  );
}
