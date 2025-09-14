"use client";

type Slice = { key: string; value: number; color: string };
type Props = { size?: number; stroke?: number; slices: Slice[] };

export default function EdgeRing({ size=120, stroke=10, slices }: Props) {
  const r = (size - stroke) / 2;
  const c = size / 2;
  const circ = 2 * Math.PI * r;
  const total = Math.max(1, slices.reduce((a, s)=> a + Math.max(0, s.value), 0));
  let acc = 0;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={c} cy={c} r={r} fill="none" stroke="#1f2937" strokeWidth={stroke} />
      {slices.map((s, i) => {
        const frac = Math.max(0, s.value) / total;
        const len = frac * circ;
        const dash = `${len} ${circ - len}`;
        const rot = (acc / total) * 360 - 90; // start at top
        acc += Math.max(0, s.value);
        return (
          <circle key={s.key} cx={c} cy={c} r={r} fill="none" stroke={s.color} strokeWidth={stroke}
            strokeDasharray={dash} transform={`rotate(${rot} ${c} ${c})`} strokeLinecap="butt" />
        );
      })}
    </svg>
  );
}

