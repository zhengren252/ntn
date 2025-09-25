import { test, expect } from '@playwright/test';
import { mockWebSocketInit } from '../utils/mockWebSocket';
import { makeAIChatResponse, makeStrategyCodeResponse } from '../fixtures/ai-lab';

test.describe('UAT-FE-02: AI策略实验室交互体验', () => {
  test.beforeEach(async ({ page }) => {
    // 注入 WebSocket Mock
    await page.addInitScript(mockWebSocketInit);

    // Mock AI聊天API
    await page.route('**/api/ai/chat', async (route) => {
      const body = JSON.stringify(makeAIChatResponse());
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    // Mock策略代码生成API
    await page.route('**/api/ai/generate-strategy', async (route) => {
      const body = JSON.stringify(makeStrategyCodeResponse());
      await route.fulfill({ status: 200, contentType: 'application/json', body });
    });

    await page.goto('/');
  });

  test('应该能够与AI策略研究助理进行自然语言交互', async ({ page }) => {
    // 导航到AI策略实验室
    const aiLabLink = page.locator('nav').getByText('AI实验室', { exact: false });
    if (await aiLabLink.count() > 0) {
      await aiLabLink.click();
    } else {
      await page.goto('/ai-lab');
    }
    
    // 验证页面加载
    await expect(page).toHaveTitle(/AI|策略|实验室|Lab/i);
    
    // 验证AI助理界面
    const chatInterface = page.locator('.chat-interface, .ai-chat, [data-testid="ai-chat"]');
    await expect(chatInterface).toBeVisible({ timeout: 10000 });
    
    // 验证输入框
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await expect(messageInput).toBeVisible();
    await expect(messageInput).toBeEnabled();
    
    // 发送测试消息
    const testMessage = '请帮我分析一下当前市场趋势，并推荐一个适合的交易策略';
    await messageInput.fill(testMessage);
    
    // 点击发送按钮
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send"), [data-testid="send-button"]');
    await sendButton.click();
    
    // 验证消息已发送
    const userMessage = page.locator('.user-message, .message-user').last();
    await expect(userMessage).toContainText(testMessage);
    
    // 等待AI响应
    const aiResponse = page.locator('.ai-message, .message-ai, .assistant-message').last();
    await expect(aiResponse).toBeVisible({ timeout: 15000 });
    
    // 验证AI响应内容有价值
    const responseText = await aiResponse.textContent();
    expect(responseText).toBeTruthy();
    expect(responseText!.length).toBeGreaterThan(50); // 响应应该有实质内容
    
    // 验证响应包含策略相关内容
    expect(responseText).toMatch(/策略|交易|市场|分析|建议|Strategy|Trading|Market|Analysis/i);
  });

  test('应该能够生成和显示策略代码', async ({ page }) => {
    await page.goto('/ai-lab');
    
    // 等待界面加载
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    // 发送代码生成请求
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.fill('请生成一个基于移动平均线的交易策略代码');
    
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")');
    await sendButton.click();
    
    // 等待AI响应
    await page.waitForTimeout(5000);
    
    // 验证代码块显示
    const codeBlock = page.locator('pre, code, .code-block, .highlight');
    if (await codeBlock.count() > 0) {
      await expect(codeBlock.first()).toBeVisible();
      
      // 验证代码内容
      const codeText = await codeBlock.first().textContent();
      expect(codeText).toMatch(/def|function|class|import|return/i); // 应该包含代码关键字
    }
    
    // 验证代码编辑器
    const codeEditor = page.locator('.monaco-editor, .code-editor, [data-testid="code-editor"]');
    if (await codeEditor.count() > 0) {
      await expect(codeEditor).toBeVisible();
      
      // 验证编辑器功能
      await codeEditor.click();
      await page.keyboard.type('# 测试编辑功能');
      
      // 验证语法高亮
      const syntaxHighlight = page.locator('.token, .keyword, .string');
      if (await syntaxHighlight.count() > 0) {
        await expect(syntaxHighlight.first()).toBeVisible();
      }
    }
  });

  test('应该支持策略回测和性能分析', async ({ page }) => {
    await page.goto('/ai-lab');
    
    // 等待界面加载
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    // 请求策略回测
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.fill('请对刚才生成的策略进行回测分析');
    
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")');
    await sendButton.click();
    
    // 等待回测结果
    await page.waitForTimeout(8000);
    
    // 验证回测结果显示
    const backtestResults = page.locator('.backtest-results, .performance-metrics, [data-testid="backtest-results"]');
    if (await backtestResults.count() > 0) {
      await expect(backtestResults).toBeVisible();
      
      // 验证关键指标
      await expect(page.locator('text=/收益率|Return/i')).toBeVisible();
      await expect(page.locator('text=/夏普比率|Sharpe/i')).toBeVisible();
      await expect(page.locator('text=/最大回撤|Drawdown/i')).toBeVisible();
      await expect(page.locator('text=/胜率|Win Rate/i')).toBeVisible();
    }
    
    // 验证性能图表
    const performanceChart = page.locator('.performance-chart, canvas, svg');
    if (await performanceChart.count() > 0) {
      await expect(performanceChart.first()).toBeVisible();
    }
    
    // 验证详细分析报告
    const analysisReport = page.locator('.analysis-report, .detailed-analysis');
    if (await analysisReport.count() > 0) {
      await expect(analysisReport).toBeVisible();
      
      const reportText = await analysisReport.textContent();
      expect(reportText).toMatch(/分析|评估|建议|风险|Analysis|Assessment|Risk/i);
    }
  });

  test('应该支持多轮对话和上下文理解', async ({ page }) => {
    await page.goto('/ai-lab');
    
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    const messageInput = page.locator('textarea, input[type="text"]').last();
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")');
    
    // 第一轮对话
    await messageInput.fill('我想开发一个量化交易策略');
    await sendButton.click();
    await page.waitForTimeout(3000);
    
    // 第二轮对话（测试上下文理解）
    await messageInput.fill('这个策略应该关注哪些技术指标？');
    await sendButton.click();
    await page.waitForTimeout(3000);
    
    // 第三轮对话（进一步细化）
    await messageInput.fill('请详细解释RSI指标的使用方法');
    await sendButton.click();
    await page.waitForTimeout(3000);
    
    // 验证对话历史
    const messageHistory = page.locator('.message, .chat-message');
    await expect(messageHistory).toHaveCount(6); // 3条用户消息 + 3条AI响应
    
    // 验证最后的响应与RSI相关
    const lastAiMessage = page.locator('.ai-message, .message-ai').last();
    const lastResponseText = await lastAiMessage.textContent();
    expect(lastResponseText).toMatch(/RSI|相对强弱|超买|超卖|Relative Strength/i);
  });

  test('应该支持策略模板和预设场景', async ({ page }) => {
    await page.goto('/ai-lab');
    
    // 查找策略模板区域
    const templateSection = page.locator('.strategy-templates, .templates, [data-testid="templates"]');
    if (await templateSection.count() > 0) {
      await expect(templateSection).toBeVisible();
      
      // 验证模板选项
      const templateOptions = page.locator('.template-item, .template-card');
      if (await templateOptions.count() > 0) {
        await expect(templateOptions.first()).toBeVisible();
        
        // 点击第一个模板
        await templateOptions.first().click();
        
        // 验证模板加载
        await page.waitForTimeout(2000);
        
        // 验证代码编辑器中有模板代码
        const codeEditor = page.locator('.monaco-editor, .code-editor');
        if (await codeEditor.count() > 0) {
          const editorContent = await codeEditor.textContent();
          expect(editorContent).toBeTruthy();
          expect(editorContent!.length).toBeGreaterThan(100);
        }
      }
    }
    
    // 验证预设场景
    const scenarioSelector = page.locator('.scenario-selector, select[name="scenario"]');
    if (await scenarioSelector.count() > 0) {
      await expect(scenarioSelector).toBeVisible();
      
      // 选择一个场景
      await scenarioSelector.selectOption({ index: 1 });
      await page.waitForTimeout(1000);
      
      // 验证场景描述
      const scenarioDescription = page.locator('.scenario-description, .scenario-info');
      if (await scenarioDescription.count() > 0) {
        await expect(scenarioDescription).toBeVisible();
      }
    }
  });

  test('应该支持策略保存和管理', async ({ page }) => {
    await page.goto('/ai-lab');
    
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    // 生成一个策略
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.fill('生成一个简单的均线交叉策略');
    
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")');
    await sendButton.click();
    await page.waitForTimeout(5000);
    
    // 查找保存按钮
    const saveButton = page.locator('button:has-text("保存"), button:has-text("Save"), [data-testid="save-strategy"]');
    if (await saveButton.count() > 0) {
      await saveButton.click();
      
      // 填写策略名称
      const nameInput = page.locator('input[name="strategyName"], input[placeholder*="名称"]');
      if (await nameInput.count() > 0) {
        await nameInput.fill('测试均线策略');
      }
      
      // 确认保存
      const confirmSave = page.locator('button:has-text("确认"), button:has-text("保存")');
      if (await confirmSave.count() > 0) {
        await confirmSave.click();
      }
      
      // 验证保存成功消息
      const successMessage = page.locator('.toast, .notification, .alert-success');
      await expect(successMessage).toBeVisible({ timeout: 5000 });
      await expect(successMessage).toContainText(/保存成功|已保存|Saved/i);
    }
    
    // 验证策略列表
    const strategyList = page.locator('.strategy-list, .saved-strategies, [data-testid="strategy-list"]');
    if (await strategyList.count() > 0) {
      await expect(strategyList).toBeVisible();
      
      // 验证刚保存的策略出现在列表中
      await expect(page.locator('text=测试均线策略')).toBeVisible();
    }
  });

  test('应该正确处理AI服务异常情况', async ({ page }) => {
    // 模拟AI服务错误
    await page.route('**/api/ai/**', route => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'AI service unavailable',
          message: 'AI服务暂时不可用，请稍后重试'
        })
      });
    });
    
    await page.goto('/ai-lab');
    
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    // 尝试发送消息
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.fill('测试AI服务错误处理');
    
    const sendButton = page.locator('button:has-text("发送"), button:has-text("Send")');
    await sendButton.click();
    
    // 验证错误消息显示
    const errorMessage = page.locator('.error-message, .ai-error, [data-testid="error-message"]');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    // 只检查p标签内的错误文本，避免包含按钮文本
    const errorText = errorMessage.locator('p');
    await expect(errorText).toContainText(/不可用|错误|失败|unavailable|error/i);
    
    // 验证重试按钮
    const retryButton = page.locator('button:has-text("重试"), button:has-text("Retry")');
    if (await retryButton.count() > 0) {
      await expect(retryButton).toBeVisible();
      await expect(retryButton).toBeEnabled();
    }
  });

  test('应该支持代码语法检查和错误提示', async ({ page }) => {
    await page.goto('/ai-lab');
    
    // 等待代码编辑器加载
    const codeEditor = page.locator('.monaco-editor, .code-editor, [data-testid="code-editor"]');
    if (await codeEditor.count() > 0) {
      await expect(codeEditor).toBeVisible();
      
      // 输入有语法错误的代码
      await codeEditor.click();
      await page.keyboard.press('Control+A');
      await page.keyboard.type(`
def invalid_strategy(
    # 缺少闭合括号
    return "error"
`);
      
      // 等待语法检查
      await page.waitForTimeout(2000);
      
      // 验证错误提示
      const errorIndicator = page.locator('.error-marker, .syntax-error, .squiggly-error');
      if (await errorIndicator.count() > 0) {
        await expect(errorIndicator.first()).toBeVisible();
      }
      
      // 验证错误面板
      const errorPanel = page.locator('.error-panel, .problems-panel');
      if (await errorPanel.count() > 0) {
        await expect(errorPanel).toBeVisible();
        
        const errorText = await errorPanel.textContent();
        expect(errorText).toMatch(/语法错误|syntax error|invalid/i);
      }
    }
  });

  test('应该支持快捷键和键盘操作', async ({ page }) => {
    await page.goto('/ai-lab');
    
    await page.waitForSelector('.chat-interface, .ai-chat', { timeout: 10000 });
    
    const messageInput = page.locator('textarea, input[type="text"]').last();
    await messageInput.focus();
    
    // 测试Enter发送消息
    await messageInput.fill('测试快捷键功能');
    await page.keyboard.press('Enter');
    
    // 验证消息已发送
    await expect(page.locator('.user-message, .message-user').last()).toContainText('测试快捷键功能');
    
    // 测试代码编辑器快捷键
    const codeEditor = page.locator('.monaco-editor, .code-editor');
    if (await codeEditor.count() > 0) {
      await codeEditor.click();
      
      // 测试Ctrl+A全选
      await page.keyboard.press('Control+A');
      await page.keyboard.type('print("hello world")');
      
      // 测试Ctrl+Z撤销
      await page.keyboard.press('Control+Z');
      
      // 测试Ctrl+S保存（如果支持）
      await page.keyboard.press('Control+S');
    }
  });
});