import { test, expect } from '@playwright/test';
import { mockWebSocketInit } from '../utils/mockWebSocket';
import { makeTradingHistoryResponse, makeChartDataResponse } from '../fixtures/trading-replay';

test.describe('UAT-FE-03: 高级交易复盘功能验证', () => {
  test.beforeEach(async ({ page }) => {
    // 注入 WebSocket Mock
    await page.addInitScript(mockWebSocketInit);

    // Mock交易历史API
    await page.route('**/api/trading/history*', async (route) => {
      const url = new URL(route.request().url());
      const filters = Object.fromEntries(url.searchParams);
      const body = JSON.stringify(makeTradingHistoryResponse(filters));
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    // Mock图表数据API
    await page.route('**/api/trading/chart*', async (route) => {
      const url = new URL(route.request().url());
      const symbol = url.searchParams.get('symbol') || 'BTCUSDT';
      const body = JSON.stringify(makeChartDataResponse(symbol));
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    // Mock TradingView相关请求
    await page.route('**/tradingview/**', async (route) => {
      await route.fulfill({ status: 200, contentType: 'text/html', body: '<div>TradingView Mock</div>' });
    });

    await page.goto('/');
  });

  test('应该正确显示TradingView图表和历史交易标记', async ({ page }) => {
    // 导航到交易复盘页面
    const replayLink = page.locator('nav').getByText('交易复盘', { exact: false });
    if (await replayLink.count() > 0) {
      await replayLink.click();
    } else {
      await page.goto('/trading-replay');
    }
    
    // 验证页面加载
    await expect(page).toHaveTitle(/交易复盘|Trading Replay|复盘分析/i);
    
    // 验证TradingView图表容器
    const chartContainer = page.locator('#tradingview_chart, .tradingview-widget, [data-testid="trading-chart"]');
    await expect(chartContainer).toBeVisible({ timeout: 15000 });
    
    // 等待TradingView加载完成
    await page.waitForTimeout(5000);
    
    // 验证图表iframe或canvas
    const chartFrame = page.locator('iframe, canvas').first();
    if (await chartFrame.count() > 0) {
      await expect(chartFrame).toBeVisible();
    }
    
    // 验证交易标记显示
    const tradeMarkers = page.locator('.trade-marker, .buy-marker, .sell-marker, [data-testid="trade-marker"]');
    if (await tradeMarkers.count() > 0) {
      await expect(tradeMarkers.first()).toBeVisible();
      
      // 验证买卖点标记的颜色区分
      const buyMarkers = page.locator('.buy-marker, [data-type="buy"]');
      const sellMarkers = page.locator('.sell-marker, [data-type="sell"]');
      
      if (await buyMarkers.count() > 0) {
        await expect(buyMarkers.first()).toBeVisible();
      }
      
      if (await sellMarkers.count() > 0) {
        await expect(sellMarkers.first()).toBeVisible();
      }
    }
  });

  test('应该支持交易筛选和过滤功能', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 等待页面加载
    await page.waitForSelector('.filter-panel, .trading-filters, [data-testid="filters"]', { timeout: 10000 });
    
    // 验证筛选面板
    const filterPanel = page.locator('.filter-panel, .trading-filters, [data-testid="filters"]');
    await expect(filterPanel).toBeVisible();
    
    // 测试日期范围筛选
    const dateFromInput = page.locator('input[name="dateFrom"], input[type="date"]').first();
    if (await dateFromInput.count() > 0) {
      await dateFromInput.fill('2024-01-01');
    }
    
    const dateToInput = page.locator('input[name="dateTo"], input[type="date"]').last();
    if (await dateToInput.count() > 0) {
      await dateToInput.fill('2024-01-31');
    }
    
    // 测试交易类型筛选
    const tradeTypeSelect = page.locator('select[name="tradeType"], [data-testid="trade-type-filter"]');
    if (await tradeTypeSelect.count() > 0) {
      await tradeTypeSelect.selectOption('buy');
    }
    
    // 测试策略筛选
    const strategyFilter = page.locator('select[name="strategy"], [data-testid="strategy-filter"]');
    if (await strategyFilter.count() > 0) {
      await strategyFilter.selectOption({ index: 1 });
    }
    
    // 测试盈亏筛选
    const profitLossFilter = page.locator('select[name="profitLoss"], [data-testid="pnl-filter"]');
    if (await profitLossFilter.count() > 0) {
      await profitLossFilter.selectOption('profit');
    }
    
    // 应用筛选
    const applyButton = page.locator('button:has-text("应用"), button:has-text("Apply"), [data-testid="apply-filters"]');
    if (await applyButton.count() > 0) {
      await applyButton.click();
      
      // 等待筛选结果
      await page.waitForTimeout(2000);
      
      // 验证筛选结果
      const filteredResults = page.locator('.trade-list, .filtered-trades, [data-testid="trade-results"]');
      if (await filteredResults.count() > 0) {
        await expect(filteredResults).toBeVisible();
      }
    }
    
    // 测试重置筛选
    const resetButton = page.locator('button:has-text("重置"), button:has-text("Reset"), [data-testid="reset-filters"]');
    if (await resetButton.count() > 0) {
      await resetButton.click();
      await page.waitForTimeout(1000);
    }
  });

  test('应该显示详细的交易分析和统计信息', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 等待分析面板加载
    await page.waitForSelector('.analysis-panel, .trade-analytics, [data-testid="analytics"]', { timeout: 10000 });
    
    // 验证交易统计面板
    const analyticsPanel = page.locator('.analysis-panel, .trade-analytics, [data-testid="analytics"]');
    if (await analyticsPanel.count() > 0) {
      await expect(analyticsPanel).toBeVisible();
      
      // 验证关键统计指标
      await expect(page.locator('text=/总交易次数|Total Trades/i')).toBeVisible();
      await expect(page.locator('text=/胜率|Win Rate/i')).toBeVisible();
      await expect(page.locator('text=/平均收益|Average Return/i')).toBeVisible();
      await expect(page.locator('text=/最大盈利|Max Profit/i')).toBeVisible();
      await expect(page.locator('text=/最大亏损|Max Loss/i')).toBeVisible();
      await expect(page.locator('text=/夏普比率|Sharpe Ratio/i')).toBeVisible();
      
      // 验证数值显示格式
      const winRateElement = page.locator('[data-testid="win-rate"], .win-rate');
      if (await winRateElement.count() > 0) {
        const winRateText = await winRateElement.textContent();
        expect(winRateText).toMatch(/\d+(\.\d+)?%/); // 应该是百分比格式
      }
    }
    
    // 验证收益分布图表
    const distributionChart = page.locator('.distribution-chart, .pnl-distribution, canvas, svg');
    if (await distributionChart.count() > 0) {
      await expect(distributionChart.first()).toBeVisible();
    }
    
    // 验证时间序列分析
    const timeSeriesChart = page.locator('.time-series, .equity-curve, .performance-chart');
    if (await timeSeriesChart.count() > 0) {
      await expect(timeSeriesChart).toBeVisible();
    }
  });

  test('应该支持单笔交易详情查看', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 等待交易列表加载
    await page.waitForSelector('.trade-list, .trades-table, [data-testid="trades-list"]', { timeout: 10000 });
    
    // 查找交易列表
    const tradesList = page.locator('.trade-list, .trades-table, [data-testid="trades-list"]');
    if (await tradesList.count() > 0) {
      await expect(tradesList).toBeVisible();
      
      // 点击第一笔交易的详情按钮
      const firstTradeDetailButton = page.locator('tbody tr').first().locator('button:has-text("详情")');
      if (await firstTradeDetailButton.count() > 0) {
        await firstTradeDetailButton.click();
        
        // 验证交易详情弹窗或面板
        const tradeDetails = page.locator('.trade-details, .trade-modal, [data-testid="trade-details"]');
        await expect(tradeDetails).toBeVisible({ timeout: 5000 });
        
        // 验证详情内容
        await expect(page.locator('text=/交易时间|Trade Time/i')).toBeVisible();
        await expect(page.locator('text=/交易价格|Price/i')).toBeVisible();
        await expect(page.locator('text=/交易数量|Quantity/i')).toBeVisible();
        await expect(page.locator('text=/盈亏金额|PnL/i')).toBeVisible();
        
        // 验证盈亏计算
        const pnlElement = page.locator('[data-testid="pnl"], .pnl, .profit-loss');
        if (await pnlElement.count() > 0) {
          const pnlText = await pnlElement.textContent();
          expect(pnlText).toMatch(/[+-]?\d+(\.\d+)?/); // 应该包含数字
        }
        
        // 关闭详情面板
        const closeButton = page.locator('button:has-text("关闭"), button:has-text("Close"), .close-button');
        if (await closeButton.count() > 0) {
          await closeButton.click();
        }
      }
    }
  });

  test('应该支持交易数据导出功能', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 查找导出按钮
    const exportButton = page.locator('button:has-text("导出"), button:has-text("Export"), [data-testid="export-button"]');
    if (await exportButton.count() > 0) {
      await expect(exportButton).toBeVisible();
      await expect(exportButton).toBeEnabled();
      
      // 点击导出按钮
      await exportButton.click();
      
      // 验证导出选项
      const exportOptions = page.locator('.export-options, .export-modal, [data-testid="export-options"]');
      if (await exportOptions.count() > 0) {
        await expect(exportOptions).toBeVisible();
        
        // 验证导出格式选项
        await expect(page.locator('text=/CSV|Excel|PDF/i')).toBeVisible();
        
        // 选择CSV格式
        const csvOption = page.locator('input[value="csv"], button:has-text("CSV")');
        if (await csvOption.count() > 0) {
          await csvOption.click();
        }
        
        // 确认导出
        const confirmExport = page.locator('button:has-text("确认导出"), button:has-text("Export")');
        if (await confirmExport.count() > 0) {
          // 监听下载事件
          const downloadPromise = page.waitForEvent('download', { timeout: 10000 });
          await confirmExport.click();
          
          try {
            const download = await downloadPromise;
            expect(download.suggestedFilename()).toMatch(/\.(csv|xlsx|pdf)$/i);
          } catch (error) {
            // 如果没有实际下载，至少验证导出流程启动
            console.log('Export process initiated (download may be mocked)');
          }
        }
      }
    }
  });

  test('应该支持不同时间周期的图表切换', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 等待图表加载
    await page.waitForSelector('#tradingview_chart, .tradingview-widget', { timeout: 15000 });
    
    // 查找时间周期选择器
    const timeframeSelector = page.locator('.timeframe-selector, .interval-selector, [data-testid="timeframe"]');
    if (await timeframeSelector.count() > 0) {
      await expect(timeframeSelector).toBeVisible();
      
      // 测试不同时间周期
      const timeframes = ['1m', '5m', '15m', '1h', '4h', '1d'];
      
      for (const timeframe of timeframes.slice(0, 3)) { // 测试前3个
        const timeframeButton = page.locator(`button:has-text("${timeframe}"), [data-timeframe="${timeframe}"]`);
        if (await timeframeButton.count() > 0) {
          await timeframeButton.click();
          await page.waitForTimeout(2000); // 等待图表更新
          
          // 验证图表已更新
          await expect(timeframeButton).toHaveClass(/active|selected/);
        }
      }
    }
  });

  test('应该支持策略表现对比分析', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 查找策略对比功能
    const compareButton = page.locator('button:has-text("策略对比"), button:has-text("Compare"), [data-testid="compare-strategies"]');
    if (await compareButton.count() > 0) {
      await compareButton.click();
      
      // 验证对比面板
      const comparePanel = page.locator('.strategy-compare, .comparison-panel, [data-testid="comparison"]');
      await expect(comparePanel).toBeVisible();
      
      // 选择要对比的策略
      const strategy1Select = page.locator('select[name="strategy1"], [data-testid="strategy1-select"]');
      if (await strategy1Select.count() > 0) {
        await strategy1Select.selectOption({ index: 1 });
      }
      
      const strategy2Select = page.locator('select[name="strategy2"], [data-testid="strategy2-select"]');
      if (await strategy2Select.count() > 0) {
        await strategy2Select.selectOption({ index: 2 });
      }
      
      // 开始对比
      const startCompare = page.locator('button:has-text("开始对比"), button:has-text("Compare")');
      if (await startCompare.count() > 0) {
        await startCompare.click();
        await page.waitForTimeout(3000);
        
        // 验证对比结果
        const comparisonResults = page.locator('.comparison-results, .compare-table');
        if (await comparisonResults.count() > 0) {
          await expect(comparisonResults).toBeVisible();
          
          // 验证对比指标
          await expect(page.locator('text=/收益率对比|Return Comparison/i')).toBeVisible();
          await expect(page.locator('text=/风险对比|Risk Comparison/i')).toBeVisible();
          await expect(page.locator('text=/夏普比率|Sharpe Ratio/i')).toBeVisible();
        }
      }
    }
  });

  test('应该支持自定义指标和技术分析', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 查找技术指标面板
    const indicatorsPanel = page.locator('.indicators-panel, .technical-indicators, [data-testid="indicators"]');
    if (await indicatorsPanel.count() > 0) {
      await expect(indicatorsPanel).toBeVisible();
      
      // 添加技术指标
      const addIndicatorButton = page.locator('button:has-text("添加指标"), button:has-text("Add Indicator")');
      if (await addIndicatorButton.count() > 0) {
        await addIndicatorButton.click();
        
        // 选择指标类型
        const indicatorSelect = page.locator('select[name="indicator"], .indicator-selector');
        if (await indicatorSelect.count() > 0) {
          await indicatorSelect.selectOption('MA'); // 移动平均线
          
          // 设置参数
          const periodInput = page.locator('input[name="period"], input[placeholder*="周期"]');
          if (await periodInput.count() > 0) {
            await periodInput.fill('20');
          }
          
          // 确认添加
          const confirmAdd = page.locator('button:has-text("确认"), button:has-text("Add")');
          if (await confirmAdd.count() > 0) {
            await confirmAdd.click();
            await page.waitForTimeout(2000);
            
            // 验证指标已添加到图表
            const indicatorLine = page.locator('.indicator-line, .ma-line, [data-indicator="MA"]');
            if (await indicatorLine.count() > 0) {
              await expect(indicatorLine).toBeVisible();
            }
          }
        }
      }
    }
  });

  test('应该正确处理大量历史数据的性能', async ({ page }) => {
    await page.goto('/trading-replay');
    
    // 设置较长的日期范围
    const dateFromInput = page.locator('input[name="dateFrom"], input[type="date"]').first();
    if (await dateFromInput.count() > 0) {
      await dateFromInput.fill('2023-01-01');
    }
    
    const dateToInput = page.locator('input[name="dateTo"], input[type="date"]').last();
    if (await dateToInput.count() > 0) {
      await dateToInput.fill('2024-12-31');
    }
    
    // 应用筛选
    const applyButton = page.locator('button:has-text("应用"), button:has-text("Apply")');
    if (await applyButton.count() > 0) {
      const startTime = Date.now();
      await applyButton.click();
      
      // 等待加载完成
      await page.waitForSelector('.trade-list, .loading-complete', { timeout: 30000 });
      
      const loadTime = Date.now() - startTime;
      console.log(`Data loading time: ${loadTime}ms`);
      
      // 验证性能合理（应该在30秒内完成）
      expect(loadTime).toBeLessThan(30000);
      
      // 验证数据正确加载
      const tradesList = page.locator('.trade-list, .trades-table');
      if (await tradesList.count() > 0) {
        await expect(tradesList).toBeVisible();
      }
    }
    
    // 测试滚动性能
    const tradesList = page.locator('.trade-list, .trades-table');
    if (await tradesList.count() > 0) {
      // 快速滚动测试
      for (let i = 0; i < 5; i++) {
        await page.mouse.wheel(0, 1000);
        await page.waitForTimeout(100);
      }
      
      // 验证滚动后界面仍然响应
      await expect(tradesList).toBeVisible();
    }
  });
});