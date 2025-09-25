import type { Metadata } from "next";
import "@fontsource/inter/400.css";
import "@fontsource/inter/700.css";
import "./globals.css";
import { Providers } from './providers'
import { Navigation } from '@/components/navigation'

export const metadata: Metadata = {
  title: "ReviewGuard - 策略审核系统",
  description: "智能化的交易策略审核和风险管理平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>
        <Providers>
          <div className="min-h-screen bg-background">
            <Navigation />
            <main className="flex-1">
              {children}
            </main>
          </div>
        </Providers>
      </body>
    </html>
  );
}
