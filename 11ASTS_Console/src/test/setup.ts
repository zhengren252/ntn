import '@testing-library/jest-dom';
import { server } from './mocks/server';
import { beforeAll, afterEach, afterAll } from 'vitest';

// 启动MSW服务器
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// 每个测试后重置处理器
afterEach(() => server.resetHandlers());

// 测试完成后关闭服务器
afterAll(() => server.close());

// Mock IntersectionObserver（使用 defineProperty 避免对只读 prototype 赋值）
class MockIntersectionObserver {
  // 构造函数：保存回调与选项但不执行实际观测
  constructor(callback: IntersectionObserverCallback, options?: IntersectionObserverInit) {
    // noop in test environment
  }
  // 断开观察
  disconnect() {}
  // 开始观察
  observe(_target: Element) {}
  // 停止观察
  unobserve(_target: Element) {}
  // 取回未处理的观测条目
  takeRecords(): IntersectionObserverEntry[] { return []; }
  // 只读属性
  readonly root: Element | Document | null = null;
  readonly rootMargin: string = '0px';
  readonly thresholds: ReadonlyArray<number> = [];
}

// 通过 defineProperty 定义全局 IntersectionObserver，避免触碰只读 prototype
Object.defineProperty(window as any, 'IntersectionObserver', {
  configurable: true,
  writable: true,
  value: MockIntersectionObserver as any,
});
Object.defineProperty(global as any, 'IntersectionObserver', {
  configurable: true,
  writable: true,
  value: MockIntersectionObserver as any,
});

// Mock ResizeObserver
(global as any).ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});