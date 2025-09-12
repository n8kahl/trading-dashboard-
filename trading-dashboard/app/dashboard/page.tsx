'use client';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../lib/api';
import { WatchlistSchema, RankedPicksSchema, OptionContractsSchema } from '../../lib/zod';
import { Table } from '../../components/ui/table';
import { Skeleton } from '../../components/ui/skeleton';

export default function DashboardPage() {
  const watchlist = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => apiGet('/api/v1/screener/watchlist/get', WatchlistSchema),
  });
  const ranked = useQuery({
    queryKey: ['ranked'],
    queryFn: () => apiGet('/api/v1/screener/watchlist/ranked', RankedPicksSchema),
  });
  const options = useQuery({
    queryKey: ['atm'],
    queryFn: () => apiGet('/api/v1/options/pick?symbol=SPY', OptionContractsSchema),
  });

  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-2 text-lg font-semibold">Watchlist</h2>
        {watchlist.isLoading ? (
          <Skeleton className="h-24" />
        ) : watchlist.data?.length ? (
          <Table data={watchlist.data.slice(0,5)} columns={[{ header: 'Symbol', accessor: (r) => r.symbol }]} />
        ) : (
          <p>No symbols right now, try again in a few minutes.</p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">Ranked Picks</h2>
        {ranked.isLoading ? (
          <Skeleton className="h-24" />
        ) : ranked.data?.length ? (
          <Table data={ranked.data.slice(0,5)} columns={[{ header: 'Symbol', accessor: (r) => r.symbol }, {header: 'Score', accessor: (r)=>r.score}]} />
        ) : (
          <p>No picks right now, try again in a few minutes.</p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-lg font-semibold">ATM Contracts</h2>
        {options.isLoading ? (
          <Skeleton className="h-24" />
        ) : options.data?.length ? (
          <Table data={options.data.slice(0,5)} columns={[
            { header: 'Symbol', accessor: (r) => r.symbol },
            { header: 'Delta', accessor: (r) => r.delta ?? '-' },
            { header: 'Gamma', accessor: (r) => r.gamma ?? '-' },
            { header: 'Theta', accessor: (r) => r.theta ?? '-' },
          ]} />
        ) : (
          <p>No contracts found.</p>
        )}
      </section>
    </div>
  );
}
