"use client";
import { usePositions } from "@/src/lib/store";

export default function PositionsPage() {
  const positions = usePositions();
  return (
    <main className="container">
      <h1>Positions</h1>
      <table className="table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Qty</th>
            <th>Avg</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p: any) => (
            <tr key={p.symbol}>
              <td>{p.symbol}</td>
              <td>{p.qty}</td>
              <td>{p.avg_price}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
