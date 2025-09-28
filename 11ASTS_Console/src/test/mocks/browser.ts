import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

// 设置MSW worker用于浏览器环境
export const worker = setupWorker(...handlers)