'use client';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../lib/api';
import { OptionContractsSchema } from '../../lib/zod';
import { Table } from '../../components/ui/table';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';

export default function OptionsPage() {
  const [form, setForm] = useState({ symbol: 'SPY', side: 'call', horizon: '30', n: '5' });
  const { data = [], refetch, isFetching } = useQuery({
    queryKey: ['options', form],
    queryFn: () => apiGet(`/api/v1/options/pick?symbol=${form.symbol}&side=${form.side}&horizon=${form.horizon}&n=${form.n}`, OptionContractsSchema),
  });
  return (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <Input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} placeholder="Symbol" />
        <Input value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })} placeholder="Side" />
        <Input value={form.horizon} onChange={(e) => setForm({ ...form, horizon: e.target.value })} placeholder="Horizon" />
        <Input value={form.n} onChange={(e) => setForm({ ...form, n: e.target.value })} placeholder="N" />
        <Button onClick={() => refetch()} disabled={isFetching}>Go</Button>
      </div>
      {data.length ? (
        <Table
          data={data}
          columns={[
            { header: 'Symbol', accessor: (r) => r.symbol },
            { header: 'Strike', accessor: (r) => r.strike },
            { header: 'Delta', accessor: (r) => r.delta ?? '-' },
          ]}
        />
      ) : (
        <p>No contracts found.</p>
      )}
    </div>
  );
}
