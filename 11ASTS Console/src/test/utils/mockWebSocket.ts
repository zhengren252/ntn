/*
 * Mock WebSocket installer for Playwright addInitScript
 * Usage in tests:
 *   await page.addInitScript(mockWebSocketInit)
 */

// Exported function must be self-contained and serializable for addInitScript
export function mockWebSocketInit(): void {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const g: any = window as any;
  g.__WS_CONNECTED__ = false;
  g.__WS_MESSAGE_COUNT__ = 0;
  g.__WS_SOCKETS__ = [];

  class MockWebSocket {
    url: string;
    protocols?: string | string[];
    readyState: number;
    // 回调不再绑定 this: WebSocket，避免与 MockWebSocket 的 this 类型冲突
    onopen: ((ev: Event) => unknown) | null = null;
    onmessage: ((ev: MessageEvent) => unknown) | null = null;
    onclose: ((ev: CloseEvent) => unknown) | null = null;
    onerror: ((ev: Event) => unknown) | null = null;
    private _interval: number | null = null;

    static CONNECTING = 0;
    static OPEN = 1;
    static CLOSING = 2;
    static CLOSED = 3;

    constructor(url: string, protocols?: string | string[]) {
      this.url = url;
      this.protocols = protocols;
      this.readyState = MockWebSocket.CONNECTING;

      // Register to global for test-controlled message injection
      g.__WS_SOCKETS__.push(this);

      // Simulate connection established
      setTimeout(() => {
        this.readyState = MockWebSocket.OPEN;
        g.__WS_CONNECTED__ = true;
        // this.onopen && this.onopen(new Event('open'));
        if (this.onopen) { this.onopen(new Event('open')); }

        // Periodically push system update messages to drive UI updates
        this._interval = window.setInterval(() => {
          if (this.readyState !== MockWebSocket.OPEN) return;
          const message = {
            type: 'systemUpdate',
            data: { status: 'running', t: Date.now() },
            timestamp: Date.now()
          };
          g.__WS_MESSAGE_COUNT__++;
          // this.onmessage && this.onmessage(new MessageEvent('message', { data: JSON.stringify(message) }));
          if (this.onmessage) { this.onmessage(new MessageEvent('message', { data: JSON.stringify(message) })); }
        }, 2000);
      }, 50);
    }

    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    send(data: string) {
      // Handle heartbeat
      try {
        const payload = JSON.parse(data);
        if (payload.type === 'ping') {
          const pong = { type: 'pong', timestamp: Date.now() };
          // this.onmessage && this.onmessage(new MessageEvent('message', { data: JSON.stringify(pong) }));
          if (this.onmessage) { this.onmessage(new MessageEvent('message', { data: JSON.stringify(pong) })); }
        }
      } catch {
        // ignore
      }
    }

    close(code = 1000, reason = 'Mock close') {
      this.readyState = MockWebSocket.CLOSED;
      if (this._interval) {
        clearInterval(this._interval);
        this._interval = null;
      }
      // this.onclose && this.onclose(new CloseEvent('close', { wasClean: true, code, reason }));
      if (this.onclose) { this.onclose(new CloseEvent('close', { wasClean: true, code, reason })); }
    }
  }

  // Override global WebSocket
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).WebSocket = (MockWebSocket as unknown) as typeof WebSocket;

  // Proactively create a client to ensure messages are produced (even if app doesn't connect)
  setTimeout(() => {
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__WS_CLIENT__ = new (window as any).WebSocket('ws://localhost:8001/ws/system');
    } catch (e) {
      // 保留最后一次初始化错误，避免空块并便于排查
      (g as any).__WS_INIT_ERROR__ = e;
    }
  }, 0);
}