'use client';
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiPost } from '../../lib/api';
import { SizingResponseSchema } from '../../lib/zod';
import { Input } from '../../components/ui/input';
import { Button } from '../../components/ui/button';

export default function SizingPage() {
  const [symbol, setSymbol] = useState('');
  const mutation = useMutation({
    mutationFn: (s: string) => apiPost('/api/v1/sizing/suggest', { symbol: s }, SizingResponseSchema),
  });
  return (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="Symbol" />
        <Button onClick={() => mutation.mutate(symbol)} disabled={mutation.isLoading}>Suggest</Button>
      </div>
      {mutation.data && (
        <div className="space-y-2">
          <div>Qty: {mutation.data.qty}</div>
          <div>Expected R: {mutation.data.expected_R}</div>
        </div>
      )}
    </div>
  );
}
