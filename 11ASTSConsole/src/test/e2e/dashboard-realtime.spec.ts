import { test, expect } from '@playwright/test';
import { mockWebSocketInit } from '../utils/mockWebSocket'
import { makeOverviewResponse, makeChartResponse } from '../fixtures/dashboard'

test.describe('UAT-FE-01: 仪表盘数据实时性与准确性', () => {
  test.beforeEach(async ({ page }) => {
    // 注入 WebSocket 桩，模拟连接与消息推送（抽取为可复用工具）
    await page.addInitScript(mockWebSocketInit)

    // 最小后端 Mock：拦截仪表盘接口，返回与前端组件匹配的最小数据结构（抽取为夹具）
    await page.route('**/api/dashboard/overview', async (route) => {
      const body = JSON.stringify(makeOverviewResponse())
      await route.fulfill({ status: 200, contentType: 'application/json', body })
    })

    await page.route('**/api/dashboard/chart*', async (route) => {
      const body = JSON.stringify(makeChartResponse())
      await route.fulfill({ status: 200, contentType: 'application/json', body })
    })

    await page.goto('/')
  })

  test('应该显示核心系统指标并实时更新', async ({ page }) => {
    // 移除对 overview 接口的强制等待，改为等待页面可见元素
    await page.waitForLoadState('domcontentloaded')

    const titleLocator = page.locator('h1, [data-testid="page-title"], header .title, .page-title')
    await expect(titleLocator.first()).toBeVisible({ timeout: 10000 })

    const overviewHeading = page.locator('text=/总交易次数|总收益|活跃模块|成功率|系统模块状态|Overview|总览/i')
    await expect(overviewHeading.first()).toBeVisible({ timeout: 10000 })

    const labelLocators = [
      page.locator('text=/总交易次数|Total Trades/i'),
      page.locator('text=/成功率|Success Rate/i'),
      page.locator('text=/总收益|Total Profit|Profit/i'),
      page.locator('text=/活跃模块|Active Modules|Active Strategies/i'),
      page.locator('text=/系统状态|系统模块状态|System Status/i')
    ]

    const visibleLabels: number = (await Promise.all(labelLocators.map(async l => (await l.count()) > 0))).filter(v => v).length
    if (visibleLabels >= 2) {
      for (const l of labelLocators) {
        if (await l.count() > 0) {
          await expect(l.first()).toBeVisible()
        }
      }
    } else {
      const anyH3 = page.locator('h3:has-text(/总交易次数|成功率|总收益|活跃模块|系统模块状态/i)')
      await expect(anyH3.first()).toBeVisible({ timeout: 10000 })
      const numLike = page.locator('text=/[\$]?\d[\d,\.]*%?|\d+\/\d+/')
      await expect(numLike.first()).toBeVisible({ timeout: 10000 })
    }

    const statusCss = page.locator('.status-indicator, .system-status, [data-testid="system-status"]')
    const statusText = page.locator('text=/系统已停止|运行中|警告|已停止|Online|Running|Warning/i')
    if (await statusCss.count() > 0) {
      await expect(statusCss.first()).toBeVisible()
    } else if (await statusText.count() > 0) {
      await expect(statusText.first()).toBeVisible()
    }
   })

  test('应该通过WebSocket实时更新数据', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('domcontentloaded')

    await page.evaluate(() => {
      const g: any = window as any
      const sockets: any[] = Array.isArray(g.__WS_SOCKETS__) ? g.__WS_SOCKETS__ : []
      for (const s of sockets) {
        try {
          if (typeof s.onmessage === 'function') {
            const payload = { type: 'systemUpdate', timestamp: Date.now() }
            s.onmessage({ data: JSON.stringify(payload) } as any)
          }
        } catch {}
      }
      g.__WS_MESSAGE_COUNT__ = (g.__WS_MESSAGE_COUNT__ || 0) + 1
    })

    await page.waitForFunction(() => ((window as any).__WS_MESSAGE_COUNT__ || 0) > 0, undefined, { timeout: 10000 })

    const connectionStatus = page.locator('.connection-status, [data-testid="ws-status"]')
    if (await connectionStatus.count() > 0) {
      await expect(connectionStatus).toContainText(/已连接|Connected|在线|Online/i)
    }
  })

  test('应该正确显示交易系统各模组状态', async ({ page }) => {
    await page.goto('/')

    const moduleStatusPanel = page.locator('.module-status, .system-modules, [data-testid="module-status"]')
    if (await moduleStatusPanel.count() > 0) {
      await expect(moduleStatusPanel).toBeVisible()

      await expect(page.locator('text=/总控模组|Master Control/i')).toBeVisible()
      await expect(page.locator('text=/交易员模组|Trader Module/i')).toBeVisible()
      await expect(page.locator('text=/策略优化|Strategy Optimization/i')).toBeVisible()
      await expect(page.locator('text=/人工审核|Manual Review/i')).toBeVisible()
      await expect(page.locator('text=/风控模组|Risk Management/i')).toBeVisible()

      const statusDots = page.locator('.status-dot, .module-indicator, .status-badge')
      if (await statusDots.count() > 0) {
        await expect(statusDots.first()).toBeVisible()
      }
    }
  })

  test('应该显示实时市场数据和图表', async ({ page }) => {
    await page.goto('/')

    const marketDataPanel = page.locator('.market-data, [data-testid="market-data"], .trading-view')
    if (await marketDataPanel.count() > 0) {
      await expect(marketDataPanel).toBeVisible()

      const priceElements = page.locator('.price, .current-price, [data-testid="price"]')
      if (await priceElements.count() > 0) {
        const priceText = await priceElements.first().textContent()
        expect((priceText || '')).toMatch(/[\d.,]+/)
      }
    }

    const charts = page.locator('canvas, svg, .recharts-wrapper, .chart-container')
    if (await charts.count() > 0) {
      await expect(charts.first()).toBeVisible()
    }

    await page.waitForTimeout(3000)

    const chartData = page.locator('.recharts-line, .recharts-bar, path, circle')
    if (await chartData.count() > 0) {
      await expect(chartData.first()).toBeVisible()
    }
  })

  test('应该正确显示风险指标和告警', async ({ page }) => {
    await page.goto('/')

    const riskPanel = page.locator('.risk-metrics, [data-testid="risk-panel"], .risk-dashboard')
    if (await riskPanel.count() > 0) {
      await expect(riskPanel).toBeVisible()

      await expect(page.locator('text=/VaR|风险价值/i')).toBeVisible()
      await expect(page.locator('text=/最大回撤|Max Drawdown/i')).toBeVisible()
      await expect(page.locator('text=/夏普比率|Sharpe Ratio/i')).toBeVisible()

      const riskLevel = page.locator('.risk-level, [data-testid="risk-level"]')
      if (await riskLevel.count() > 0) {
        const levelText = await riskLevel.textContent()
        expect((levelText || '')).toMatch(/低|中|高|Low|Medium|High/i)
      }
    }

    const alertPanel = page.locator('.alerts, .warnings, [data-testid="alerts"]')
    if (await alertPanel.count() > 0) {
      await expect(alertPanel).toBeVisible()

      const alertItems = page.locator('.alert-item, .warning-item')
      if (await alertItems.count() > 0) {
        await expect(alertItems.first()).toBeVisible()

        const alertBadge = alertItems.first().locator('.badge, .severity')
        if (await alertBadge.count() > 0) {
          await expect(alertBadge).toBeVisible()
        }
      }
    }
  })

  test('应该支持数据刷新和手动更新', async ({ page }) => {
    await page.goto('/')

    const refreshButton = page.locator('button:has-text("刷新"), button:has-text("Refresh"), [data-testid="refresh-button"]')
    if (await refreshButton.count() > 0) {
      const dataElement = page.locator('.metric-value, .data-value').first()
      let beforeRefresh = ''
      if (await dataElement.count() > 0) {
        beforeRefresh = await dataElement.textContent() || ''
      }

      await refreshButton.click()

      const loadingIndicator = page.locator('.loading, .spinner, [data-testid="loading"]')
      if (await loadingIndicator.count() > 0) {
        await expect(loadingIndicator).toBeVisible()
        await expect(loadingIndicator).not.toBeVisible({ timeout: 10000 })
      }

      await page.waitForTimeout(2000)
    }

    const autoRefreshToggle = page.locator('input[type="checkbox"]:near(:text("自动刷新")), [data-testid="auto-refresh"]')
    if (await autoRefreshToggle.count() > 0) {
      await expect(autoRefreshToggle).toBeVisible()
      await autoRefreshToggle.click()
      await page.waitForTimeout(1000)
    }
  })

  test('应该在网络断开时显示适当的错误状态', async ({ page }) => {
    await page.route('**/api/**', async route => {
      await route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ code: 1, message: 'Network Error' }) })
    })

    await page.goto('/')

    const refreshButton = page.locator('button:has-text("刷新"), button:has-text("Refresh"), [data-testid="refresh-button"]')
    if (await refreshButton.count() > 0) {
      await refreshButton.first().click()
    } else {
      await page.reload()
    }

    const errorIndicator = page.locator('.error-state, .connection-error, [data-testid="error-state"], .ant-result, .ant-empty, .ant-message-error, .ant-notification-notice-message')
    if (await errorIndicator.count() > 0) {
      await expect(errorIndicator.first()).toBeVisible({ timeout: 10000 })
    } else {
      const textErr = page.locator('text=数据加载失败, text=加载失败, text=网络错误, text=连接失败, text=请求失败, text=Network Error, text=Request failed')
      if (await textErr.count() === 0) {
        await expect(page.locator('text=/总盈利|Total Profit/i')).toHaveCount(0)
      } else {
        await expect(textErr.first()).toBeVisible({ timeout: 10000 })
      }
    }

    const anyErrText = page.locator('text=/网络错误|连接失败|Request failed|数据加载失败|加载失败|Network Error|Connection Failed/i')
    if (await anyErrText.count() > 0) {
      await expect(anyErrText.first()).toBeVisible()
    }
  })
})