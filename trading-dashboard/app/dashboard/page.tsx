"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import { WatchlistZ, OptionsPicksZ } from "@/lib/zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Page() {
  const wl = useQuery({ queryKey: ["watchlist"], queryFn: () => apiGet("/api/v1/screener/watchlist/get", WatchlistZ) });
  const picks = useQuery({
    queryKey: ["picks","SPY"],
    queryFn: () => apiPost("/api/v1/options/pick", { symbol: "SPY", side: "long_call", horizon: "intra", n: 5 }, OptionsPicksZ)
  });

  return (
    <div className="grid gap-4 grid-cols-1 xl:grid-cols-2">
      <Card>
        <CardHeader><CardTitle>Watchlist</CardTitle></CardHeader>
        <CardContent>
          {wl.isLoading ? "Loading..." : wl.data?.symbols?.join(", ")}
        </CardContent>
      </Card>
      <Card>
        <CardHeader><CardTitle>SPY ATM Picks (delayed)</CardTitle></CardHeader>
        <CardContent>
          {picks.isLoading ? "Loading..." : (
            <ul className="text-sm">
              {picks.data?.picks?.slice(0,5).map((p, i) => (
                <li key={i}>{p.symbol} · strike {p.strike ?? "?"} · mark {p.mark ?? "?"}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
