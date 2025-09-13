import QueryProvider from "@/src/lib/query-provider";
import BootSnapshot from "@/src/components/BootSnapshot";
import "./globals.css";
import { Toaster } from "sonner";

export const metadata = { title: "Trading Assistant Dashboard" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="topnav">
          <a href="/">Dashboard</a>
          <a href="/admin">Admin</a>
        </div>
        <div className="container">
          <QueryProvider>
            <BootSnapshot />
            {children}
          </QueryProvider>
          <Toaster position="top-right" />
        </div>
      </body>
    </html>
  );
}
