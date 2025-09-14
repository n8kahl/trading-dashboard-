
import QueryProvider from "@/src/lib/query-provider";
import BootSnapshot from "@/src/components/BootSnapshot";
import "./globals.css";
import { Toaster } from "sonner";
import Link from "next/link";
import CommandPalette from "@/components/CommandPalette";

export const metadata = { title: "Trading Assistant Dashboard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="topnav">
          <Link href="/">Dashboard</Link>
          <Link href="/admin">Admin</Link>
        </div>
        <div className="container">
          <QueryProvider>
            <BootSnapshot />
            {children}
            <CommandPalette />
          </QueryProvider>
          <Toaster position="top-right" />
        </div>
      </body>
    </html>
  );
}
