module.exports = {
  // 测试环境
  testEnvironment: 'node',
  
  // 设置文件
  setupFilesAfterEnv: ['<rootDir>/tests/setup.js'],
  
  // 测试文件匹配模式
  testMatch: [
    '<rootDir>/tests/**/*.test.js',
    '<rootDir>/tests/**/*.spec.js'
  ],
  
  // 忽略的测试文件
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/build/',
    '/01MasterControl/',
    '/02DataCenter/',
    '/03ScanPulse/',
    '/04StrategyFactory/',
    '/08PerformanceMonitor/',
    '/09AlertSystem/',
    '/10DataAnalyzer/',
    '/11ReportGenerator/'
  ],

  // 忽略的模块路径
  modulePathIgnorePatterns: [
    '<rootDir>/01MasterControl/',
    '<rootDir>/02DataCenter/',
    '<rootDir>/03ScanPulse/',
    '<rootDir>/04StrategyFactory/',
    '<rootDir>/08PerformanceMonitor/',
    '<rootDir>/09AlertSystem/',
    '<rootDir>/10DataAnalyzer/',
    '<rootDir>/11ReportGenerator/'
  ],
  
  // 代码覆盖率配置
  collectCoverage: true,
  collectCoverageFrom: [
    'api/**/*.js',
    'src/**/*.js',
    '!api/**/index.js',
    '!src/**/index.js',
    '!**/node_modules/**',
    '!**/dist/**',
    '!**/build/**',
    '!**/coverage/**',
    '!**/tests/**',
    '!**/*.config.js',
    '!**/*.test.js',
    '!**/*.spec.js'
  ],
  
  // 覆盖率阈值
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  },
  
  // 覆盖率报告格式
  coverageReporters: [
    'text',
    'text-summary',
    'html',
    'lcov',
    'json'
  ],
  
  // 覆盖率输出目录
  coverageDirectory: 'coverage',
  
  // 模块文件扩展名
  moduleFileExtensions: ['js', 'json', 'node'],
  
  // 模块路径映射
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
    '^@api/(.*)$': '<rootDir>/api/$1'
  },
  
  // 转换配置
  transform: {
    '^.+\\.js$': 'babel-jest'
  },
  
  // 转换忽略模式
  transformIgnorePatterns: [
    'node_modules/(?!(zeromq|redis)/)',
    '\\.pnp\\.[^\\\/]+$'
  ],
  
  // 清除模拟
  clearMocks: true,
  
  // 恢复模拟
  restoreMocks: true,
  
  // 测试超时
  testTimeout: 30000,
  
  // 详细输出
  verbose: true,
  
  // 错误时退出
  bail: false,
  
  // 强制退出
  forceExit: true,
  
  // 检测打开的句柄
  detectOpenHandles: true,
  
  // 最大工作进程数
  maxWorkers: 1,
  
  // 报告器配置
  reporters: [
    'default',
    [
      'jest-html-reporters',
      {
        publicPath: './coverage/html-report',
        filename: 'report.html',
        expand: true,
        hideIcon: false,
        pageTitle: 'TradeGuard Test Report'
      }
    ]
  ]
};