import React from 'react';

export interface Column<T> {
  header: string;
  accessor: (row: T) => React.ReactNode;
}

interface TableProps<T> {
  data: T[];
  columns: Column<T>[];
}

export function Table<T>({ data, columns }: TableProps<T>) {
  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr>
          {columns.map((col, i) => (
            <th key={i} className="px-2 py-1 border-b border-gray-700">
              {col.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row, i) => (
          <tr key={i} className="odd:bg-gray-900">
            {columns.map((col, j) => (
              <td key={j} className="px-2 py-1 border-b border-gray-800">
                {col.accessor(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
