import Link from 'next/link';

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/screener/watchlist', label: 'Screener' },
  { href: '/options', label: 'Options' },
  { href: '/plan', label: 'Plan' },
  { href: '/sizing', label: 'Sizing' },
  { href: '/alerts', label: 'Alerts' },
  { href: '/admin/signals', label: 'Admin' },
  { href: '/diagnostics', label: 'Diagnostics' },
];

export function Sidebar() {
  return (
    <aside className="w-48 bg-gray-900 p-4 space-y-2">
      {links.map((l) => (
        <Link key={l.href} href={l.href} className="block text-gray-300 hover:text-white">
          {l.label}
        </Link>
      ))}
    </aside>
  );
}
