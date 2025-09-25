#!/usr/bin/env node
/**
 * 性能监控脚本
 * 用于交易执行铁三角项目的实时性能监控和分析
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const sqlite3 = require('sqlite3').verbose();
const { performance } = require('perf_hooks');
const EventEmitter = require('events');

// 加载查询优化配置
const queryConfig = require('../config/query-optimization.json');

class PerformanceMonitor extends EventEmitter {
  constructor(options = {}) {
    super();
    
    this.options = {
      environment: options.environment || 'development',
      monitorInterval: options.monitorInterval || 30000, // 30秒
      slowQueryThreshold: options.slowQueryThreshold || 1000, // 1秒
      memoryThreshold: options.memoryThreshold || 80, // 80%
      cpuThreshold: options.cpuThreshold || 80, // 80%
      logFile: options.logFile || './logs/performance.log',
      reportFile: options.reportFile || './reports/performance-report.json',
      ...options
    };
    
    this.db = null;
    this.isRunning = false;
    this.intervalId = null;
    this.startTime = Date.now();
    
    this.metrics = {
      system: {
        cpu: [],
        memory: [],
        disk: [],
        network: []
      },
      database: {
        queries: [],
        connections: [],
        locks: [],
        cache: []
      },
      application: {
        requests: [],
        responses: [],
        errors: [],
        performance: []
      }
    };
    
    this.alerts = [];
    this.queryStats = new Map();
    
    // 确保日志和报告目录存在
    this.ensureDirectories();
  }

  // 确保目录存在
  ensureDirectories() {
    const dirs = [
      path.dirname(this.options.logFile),
      path.dirname(this.options.reportFile)
    ];
    
    dirs.forEach(dir => {
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }
    });
  }

  // 连接数据库
  async connect() {
    const dbPath = this.getDatabasePath();
    
    return new Promise((resolve, reject) => {
      this.db = new sqlite3.Database(dbPath, (err) => {
        if (err) {
          reject(err);
        } else {
          console.log(`✅ 性能监控已连接到数据库: ${dbPath}`);
          resolve();
        }
      });
    });
  }

  // 获取数据库路径
  getDatabasePath() {
    const configPath = path.join(__dirname, '..', 'config', `config.${this.options.environment}.json`);
    
    if (fs.existsSync(configPath)) {
      const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
      return config.database?.path || `./data/${this.options.environment}.db`;
    }
    
    return `./data/${this.options.environment}.db`;
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

  // 执行查询并监控性能
  async executeQuery(sql, params = []) {
    const startTime = performance.now();
    const queryId = this.generateQueryId(sql);
    
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        const endTime = performance.now();
        const duration = endTime - startTime;
        
        // 记录查询统计
        this.recordQueryStats(queryId, sql, duration, err, rows?.length || 0);
        
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  // 生成查询ID
  generateQueryId(sql) {
    // 简化SQL语句用于分组
    const normalized = sql
      .replace(/\s+/g, ' ')
      .replace(/\d+/g, '?')
      .replace(/'[^']*'/g, '?')
      .trim()
      .toLowerCase();
    
    return normalized.substring(0, 100);
  }

  // 记录查询统计
  recordQueryStats(queryId, sql, duration, error, rowCount) {
    const timestamp = new Date().toISOString();
    
    if (!this.queryStats.has(queryId)) {
      this.queryStats.set(queryId, {
        sql: sql.substring(0, 200),
        count: 0,
        totalDuration: 0,
        avgDuration: 0,
        minDuration: Infinity,
        maxDuration: 0,
        errors: 0,
        lastExecuted: timestamp
      });
    }
    
    const stats = this.queryStats.get(queryId);
    stats.count++;
    stats.totalDuration += duration;
    stats.avgDuration = stats.totalDuration / stats.count;
    stats.minDuration = Math.min(stats.minDuration, duration);
    stats.maxDuration = Math.max(stats.maxDuration, duration);
    stats.lastExecuted = timestamp;
    
    if (error) {
      stats.errors++;
    }
    
    // 记录到数据库指标
    this.metrics.database.queries.push({
      timestamp,
      queryId,
      duration,
      rowCount,
      error: error ? error.message : null
    });
    
    // 检查慢查询
    if (duration > this.options.slowQueryThreshold) {
      this.handleSlowQuery(queryId, sql, duration);
    }
    
    // 记录到日志
    this.log('query', {
      queryId,
      duration: Math.round(duration),
      rowCount,
      error: error ? error.message : null
    });
  }

  // 处理慢查询
  handleSlowQuery(queryId, sql, duration) {
    const alert = {
      type: 'slow_query',
      severity: 'warning',
      timestamp: new Date().toISOString(),
      message: `慢查询检测: ${Math.round(duration)}ms`,
      details: {
        queryId,
        sql: sql.substring(0, 200),
        duration,
        threshold: this.options.slowQueryThreshold
      }
    };
    
    this.alerts.push(alert);
    this.emit('slowQuery', alert);
    
    console.log(`⚠️ 慢查询警告: ${Math.round(duration)}ms - ${sql.substring(0, 100)}...`);
  }

  // 收集系统指标
  async collectSystemMetrics() {
    const timestamp = new Date().toISOString();
    
    try {
      // CPU使用率
      const cpuUsage = await this.getCpuUsage();
      this.metrics.system.cpu.push({
        timestamp,
        usage: cpuUsage
      });
      
      // 内存使用率
      const memoryUsage = this.getMemoryUsage();
      this.metrics.system.memory.push({
        timestamp,
        ...memoryUsage
      });
      
      // 磁盘使用率
      const diskUsage = await this.getDiskUsage();
      this.metrics.system.disk.push({
        timestamp,
        ...diskUsage
      });
      
      // 检查阈值
      this.checkSystemThresholds(cpuUsage, memoryUsage);
      
    } catch (error) {
      console.error('❌ 收集系统指标失败:', error.message);
    }
  }

  // 获取CPU使用率
  async getCpuUsage() {
    return new Promise((resolve) => {
      const startMeasure = this.cpuAverage();
      
      setTimeout(() => {
        const endMeasure = this.cpuAverage();
        
        const idleDifference = endMeasure.idle - startMeasure.idle;
        const totalDifference = endMeasure.total - startMeasure.total;
        
        const percentageCPU = 100 - ~~(100 * idleDifference / totalDifference);
        resolve(percentageCPU);
      }, 1000);
    });
  }

  // CPU平均值计算
  cpuAverage() {
    const cpus = os.cpus();
    let user = 0, nice = 0, sys = 0, idle = 0, irq = 0;
    
    cpus.forEach(cpu => {
      user += cpu.times.user;
      nice += cpu.times.nice;
      sys += cpu.times.sys;
      idle += cpu.times.idle;
      irq += cpu.times.irq;
    });
    
    const total = user + nice + sys + idle + irq;
    
    return { idle, total };
  }

  // 获取内存使用率
  getMemoryUsage() {
    const totalMemory = os.totalmem();
    const freeMemory = os.freemem();
    const usedMemory = totalMemory - freeMemory;
    const usagePercentage = (usedMemory / totalMemory) * 100;
    
    return {
      total: totalMemory,
      used: usedMemory,
      free: freeMemory,
      usage: usagePercentage
    };
  }

  // 获取磁盘使用率
  async getDiskUsage() {
    try {
      const stats = fs.statSync('.');
      return {
        available: 0, // 简化实现
        used: 0,
        total: 0,
        usage: 0
      };
    } catch (error) {
      return {
        available: 0,
        used: 0,
        total: 0,
        usage: 0
      };
    }
  }

  // 检查系统阈值
  checkSystemThresholds(cpuUsage, memoryUsage) {
    const timestamp = new Date().toISOString();
    
    // CPU阈值检查
    if (cpuUsage > this.options.cpuThreshold) {
      const alert = {
        type: 'high_cpu',
        severity: 'warning',
        timestamp,
        message: `CPU使用率过高: ${cpuUsage.toFixed(1)}%`,
        details: {
          current: cpuUsage,
          threshold: this.options.cpuThreshold
        }
      };
      
      this.alerts.push(alert);
      this.emit('highCpu', alert);
      console.log(`⚠️ CPU使用率警告: ${cpuUsage.toFixed(1)}%`);
    }
    
    // 内存阈值检查
    if (memoryUsage.usage > this.options.memoryThreshold) {
      const alert = {
        type: 'high_memory',
        severity: 'warning',
        timestamp,
        message: `内存使用率过高: ${memoryUsage.usage.toFixed(1)}%`,
        details: {
          current: memoryUsage.usage,
          threshold: this.options.memoryThreshold
        }
      };
      
      this.alerts.push(alert);
      this.emit('highMemory', alert);
      console.log(`⚠️ 内存使用率警告: ${memoryUsage.usage.toFixed(1)}%`);
    }
  }

  // 收集数据库指标
  async collectDatabaseMetrics() {
    const timestamp = new Date().toISOString();
    
    try {
      // 数据库大小
      const dbSize = await this.getDatabaseSize();
      
      // 表统计
      const tableStats = await this.getTableStatistics();
      
      // 索引使用情况
      const indexStats = await this.getIndexStatistics();
      
      this.metrics.database.cache.push({
        timestamp,
        dbSize,
        tableStats,
        indexStats
      });
      
    } catch (error) {
      console.error('❌ 收集数据库指标失败:', error.message);
    }
  }

  // 获取数据库大小
  async getDatabaseSize() {
    try {
      const result = await this.executeQuery('PRAGMA page_count, page_size');
      if (result.length > 0) {
        const pageCount = result[0].page_count || 0;
        const pageSize = result[0].page_size || 0;
        return pageCount * pageSize;
      }
    } catch (error) {
      console.error('获取数据库大小失败:', error.message);
    }
    return 0;
  }

  // 获取表统计信息
  async getTableStatistics() {
    try {
      const tables = await this.executeQuery(`
        SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'
      `);
      
      const stats = {};
      for (const table of tables) {
        try {
          const count = await this.executeQuery(`SELECT COUNT(*) as count FROM ${table.name}`);
          stats[table.name] = count[0].count;
        } catch (error) {
          stats[table.name] = 0;
        }
      }
      
      return stats;
    } catch (error) {
      console.error('获取表统计失败:', error.message);
      return {};
    }
  }

  // 获取索引统计信息
  async getIndexStatistics() {
    try {
      const indexes = await this.executeQuery(`
        SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'
      `);
      
      return {
        total: indexes.length,
        byTable: indexes.reduce((acc, index) => {
          acc[index.tbl_name] = (acc[index.tbl_name] || 0) + 1;
          return acc;
        }, {})
      };
    } catch (error) {
      console.error('获取索引统计失败:', error.message);
      return { total: 0, byTable: {} };
    }
  }

  // 生成性能报告
  generateReport() {
    const now = Date.now();
    const uptime = now - this.startTime;
    
    const report = {
      timestamp: new Date().toISOString(),
      environment: this.options.environment,
      uptime: uptime,
      summary: {
        totalQueries: Array.from(this.queryStats.values()).reduce((sum, stat) => sum + stat.count, 0),
        slowQueries: this.alerts.filter(a => a.type === 'slow_query').length,
        totalAlerts: this.alerts.length,
        avgQueryTime: this.calculateAverageQueryTime(),
        topSlowQueries: this.getTopSlowQueries(5)
      },
      system: {
        cpu: this.getLatestMetric('system.cpu'),
        memory: this.getLatestMetric('system.memory'),
        disk: this.getLatestMetric('system.disk')
      },
      database: {
        size: this.getLatestMetric('database.cache')?.dbSize || 0,
        tableStats: this.getLatestMetric('database.cache')?.tableStats || {},
        indexStats: this.getLatestMetric('database.cache')?.indexStats || {}
      },
      queryStats: Array.from(this.queryStats.entries()).map(([id, stats]) => ({
        queryId: id,
        ...stats
      })),
      alerts: this.alerts.slice(-50), // 最近50个警告
      recommendations: this.generateRecommendations()
    };
    
    // 保存报告
    fs.writeFileSync(this.options.reportFile, JSON.stringify(report, null, 2));
    
    return report;
  }

  // 获取最新指标
  getLatestMetric(path) {
    const parts = path.split('.');
    let current = this.metrics;
    
    for (const part of parts) {
      current = current[part];
      if (!current) return null;
    }
    
    return Array.isArray(current) ? current[current.length - 1] : current;
  }

  // 计算平均查询时间
  calculateAverageQueryTime() {
    const stats = Array.from(this.queryStats.values());
    if (stats.length === 0) return 0;
    
    const totalTime = stats.reduce((sum, stat) => sum + stat.totalDuration, 0);
    const totalCount = stats.reduce((sum, stat) => sum + stat.count, 0);
    
    return totalCount > 0 ? totalTime / totalCount : 0;
  }

  // 获取最慢查询
  getTopSlowQueries(limit = 5) {
    return Array.from(this.queryStats.entries())
      .map(([id, stats]) => ({ queryId: id, ...stats }))
      .sort((a, b) => b.maxDuration - a.maxDuration)
      .slice(0, limit);
  }

  // 生成优化建议
  generateRecommendations() {
    const recommendations = [];
    
    // 慢查询建议
    const slowQueries = this.getTopSlowQueries(3);
    slowQueries.forEach(query => {
      if (query.maxDuration > this.options.slowQueryThreshold) {
        recommendations.push({
          type: 'slow_query',
          priority: 'high',
          message: `优化慢查询: ${query.sql.substring(0, 50)}...`,
          details: `最大执行时间: ${Math.round(query.maxDuration)}ms，建议添加索引或重写查询`
        });
      }
    });
    
    // 频繁查询建议
    const frequentQueries = Array.from(this.queryStats.values())
      .filter(stat => stat.count > 100)
      .sort((a, b) => b.count - a.count)
      .slice(0, 3);
    
    frequentQueries.forEach(query => {
      recommendations.push({
        type: 'frequent_query',
        priority: 'medium',
        message: `考虑缓存频繁查询: ${query.sql.substring(0, 50)}...`,
        details: `执行次数: ${query.count}，平均时间: ${Math.round(query.avgDuration)}ms`
      });
    });
    
    // 系统资源建议
    const latestCpu = this.getLatestMetric('system.cpu');
    const latestMemory = this.getLatestMetric('system.memory');
    
    if (latestCpu && latestCpu.usage > 70) {
      recommendations.push({
        type: 'system_resource',
        priority: 'medium',
        message: 'CPU使用率较高，考虑优化查询或增加服务器资源',
        details: `当前CPU使用率: ${latestCpu.usage.toFixed(1)}%`
      });
    }
    
    if (latestMemory && latestMemory.usage > 70) {
      recommendations.push({
        type: 'system_resource',
        priority: 'medium',
        message: '内存使用率较高，考虑优化内存使用或增加内存',
        details: `当前内存使用率: ${latestMemory.usage.toFixed(1)}%`
      });
    }
    
    return recommendations;
  }

  // 记录日志
  log(type, data) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      type,
      ...data
    };
    
    const logLine = JSON.stringify(logEntry) + '\n';
    fs.appendFileSync(this.options.logFile, logLine);
  }

  // 启动监控
  async start() {
    if (this.isRunning) {
      console.log('⚠️ 性能监控已在运行中');
      return;
    }
    
    try {
      await this.connect();
      
      this.isRunning = true;
      console.log(`🚀 性能监控已启动 (环境: ${this.options.environment})`);
      console.log(`📊 监控间隔: ${this.options.monitorInterval}ms`);
      console.log(`⏱️ 慢查询阈值: ${this.options.slowQueryThreshold}ms`);
      
      // 定期收集指标
      this.intervalId = setInterval(async () => {
        try {
          await this.collectSystemMetrics();
          await this.collectDatabaseMetrics();
          
          // 定期清理旧数据
          this.cleanupOldMetrics();
          
        } catch (error) {
          console.error('❌ 收集指标失败:', error.message);
        }
      }, this.options.monitorInterval);
      
      // 定期生成报告
      setInterval(() => {
        try {
          this.generateReport();
          console.log('📊 性能报告已更新');
        } catch (error) {
          console.error('❌ 生成报告失败:', error.message);
        }
      }, 300000); // 5分钟
      
    } catch (error) {
      console.error('❌ 启动性能监控失败:', error.message);
      throw error;
    }
  }

  // 停止监控
  async stop() {
    if (!this.isRunning) {
      console.log('⚠️ 性能监控未在运行');
      return;
    }
    
    this.isRunning = false;
    
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    
    // 生成最终报告
    try {
      const finalReport = this.generateReport();
      console.log('📊 最终性能报告已生成');
    } catch (error) {
      console.error('❌ 生成最终报告失败:', error.message);
    }
    
    await this.close();
    console.log('🛑 性能监控已停止');
  }

  // 清理旧指标数据
  cleanupOldMetrics() {
    const maxAge = 24 * 60 * 60 * 1000; // 24小时
    const cutoff = Date.now() - maxAge;
    
    // 清理系统指标
    Object.keys(this.metrics.system).forEach(key => {
      this.metrics.system[key] = this.metrics.system[key].filter(
        metric => new Date(metric.timestamp).getTime() > cutoff
      );
    });
    
    // 清理数据库指标
    Object.keys(this.metrics.database).forEach(key => {
      this.metrics.database[key] = this.metrics.database[key].filter(
        metric => new Date(metric.timestamp).getTime() > cutoff
      );
    });
    
    // 清理旧警告
    this.alerts = this.alerts.filter(
      alert => new Date(alert.timestamp).getTime() > cutoff
    );
  }

  // 获取状态
  getStatus() {
    return {
      isRunning: this.isRunning,
      uptime: Date.now() - this.startTime,
      totalQueries: Array.from(this.queryStats.values()).reduce((sum, stat) => sum + stat.count, 0),
      totalAlerts: this.alerts.length,
      environment: this.options.environment
    };
  }
}

// 命令行接口
if (require.main === module) {
  const args = process.argv.slice(2);
  const command = args[0] || 'start';
  const environment = args[1] || 'development';
  
  const monitor = new PerformanceMonitor({ environment });
  
  // 处理进程信号
  process.on('SIGINT', async () => {
    console.log('\n收到停止信号，正在关闭性能监控...');
    await monitor.stop();
    process.exit(0);
  });
  
  process.on('SIGTERM', async () => {
    console.log('\n收到终止信号，正在关闭性能监控...');
    await monitor.stop();
    process.exit(0);
  });
  
  switch (command) {
    case 'start':
      monitor.start().catch(console.error);
      break;
      
    case 'stop':
      monitor.stop().catch(console.error);
      break;
      
    case 'status':
      console.log('性能监控状态:', monitor.getStatus());
      break;
      
    case 'report':
      monitor.connect()
        .then(() => {
          const report = monitor.generateReport();
          console.log('性能报告已生成:', monitor.options.reportFile);
          return monitor.close();
        })
        .catch(console.error);
      break;
      
    default:
      console.log('使用方法:');
      console.log('  node performance-monitor.js [command] [environment]');
      console.log('');
      console.log('命令:');
      console.log('  start   - 启动性能监控 (默认)');
      console.log('  stop    - 停止性能监控');
      console.log('  status  - 查看监控状态');
      console.log('  report  - 生成性能报告');
      console.log('');
      console.log('环境:');
      console.log('  development (默认)');
      console.log('  staging');
      console.log('  production');
      console.log('');
      console.log('示例:');
      console.log('  node performance-monitor.js start production');
      console.log('  node performance-monitor.js report development');
      break;
  }
}

module.exports = PerformanceMonitor;