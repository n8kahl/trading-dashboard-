'use client';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../../lib/api';
import { HealthSchema, ReadySchema } from '../../lib/zod';
import { useState } from 'react';

export default function DiagnosticsPage() {
  const health = useQuery({ queryKey: ['health'], queryFn: () => apiGet('/api/v1/diag/health', HealthSchema) });
  const ready = useQuery({ queryKey: ['ready'], queryFn: () => apiGet('/api/v1/diag/ready', ReadySchema) });
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <div>Health: {health.data?.status}</div>
      <div>Ready: {ready.data?.status}</div>
      <button className="underline" onClick={() => setError('Example error to test boundary')}>Trigger Error</button>
      {error && <div className="text-red-400">{error}</div>}
    </div>
  );
}
