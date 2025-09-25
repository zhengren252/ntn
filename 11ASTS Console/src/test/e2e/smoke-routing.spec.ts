import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5173';

type Case = { path: string; title: string; h1: string; testId: string };

const cases: Case[] = [
  { path: '/strategy', title: '策略管理 - ASTS Console', h1: '策略管理', testId: 'page-strategy' },
  { path: '/trading', title: '交易执行 - ASTS Console', h1: '交易执行', testId: 'page-trading' },
  { path: '/risk', title: '风险控制 - ASTS Console', h1: '风险控制', testId: 'page-risk' },
  { path: '/data', title: '数据中心 - ASTS Console', h1: '数据中心', testId: 'page-data' },
  { path: '/finance', title: '财务管理 - ASTS Console', h1: '财务管理', testId: 'page-finance' },
  { path: '/monitor', title: '系统监控 - ASTS Console', h1: '系统监控', testId: 'page-monitor' },
];

for (const c of cases) {
  test(`Smoke: ${c.path} should have correct title and H1`, async ({ page }) => {
    await page.goto(`${BASE}${c.path}`, { waitUntil: 'domcontentloaded' });
    await expect(page).toHaveTitle(c.title);
    await expect(page.locator(`[data-testid="${c.testId}"]`)).toBeVisible();
    const h1 = page.locator('h1');
    await expect(h1).toHaveText(c.h1);
  });
}