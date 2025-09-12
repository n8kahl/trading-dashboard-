'use client';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../../lib/api';
import { SignalsSchema } from '../../../lib/zod';
import { Table } from '../../../components/ui/table';

export default function AdminSignalsPage() {
  const { data = [] } = useQuery({ queryKey: ['signals'], queryFn: () => apiGet('/api/v1/admin/signals', SignalsSchema) });
  return (
    <div>
      {data.length ? (
        <Table
          data={data}
          columns={[
            { header: 'Symbol', accessor: (r) => r.symbol },
            { header: 'Strength', accessor: (r) => r.strength },
          ]}
        />
      ) : (
        <p>No signals.</p>
      )}
    </div>
  );
}
