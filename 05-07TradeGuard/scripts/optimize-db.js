#!/usr/bin/env node
/**
 * 数据库性能优化脚本
 * 用于交易执行铁三角项目的数据库索引优化和查询性能提升
 */

const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { performance } = require('perf_hooks');

// 配置
const config = {
  development: {
    database: './data/development.db',
    type: 'sqlite'
  },
  staging: {
    database: './data/staging.db',
    type: 'sqlite'
  },
  production: {
    database: './data/production.db',
    type: 'sqlite'
  }
};

// 性能优化SQL语句
const optimizations = {
  // 创建索引
  indexes: [
    // 策略包表索引
    'CREATE INDEX IF NOT EXISTS idx_strategy_packages_status ON strategy_packages(status)',
    'CREATE INDEX IF NOT EXISTS idx_strategy_packages_created_at ON strategy_packages(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_strategy_packages_trader_id ON strategy_packages(trader_id)',
    'CREATE INDEX IF NOT EXISTS idx_strategy_packages_symbol ON strategy_packages(symbol)',
    
    // 订单表索引
    'CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)',
    'CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_orders_strategy_id ON orders(strategy_package_id)',
    'CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol)',
    'CREATE INDEX IF NOT EXISTS idx_orders_trader_id ON orders(trader_id)',
    'CREATE INDEX IF NOT EXISTS idx_orders_price ON orders(price)',
    'CREATE INDEX IF NOT EXISTS idx_orders_quantity ON orders(quantity)',
    
    // 风险评估表索引
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_status ON risk_assessments(status)',
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_created_at ON risk_assessments(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_strategy_id ON risk_assessments(strategy_package_id)',
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_level ON risk_assessments(risk_level)',
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_risk_score ON risk_assessments(risk_score)',
    
    // 风险告警表索引
    'CREATE INDEX IF NOT EXISTS idx_risk_alerts_status ON risk_alerts(status)',
    'CREATE INDEX IF NOT EXISTS idx_risk_alerts_created_at ON risk_alerts(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_risk_alerts_alert_type ON risk_alerts(alert_type)',
    'CREATE INDEX IF NOT EXISTS idx_risk_alerts_severity ON risk_alerts(severity)',
    
    // 预算申请表索引
    'CREATE INDEX IF NOT EXISTS idx_budget_requests_status ON budget_requests(status)',
    'CREATE INDEX IF NOT EXISTS idx_budget_requests_created_at ON budget_requests(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_budget_requests_trader_id ON budget_requests(trader_id)',
    'CREATE INDEX IF NOT EXISTS idx_budget_requests_amount ON budget_requests(amount)',
    
    // 资金分配表索引
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_status ON fund_allocations(status)',
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_created_at ON fund_allocations(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_budget_id ON fund_allocations(budget_request_id)',
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_account_id ON fund_allocations(account_id)',
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_amount ON fund_allocations(allocated_amount)',
    
    // 账户表索引
    'CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)',
    'CREATE INDEX IF NOT EXISTS idx_accounts_account_type ON accounts(account_type)',
    'CREATE INDEX IF NOT EXISTS idx_accounts_balance ON accounts(balance)',
    
    // 交易记录表索引
    'CREATE INDEX IF NOT EXISTS idx_trade_records_created_at ON trade_records(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_account_id ON trade_records(account_id)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_order_id ON trade_records(order_id)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_symbol ON trade_records(symbol)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_trade_type ON trade_records(trade_type)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_amount ON trade_records(amount)',
    
    // 审计日志表索引
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at)',
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)',
    'CREATE INDEX IF NOT EXISTS idx_audit_logs_table_name ON audit_logs(table_name)',
    
    // 复合索引
    'CREATE INDEX IF NOT EXISTS idx_orders_status_created ON orders(status, created_at)',
    'CREATE INDEX IF NOT EXISTS idx_orders_trader_symbol ON orders(trader_id, symbol)',
    'CREATE INDEX IF NOT EXISTS idx_risk_assessments_level_score ON risk_assessments(risk_level, risk_score)',
    'CREATE INDEX IF NOT EXISTS idx_trade_records_account_date ON trade_records(account_id, created_at)',
    'CREATE INDEX IF NOT EXISTS idx_fund_allocations_budget_status ON fund_allocations(budget_request_id, status)'
  ],
  
  // SQLite性能优化设置
  pragmas: [
    'PRAGMA journal_mode = WAL',           // 启用WAL模式
    'PRAGMA synchronous = NORMAL',         // 平衡性能和安全性
    'PRAGMA cache_size = 10000',           // 增加缓存大小
    'PRAGMA temp_store = memory',          // 临时表存储在内存
    'PRAGMA mmap_size = 268435456',        // 启用内存映射(256MB)
    'PRAGMA optimize'                      // 优化查询计划
  ],
  
  // 查询优化视图
  views: [
    // 活跃订单视图
    `CREATE VIEW IF NOT EXISTS active_orders AS
     SELECT o.*, sp.name as strategy_name, sp.symbol as strategy_symbol
     FROM orders o
     JOIN strategy_packages sp ON o.strategy_package_id = sp.id
     WHERE o.status IN ('pending', 'partial_filled')`,
    
    // 风险汇总视图
    `CREATE VIEW IF NOT EXISTS risk_summary AS
     SELECT 
       DATE(created_at) as date,
       risk_level,
       COUNT(*) as count,
       AVG(risk_score) as avg_score,
       MAX(risk_score) as max_score
     FROM risk_assessments
     GROUP BY DATE(created_at), risk_level`,
    
    // 交易统计视图
    `CREATE VIEW IF NOT EXISTS trade_statistics AS
     SELECT 
       DATE(created_at) as date,
       symbol,
       trade_type,
       COUNT(*) as trade_count,
       SUM(amount) as total_amount,
       AVG(price) as avg_price
     FROM trade_records
     GROUP BY DATE(created_at), symbol, trade_type`,
    
    // 账户余额汇总视图
    `CREATE VIEW IF NOT EXISTS account_summary AS
     SELECT 
       account_type,
       COUNT(*) as account_count,
       SUM(balance) as total_balance,
       AVG(balance) as avg_balance,
       MIN(balance) as min_balance,
       MAX(balance) as max_balance
     FROM accounts
     WHERE status = 'active'
     GROUP BY account_type`
  ]
};

// 性能测试查询
const performanceTests = [
  {
    name: '订单查询性能测试',
    query: `SELECT COUNT(*) FROM orders WHERE status = 'pending' AND created_at > datetime('now', '-1 day')`,
    expectedTime: 100 // 毫秒
  },
  {
    name: '风险评估查询性能测试',
    query: `SELECT * FROM risk_assessments WHERE risk_level = 'high' ORDER BY created_at DESC LIMIT 10`,
    expectedTime: 50
  },
  {
    name: '交易记录聚合查询性能测试',
    query: `SELECT symbol, SUM(amount) as total FROM trade_records WHERE created_at > datetime('now', '-7 days') GROUP BY symbol`,
    expectedTime: 200
  },
  {
    name: '复杂关联查询性能测试',
    query: `
      SELECT o.id, o.symbol, o.quantity, sp.name, ra.risk_score
      FROM orders o
      JOIN strategy_packages sp ON o.strategy_package_id = sp.id
      LEFT JOIN risk_assessments ra ON ra.strategy_package_id = sp.id
      WHERE o.status = 'pending' AND sp.status = 'active'
      ORDER BY ra.risk_score DESC
      LIMIT 20
    `,
    expectedTime: 300
  }
];

class DatabaseOptimizer {
  constructor(environment = 'development') {
    this.environment = environment;
    this.config = config[environment];
    this.db = null;
    this.results = {
      indexes: [],
      pragmas: [],
      views: [],
      performance: []
    };
  }

  // 连接数据库
  async connect() {
    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(this.config.database, (err) => {
        if (err) {
          reject(err);
        } else {
          console.log(`✅ 已连接到数据库: ${this.config.database}`);
          resolve();
        }
      });
    });
  }

  // 关闭数据库连接
  async close() {
    return new Promise((resolve) => {
      if (this.db) {
        this.db.close((err) => {
          if (err) {
            console.error('❌ 关闭数据库连接失败:', err.message);
          } else {
            console.log('✅ 数据库连接已关闭');
          }
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  // 执行SQL语句
  async runSQL(sql) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, (err) => {
        if (err) {
          reject(err);
        } else {
          resolve();
        }
      });
    });
  }

  // 执行查询
  async querySQL(sql) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  // 创建索引
  async createIndexes() {
    console.log('\n🔧 开始创建数据库索引...');
    
    for (const indexSQL of optimizations.indexes) {
      try {
        const start = performance.now();
        await this.runSQL(indexSQL);
        const end = performance.now();
        
        const indexName = indexSQL.match(/CREATE INDEX IF NOT EXISTS (\w+)/)[1];
        this.results.indexes.push({
          name: indexName,
          sql: indexSQL,
          time: Math.round(end - start),
          status: 'success'
        });
        
        console.log(`  ✅ 索引创建成功: ${indexName} (${Math.round(end - start)}ms)`);
      } catch (error) {
        const indexName = indexSQL.match(/CREATE INDEX IF NOT EXISTS (\w+)/)?.[1] || 'unknown';
        this.results.indexes.push({
          name: indexName,
          sql: indexSQL,
          error: error.message,
          status: 'failed'
        });
        
        console.log(`  ❌ 索引创建失败: ${indexName} - ${error.message}`);
      }
    }
  }

  // 应用性能优化设置
  async applyPragmas() {
    console.log('\n⚙️ 应用性能优化设置...');
    
    for (const pragmaSQL of optimizations.pragmas) {
      try {
        const start = performance.now();
        await this.runSQL(pragmaSQL);
        const end = performance.now();
        
        this.results.pragmas.push({
          sql: pragmaSQL,
          time: Math.round(end - start),
          status: 'success'
        });
        
        console.log(`  ✅ 设置应用成功: ${pragmaSQL} (${Math.round(end - start)}ms)`);
      } catch (error) {
        this.results.pragmas.push({
          sql: pragmaSQL,
          error: error.message,
          status: 'failed'
        });
        
        console.log(`  ❌ 设置应用失败: ${pragmaSQL} - ${error.message}`);
      }
    }
  }

  // 创建优化视图
  async createViews() {
    console.log('\n📊 创建优化视图...');
    
    for (const viewSQL of optimizations.views) {
      try {
        const start = performance.now();
        await this.runSQL(viewSQL);
        const end = performance.now();
        
        const viewName = viewSQL.match(/CREATE VIEW IF NOT EXISTS (\w+)/)[1];
        this.results.views.push({
          name: viewName,
          sql: viewSQL,
          time: Math.round(end - start),
          status: 'success'
        });
        
        console.log(`  ✅ 视图创建成功: ${viewName} (${Math.round(end - start)}ms)`);
      } catch (error) {
        const viewName = viewSQL.match(/CREATE VIEW IF NOT EXISTS (\w+)/)?.[1] || 'unknown';
        this.results.views.push({
          name: viewName,
          sql: viewSQL,
          error: error.message,
          status: 'failed'
        });
        
        console.log(`  ❌ 视图创建失败: ${viewName} - ${error.message}`);
      }
    }
  }

  // 性能测试
  async runPerformanceTests() {
    console.log('\n🚀 运行性能测试...');
    
    for (const test of performanceTests) {
      try {
        const start = performance.now();
        const result = await this.querySQL(test.query);
        const end = performance.now();
        const actualTime = Math.round(end - start);
        
        const passed = actualTime <= test.expectedTime;
        this.results.performance.push({
          name: test.name,
          query: test.query,
          expectedTime: test.expectedTime,
          actualTime: actualTime,
          resultCount: result.length,
          passed: passed,
          status: 'success'
        });
        
        const status = passed ? '✅' : '⚠️';
        console.log(`  ${status} ${test.name}: ${actualTime}ms (期望: ${test.expectedTime}ms)`);
        
        if (!passed) {
          console.log(`    警告: 查询时间超出预期 ${actualTime - test.expectedTime}ms`);
        }
      } catch (error) {
        this.results.performance.push({
          name: test.name,
          query: test.query,
          error: error.message,
          status: 'failed'
        });
        
        console.log(`  ❌ ${test.name}: 测试失败 - ${error.message}`);
      }
    }
  }

  // 分析数据库统计信息
  async analyzeDatabase() {
    console.log('\n📈 分析数据库统计信息...');
    
    try {
      // 表大小统计
      const tables = await this.querySQL(`
        SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
      `);
      
      console.log('\n📋 表统计信息:');
      for (const table of tables) {
        try {
          const count = await this.querySQL(`SELECT COUNT(*) as count FROM ${table.name}`);
          console.log(`  ${table.name}: ${count[0].count} 行`);
        } catch (error) {
          console.log(`  ${table.name}: 无法获取行数 - ${error.message}`);
        }
      }
      
      // 索引统计
      const indexes = await this.querySQL(`
        SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'
      `);
      
      console.log('\n🔍 索引统计信息:');
      const indexByTable = {};
      indexes.forEach(index => {
        if (!indexByTable[index.tbl_name]) {
          indexByTable[index.tbl_name] = [];
        }
        indexByTable[index.tbl_name].push(index.name);
      });
      
      Object.keys(indexByTable).forEach(table => {
        console.log(`  ${table}: ${indexByTable[table].length} 个索引`);
        indexByTable[table].forEach(index => {
          console.log(`    - ${index}`);
        });
      });
      
      // 数据库大小
      const dbStats = await this.querySQL('PRAGMA page_count, page_size');
      if (dbStats.length > 0) {
        const pageCount = dbStats[0].page_count || 0;
        const pageSize = dbStats[0].page_size || 0;
        const dbSize = (pageCount * pageSize / 1024 / 1024).toFixed(2);
        console.log(`\n💾 数据库大小: ${dbSize} MB`);
      }
      
    } catch (error) {
      console.log(`❌ 数据库分析失败: ${error.message}`);
    }
  }

  // 生成优化报告
  generateReport() {
    console.log('\n📊 生成优化报告...');
    
    const report = {
      timestamp: new Date().toISOString(),
      environment: this.environment,
      database: this.config.database,
      summary: {
        indexes: {
          total: this.results.indexes.length,
          success: this.results.indexes.filter(i => i.status === 'success').length,
          failed: this.results.indexes.filter(i => i.status === 'failed').length
        },
        pragmas: {
          total: this.results.pragmas.length,
          success: this.results.pragmas.filter(p => p.status === 'success').length,
          failed: this.results.pragmas.filter(p => p.status === 'failed').length
        },
        views: {
          total: this.results.views.length,
          success: this.results.views.filter(v => v.status === 'success').length,
          failed: this.results.views.filter(v => v.status === 'failed').length
        },
        performance: {
          total: this.results.performance.length,
          passed: this.results.performance.filter(p => p.passed).length,
          failed: this.results.performance.filter(p => p.status === 'failed').length
        }
      },
      details: this.results
    };
    
    // 保存报告
    const reportPath = path.join(__dirname, '..', 'reports', `db-optimization-${this.environment}-${Date.now()}.json`);
    
    // 确保报告目录存在
    const reportDir = path.dirname(reportPath);
    if (!fs.existsSync(reportDir)) {
      fs.mkdirSync(reportDir, { recursive: true });
    }
    
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
    console.log(`📄 优化报告已保存: ${reportPath}`);
    
    // 打印摘要
    console.log('\n📋 优化摘要:');
    console.log(`  索引: ${report.summary.indexes.success}/${report.summary.indexes.total} 成功`);
    console.log(`  设置: ${report.summary.pragmas.success}/${report.summary.pragmas.total} 成功`);
    console.log(`  视图: ${report.summary.views.success}/${report.summary.views.total} 成功`);
    console.log(`  性能测试: ${report.summary.performance.passed}/${report.summary.performance.total} 通过`);
    
    return report;
  }

  // 运行完整优化流程
  async optimize() {
    try {
      console.log(`🚀 开始数据库优化 (环境: ${this.environment})`);
      console.log(`📁 数据库文件: ${this.config.database}`);
      
      await this.connect();
      await this.createIndexes();
      await this.applyPragmas();
      await this.createViews();
      await this.runPerformanceTests();
      await this.analyzeDatabase();
      
      const report = this.generateReport();
      
      console.log('\n🎉 数据库优化完成!');
      return report;
      
    } catch (error) {
      console.error('❌ 数据库优化失败:', error.message);
      throw error;
    } finally {
      await this.close();
    }
  }
}

// 命令行接口
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0] || 'optimize';
  const environment = args[1] || 'development';
  
  const optimizer = new DatabaseOptimizer(environment);
  
  switch (command) {
    case 'optimize':
      optimizer.optimize().catch(console.error);
      break;
      
    case 'indexes':
      optimizer.connect()
        .then(() => optimizer.createIndexes())
        .then(() => optimizer.close())
        .catch(console.error);
      break;
      
    case 'pragmas':
      optimizer.connect()
        .then(() => optimizer.applyPragmas())
        .then(() => optimizer.close())
        .catch(console.error);
      break;
      
    case 'views':
      optimizer.connect()
        .then(() => optimizer.createViews())
        .then(() => optimizer.close())
        .catch(console.error);
      break;
      
    case 'test':
      optimizer.connect()
        .then(() => optimizer.runPerformanceTests())
        .then(() => optimizer.close())
        .catch(console.error);
      break;
      
    case 'analyze':
      optimizer.connect()
        .then(() => optimizer.analyzeDatabase())
        .then(() => optimizer.close())
        .catch(console.error);
      break;
      
    default:
      console.log('使用方法:');
      console.log('  node optimize-db.js [command] [environment]');
      console.log('');
      console.log('命令:');
      console.log('  optimize  - 运行完整优化流程 (默认)');
      console.log('  indexes   - 仅创建索引');
      console.log('  pragmas   - 仅应用性能设置');
      console.log('  views     - 仅创建视图');
      console.log('  test      - 仅运行性能测试');
      console.log('  analyze   - 仅分析数据库');
      console.log('');
      console.log('环境:');
      console.log('  development (默认)');
      console.log('  staging');
      console.log('  production');
      console.log('');
      console.log('示例:');
      console.log('  node optimize-db.js optimize development');
      console.log('  node optimize-db.js test production');
      break;
  }
}

module.exports = DatabaseOptimizer;