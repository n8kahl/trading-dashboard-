export type CoachMsg = { role: 'system'|'user'|'assistant'|'tool'; content: string; tool_call_id?: string; name?: string };

export async function coachChat(messages: CoachMsg[]) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ''}/api/v1/coach/chat`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ messages }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

