import QueryProvider from "@/src/lib/query-provider";
import "./globals.css";

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
          <QueryProvider>{children}</QueryProvider>
        </div>
      </body>
    </html>
  );
}
