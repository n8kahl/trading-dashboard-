export type CoachMsg = { role: 'system'|'user'|'assistant'|'tool'; content: string; tool_call_id?: string; name?: string };

export async function coachChat(messages: CoachMsg[]) {
  // Proxy to the backend to avoid CORS.
  const url = `/api/proxy?path=${encodeURIComponent('/api/v1/coach/chat')}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ messages }),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
