'use client';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../../lib/api';
import { z } from 'zod';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { Skeleton } from '../../../components/ui/skeleton';

const MetricsSchema = z.array(z.object({ bucket: z.number(), expected: z.number(), actual: z.number(), expectancy: z.number() }));

export default function AdminDiagnosticsPage() {
  const { data, isPending } = useQuery({
    queryKey: ['admin-metrics'],
    queryFn: () => apiGet('/api/v1/admin/diag/metrics', MetricsSchema),
  });

  if (isPending) return <Skeleton className="h-64" />;
  if (!data) return <p>No diagnostics.</p>;

  return (
    <div className="space-y-8">
      <div className="h-64">
        <h2 className="mb-2 font-semibold">Calibration</h2>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="expected" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="actual" stroke="#8884d8" />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="h-64">
        <h2 className="mb-2 font-semibold">Expectancy</h2>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis dataKey="bucket" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="expectancy" fill="#82ca9d" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
