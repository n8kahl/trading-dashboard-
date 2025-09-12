"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
const items = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/screener/watchlist", label: "Screener" },
  { href: "/options", label: "Options" },
  { href: "/plan", label: "Plan" },
  { href: "/sizing", label: "Sizing" },
  { href: "/alerts", label: "Alerts" },
  { href: "/admin/signals", label: "Admin" },
  { href: "/diagnostics", label: "Diagnostics" },
];
export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-60 shrink-0 border-r p-3">
      <div className="text-sm text-muted-foreground mb-2">Trading Assistant</div>
      <nav className="space-y-1">
        {items.map(i => (
          <Link key={i.href} href={i.href}
            className={cn("block rounded px-2 py-1 hover:bg-accent hover:text-accent-foreground",
              pathname?.startsWith(i.href) && "bg-accent text-accent-foreground")}>
            {i.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
