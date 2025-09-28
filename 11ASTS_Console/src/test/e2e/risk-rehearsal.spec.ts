import { test, expect } from '@playwright/test';
import { mockWebSocketInit } from '../utils/mockWebSocket';
import { makeRehearsalScenariosResponse, makeRehearsalStartResponse, makeRehearsalStatusResponse } from '../fixtures/risk-rehearsal';

test.describe('E2E-FE-RISK-REHEARSAL-01: 风控演习流程', () => {
  test.beforeEach(async ({ page }) => {
    // 注入 WebSocket Mock
    await page.addInitScript(mockWebSocketInit);

    // Mock演习场景列表API
    await page.route('**/api/risk/scenarios', async (route) => {
      const body = JSON.stringify(makeRehearsalScenariosResponse());
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    // Mock演习启动API
    await page.route('**/api/risk/rehearsal/start', async (route) => {
      const body = JSON.stringify(makeRehearsalStartResponse());
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    // Mock演习状态查询API
    await page.route('**/api/risk/rehearsal/status/*', async (route) => {
      const url = route.request().url();
      const rehearsalId = url.split('/').pop() || 'rehearsal_001';
      const body = JSON.stringify(makeRehearsalStatusResponse(rehearsalId, 45));
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    await page.goto('/');
  });

  test('应该能够成功配置并启动风控演习', async ({ page }) => {
    // 步骤1: 导航到风控演习中心
    await page.goto('/');
    
    // 查找并点击风控演习导航链接
    const riskLink = page.locator('nav').getByText('风控演习', { exact: false });
    if (await riskLink.count() > 0) {
      await riskLink.click();
    } else {
      // 如果没有找到导航链接，尝试其他可能的名称
      const rehearsalLink = page.locator('nav').getByText('演习', { exact: false });
      if (await rehearsalLink.count() > 0) {
        await rehearsalLink.click();
      } else {
        // 直接访问风控演习页面
        await page.goto('/risk-rehearsal');
      }
    }

    // 验证页面标题
    await expect(page).toHaveTitle(/风控|演习|Risk|Rehearsal/i);
    
    // 步骤2: 验证风控演习中心页面加载
    await page.waitForSelector('[data-testid="risk-rehearsal-form"], .rehearsal-form, form', { timeout: 10000 });
    
    // 验证页面关键元素
    await expect(page.locator('h1, h2')).toContainText(/风控演习|Risk Rehearsal/i);
    
    // 步骤3: 选择极端行情场景
    const scenarioSelect = page.locator('select[name="scenario"], [data-testid="scenario-select"]');
    if (await scenarioSelect.count() > 0) {
      await scenarioSelect.selectOption({ label: '519闪崩' });
    } else {
      // 如果是单选按钮或其他形式
      const crashScenario = page.locator('input[value*="519"], label:has-text("519闪崩"), button:has-text("519闪崩")');
      if (await crashScenario.count() > 0) {
        await crashScenario.click();
      }
    }
    
    // 步骤4: 配置演习参数（如果有的话）
    const durationInput = page.locator('input[name="duration"], [data-testid="duration-input"]');
    if (await durationInput.count() > 0) {
      await durationInput.fill('30'); // 30分钟演习
    }
    
    const intensitySelect = page.locator('select[name="intensity"], [data-testid="intensity-select"]');
    if (await intensitySelect.count() > 0) {
      await intensitySelect.selectOption('high');
    }
    
    // 步骤5: 启动演习
    const startButton = page.locator('button:has-text("启动演习"), button:has-text("开始"), [data-testid="start-rehearsal-button"]');
    await expect(startButton).toBeVisible();
    await expect(startButton).toBeEnabled();
    await startButton.click();
    
    // 步骤6: 处理确认对话框
    const confirmDialog = page.locator('.dialog, .modal, [role="dialog"]');
    if (await confirmDialog.count() > 0) {
      await expect(confirmDialog).toContainText(/确认|启动|演习/i);
      
      const confirmButton = confirmDialog.locator('button:has-text("确认"), button:has-text("启动"), button:has-text("是")');
      await confirmButton.click();
    }
    
    // 步骤7: 验证演习启动成功
    // 等待成功消息
    const successMessage = page.locator('.toast, .notification, .alert-success, [data-testid="success-message"]');
    await expect(successMessage).toBeVisible({ timeout: 10000 });
    await expect(successMessage).toContainText(/启动|成功|演习/i);
    
    // 步骤8: 验证演习状态显示
    // 检查演习状态指示器
    const statusIndicator = page.locator('.rehearsal-status, [data-testid="rehearsal-status"], .status-badge');
    if (await statusIndicator.count() > 0) {
      await expect(statusIndicator).toBeVisible();
      await expect(statusIndicator).toContainText(/进行中|运行|Running|Active/i);
    }
    
    // 验证演习控制面板
    const controlPanel = page.locator('.rehearsal-controls, [data-testid="rehearsal-controls"]');
    if (await controlPanel.count() > 0) {
      await expect(controlPanel).toBeVisible();
      
      // 验证停止按钮可用
      const stopButton = controlPanel.locator('button:has-text("停止"), button:has-text("结束"), button:has-text("Stop")');
      if (await stopButton.count() > 0) {
        await expect(stopButton).toBeVisible();
        await expect(stopButton).toBeEnabled();
      }
    }
  });

  test('应该能够监控演习进度和实时数据', async ({ page }) => {
    // 先启动一个演习
    await page.goto('/risk-rehearsal');
    
    // 快速启动演习
    const startButton = page.locator('button:has-text("启动演习"), button:has-text("开始")');
    if (await startButton.count() > 0) {
      await startButton.click();
      
      // 处理确认对话框
      const confirmButton = page.locator('.dialog button:has-text("确认启动"), .modal button:has-text("确认启动")');
      if (await confirmButton.count() > 0) {
        await confirmButton.click();
      }
    }
    
    // 验证实时监控面板
    const monitoringPanel = page.locator('.monitoring-panel, [data-testid="monitoring-panel"], .real-time-data');
    if (await monitoringPanel.count() > 0) {
      await expect(monitoringPanel).toBeVisible();
      
      // 验证关键指标显示
      await expect(page.locator('text=/市场数据|Market Data/i')).toBeVisible();
      await expect(page.locator('text=/风险指标|Risk Metrics/i')).toBeVisible();
      await expect(page.locator('text=/系统状态|System Status/i')).toBeVisible();
    }
    
    // 验证图表显示
    const charts = page.locator('.chart, canvas, svg');
    if (await charts.count() > 0) {
      await expect(charts.first()).toBeVisible();
    }
    
    // 验证数据更新（等待几秒钟观察数据变化）
    await page.waitForTimeout(3000);
    
    // 验证时间戳更新
    const timestamp = page.locator('.timestamp, [data-testid="last-update"]');
    if (await timestamp.count() > 0) {
      await expect(timestamp).toBeVisible();
    }
  });

  test('应该能够停止正在进行的演习', async ({ page }) => {
    await page.goto('/risk-rehearsal');
    
    // 启动演习
    const startButton = page.locator('button:has-text("启动演习"), button:has-text("开始")');
    if (await startButton.count() > 0) {
      await startButton.click();
      
      const confirmButton = page.locator('.dialog button:has-text("确认启动"), .modal button:has-text("确认启动")');
      if (await confirmButton.count() > 0) {
        await confirmButton.click();
      }
      
      // 等待演习启动
      await page.waitForTimeout(2000);
    }
    
    // 点击停止按钮
    const stopButton = page.locator('button:has-text("停止"), button:has-text("结束"), button:has-text("Stop")');
    await expect(stopButton).toBeVisible();
    await stopButton.click();
    
    // 处理停止确认
    const confirmDialog = page.locator('.dialog, .modal, [role="dialog"]');
    if (await confirmDialog.count() > 0) {
      const confirmButton = confirmDialog.locator('button:has-text("确认"), button:has-text("停止")');
      await confirmButton.click();
    }
    
    // 验证演习已停止
    const successMessage = page.locator('.toast, .notification, .alert-success');
    await expect(successMessage).toBeVisible({ timeout: 5000 });
    await expect(successMessage).toContainText(/停止|结束|已停止/i);
    
    // 验证状态更新
    const statusIndicator = page.locator('.rehearsal-status, [data-testid="rehearsal-status"]');
    if (await statusIndicator.count() > 0) {
      await expect(statusIndicator).toContainText(/已停止|停止|Stopped/i);
    }
  });

  test('应该正确处理演习启动失败的情况', async ({ page }) => {
    // 模拟API错误
    await page.route('**/api/risk/rehearsal/start', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'System busy',
          message: '系统繁忙，无法启动演习，请稍后重试'
        })
      });
    });
    
    await page.goto('/risk-rehearsal');
    
    // 尝试启动演习
    const startButton = page.locator('button:has-text("启动演习"), button:has-text("开始")');
    await startButton.click();
    
    // 处理确认对话框
    const confirmButton = page.locator('.dialog button:has-text("确认启动"), .modal button:has-text("确认启动")');
    if (await confirmButton.count() > 0) {
      await confirmButton.click();
    }
    
    // 验证错误消息显示
    const errorMessage = page.locator('.toast, .notification, .alert-error, [data-testid="error-message"]');
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    await expect(errorMessage).toContainText(/失败|错误|繁忙/i);
    
    // 验证按钮状态恢复
    await expect(startButton).toBeEnabled();
  });

  test('应该能够查看演习历史记录', async ({ page }) => {
    await page.goto('/risk-rehearsal');
    
    // 查找历史记录标签或按钮
    const historyTab = page.locator('button:has-text("历史"), tab:has-text("历史"), [data-testid="history-tab"]');
    if (await historyTab.count() > 0) {
      await historyTab.click();
      
      // 验证历史记录列表
      const historyList = page.locator('.history-list, [data-testid="rehearsal-history"], table');
      await expect(historyList).toBeVisible();
      
      // 验证历史记录项
      const historyItems = page.locator('.history-item, tbody tr');
      if (await historyItems.count() > 0) {
        await expect(historyItems.first()).toBeVisible();
        
        // 验证关键信息显示
        await expect(page.locator('text=/开始时间|Start Time/i')).toBeVisible();
        await expect(page.locator('text=/场景|Scenario/i')).toBeVisible();
        await expect(page.locator('text=/状态|Status/i')).toBeVisible();
      }
    }
  });
});