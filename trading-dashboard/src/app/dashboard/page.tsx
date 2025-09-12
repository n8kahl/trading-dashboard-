"use client";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/api";
import { WatchlistZ, OptionsPicksZ } from "@/lib/zod";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Page() {
  const wl = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => apiGet("/api/v1/screener/watchlist/get", WatchlistZ),
  });

  const opts = useQuery({
    queryKey: ["options", wl.data?.symbols?.[0]],
    enabled: !!wl.data?.symbols?.[0],
    queryFn: async () => {
      const j = await apiPost("/api/v1/options/pick", {
        symbol: wl.data!.symbols[0],
        side: "long_call",
        horizon: "intra",
        n: 5,
        prefer: "tradier",
      }, OptionsPicksZ);
      return j;
    },
  });

  return (
    <div className="p-6 grid gap-6">
      <Card>
        <CardHeader><CardTitle>Watchlist</CardTitle></CardHeader>
        <CardContent>
          {!wl.data ? "Loading..." : (
            <ul className="list-disc pl-4">
              {wl.data.symbols.map((s) => <li key={s}>{s}</li>)}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Options (first symbol)</CardTitle></CardHeader>
        <CardContent>
          {!opts.data ? "Loading..." : (
            <pre className="text-xs overflow-auto">{JSON.stringify(opts.data.picks.slice(0,5), null, 2)}</pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
