'use client';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../../lib/api';
import { PositionsSchema } from '../../../lib/zod';
import { Table } from '../../../components/ui/table';

export default function AdminPositionsPage() {
  const { data = [] } = useQuery({ queryKey: ['positions'], queryFn: () => apiGet('/api/v1/admin/positions', PositionsSchema) });
  return (
    <div>
      {data.length ? (
        <Table
          data={data}
          columns={[
            { header: 'Symbol', accessor: (r) => r.symbol },
            { header: 'Qty', accessor: (r) => r.qty },
            { header: 'Basis', accessor: (r) => r.basis },
          ]}
        />
      ) : (
        <p>No positions.</p>
      )}
    </div>
  );
}
