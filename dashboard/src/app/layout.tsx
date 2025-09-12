import './globals.css';
import Providers from './providers';

export const metadata = {
  title: 'Trading Assistant Dashboard',
  description: 'Dashboard for Trading Assistant API',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{fontFamily:'system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,Helvetica,Arial'}}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
