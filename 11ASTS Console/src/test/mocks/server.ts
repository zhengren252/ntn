import { setupServer } from 'msw/node'
import { handlers } from './handlers'

// 设置MSW server用于Node.js测试环境
export const server = setupServer(...handlers)