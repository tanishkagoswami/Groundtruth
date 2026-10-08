import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'GroundTruth Telemetry',
  description: 'Academic Code Reproducibility Diagnostics',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-slate-300">
        {children}
      </body>
    </html>
  );
}