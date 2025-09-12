'use client';
import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { apiGet } from '../../../lib/api';
import { RankedPicksSchema } from '../../../lib/zod';
import { Table } from '../../../components/ui/table';
import { Input } from '../../../components/ui/input';
import Link from 'next/link';

export default function RankedPage() {
  const { data = [] } = useQuery({ queryKey: ['ranked'], queryFn: () => apiGet('/api/v1/screener/watchlist/ranked', RankedPicksSchema) });
  const [filter, setFilter] = useState('');
  const filtered = data.filter((d) => d.symbol.toLowerCase().includes(filter.toLowerCase()));
  return (
    <div className="space-y-4">
      <Input placeholder="Filter" value={filter} onChange={(e) => setFilter(e.target.value)} />
      {filtered.length ? (
        <Table
          data={filtered}
          columns={[
            {
              header: 'Symbol',
              accessor: (r) => <Link href={`/plan?symbol=${r.symbol}`} className="text-blue-400">{r.symbol}</Link>,
            },
            { header: 'Score', accessor: (r) => r.score },
          ]}
        />
      ) : (
        <p>No picks right now, try again in a few minutes.</p>
      )}
    </div>
  );
}
