'use client';
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '../../lib/api';
import { PlanResponseSchema } from '../../lib/zod';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';

export default function PlanPage() {
  const [symbol, setSymbol] = useState('');
  const mutation = useMutation({
    mutationFn: (s: string) => apiPost('/api/v1/plan/validate', { symbol: s }, PlanResponseSchema),
  });
  return (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="Symbol" />
        <Button onClick={() => mutation.mutate(symbol)} disabled={mutation.isPending}>Validate</Button>
      </div>
      {mutation.data && (
        <div className="space-y-2">
          <div>Targets: {mutation.data.targets.join(', ')}</div>
          <div>Per Unit Risk: {mutation.data.per_unit_risk}</div>
          {mutation.data.notes && <div>Notes: {mutation.data.notes}</div>}
        </div>
      )}
    </div>
  );
}
