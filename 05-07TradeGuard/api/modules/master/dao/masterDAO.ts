import Database from 'better-sqlite3';
import { logger } from '../../../shared/utils/logger';
import { configManager } from '../../../config/environment';

// 配置项接口
interface ConfigItem {
  id?: number;
  config_key: string;
  config_value: string;
  config_type: string;
  description?: string;
  category?: string;
  is_readonly?: boolean;
  created_at?: string;
  updated_at?: string;
  updated_by?: string;
}

// 系统事件接口
interface SystemEvent {
  id?: number;
  event_type?: string;
  event_category?: string;
  severity?: string;
  source_module?: string;
  title?: string;
  description?: string;
  event_data?: string;
  user_id?: string;
  resolved?: boolean;
  resolved_by?: string;
  resolved_at?: string;
  created_at?: string;
}

// 事件过滤器接口
interface Event {
  eventType?: string;
  severity?: string;
  sourceModule?: string;
  resolved?: boolean;
  hours?: number;
}

// 数据库连接
const db = new Database(configManager.get<string>('database.path') || './data/tradeguard.db');

/**
 * 系统监控数据访问对象
 */
export class SystemMonitorDAO {
  /**
   * 初始化系统监控表
   */
  initialize(): void {
    try {
      // 创建系统状态表
      db.exec(`
        CREATE TABLE IF NOT EXISTS system_status (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          module_name TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('healthy', 'warning', 'critical', 'offline')),
          cpu_usage REAL DEFAULT 0,
          memory_usage REAL DEFAULT 0,
          disk_usage REAL DEFAULT 0,
          network_latency REAL DEFAULT 0,
          error_count INTEGER DEFAULT 0,
          last_heartbeat DATETIME DEFAULT CURRENT_TIMESTAMP,
          metadata TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // 创建性能指标表
      db.exec(`
        CREATE TABLE IF NOT EXISTS performance_metrics (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          module_name TEXT NOT NULL,
          metric_type TEXT NOT NULL,
          metric_name TEXT NOT NULL,
          metric_value REAL NOT NULL,
          unit TEXT,
          threshold_warning REAL,
          threshold_critical REAL,
          tags TEXT,
          recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // 创建系统事件表
      db.exec(`
        CREATE TABLE IF NOT EXISTS system_events (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          event_type TEXT NOT NULL,
          event_category TEXT NOT NULL,
          severity TEXT NOT NULL CHECK(severity IN ('info', 'warning', 'error', 'critical')),
          source_module TEXT NOT NULL,
          title TEXT NOT NULL,
          description TEXT,
          event_data TEXT,
          user_id TEXT,
          resolved BOOLEAN DEFAULT FALSE,
          resolved_by TEXT,
          resolved_at DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // 创建索引
      db.exec(`
        CREATE INDEX IF NOT EXISTS idx_system_status_module ON system_status(module_name);
        CREATE INDEX IF NOT EXISTS idx_system_status_status ON system_status(status);
        CREATE INDEX IF NOT EXISTS idx_system_status_updated ON system_status(updated_at);
        
        CREATE INDEX IF NOT EXISTS idx_performance_module ON performance_metrics(module_name);
        CREATE INDEX IF NOT EXISTS idx_performance_type ON performance_metrics(metric_type);
        CREATE INDEX IF NOT EXISTS idx_performance_recorded ON performance_metrics(recorded_at);
        
        CREATE INDEX IF NOT EXISTS idx_system_events_type ON system_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_system_events_severity ON system_events(severity);
        CREATE INDEX IF NOT EXISTS idx_system_events_source ON system_events(source_module);
        CREATE INDEX IF NOT EXISTS idx_system_events_created ON system_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_system_events_resolved ON system_events(resolved);
      `);

      logger.info('系统监控DAO初始化完成');
    } catch (error) {
      logger.error('系统监控DAO初始化失败:', error);
      throw error;
    }
  }

  /**
   * 更新模组状态
   */
  updateModuleStatus(moduleData: Record<string, unknown>): boolean {
    try {
      const stmt = db.prepare(`
        INSERT OR REPLACE INTO system_status (
          module_name, status, cpu_usage, memory_usage, disk_usage, 
          network_latency, error_count, last_heartbeat, metadata, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
      `);

      const result = stmt.run(
        moduleData.module_name,
        moduleData.status,
        moduleData.cpu_usage || 0,
        moduleData.memory_usage || 0,
        moduleData.disk_usage || 0,
        moduleData.network_latency || 0,
        moduleData.error_count || 0,
        moduleData.last_heartbeat || new Date().toISOString(),
        moduleData.metadata ? JSON.stringify(moduleData.metadata) : null
      );

      return result.changes > 0;
    } catch (error) {
      logger.error('更新模组状态失败:', error);
      return false;
    }
  }

  /**
   * 获取所有模组状态
   */
  getAllModuleStatus(): Record<string, unknown>[] {
    try {
      const stmt = db.prepare('SELECT * FROM system_status ORDER BY updated_at DESC');
      return stmt.all() as Record<string, unknown>[];
    } catch (error) {
      logger.error('获取模组状态失败:', error);
      return [];
    }
  }

  /**
   * 获取特定模组状态
   */
  getModuleStatus(moduleName: string): Record<string, unknown> | null {
    try {
      const stmt = db.prepare('SELECT * FROM system_status WHERE module_name = ?');
      const result = stmt.get(moduleName);
      return result ? (result as Record<string, unknown>) : null;
    } catch (error) {
      logger.error('获取特定模组状态失败:', error);
      return null;
    }
  }

  /**
   * 获取异常状态的模组
   */
  getUnhealthyModules(): Record<string, unknown>[] {
    try {
      const stmt = db.prepare(`
        SELECT * FROM system_status 
        WHERE status IN ('warning', 'critical', 'offline')
        ORDER BY 
          CASE status 
            WHEN 'critical' THEN 1
            WHEN 'offline' THEN 2
            WHEN 'warning' THEN 3
          END,
          updated_at DESC
      `);
      return stmt.all() as Record<string, unknown>[];
    } catch (error) {
      logger.error('获取异常模组失败:', error);
      return [];
    }
  }

  /**
   * 记录性能指标
   */
  recordPerformanceMetric(metricData: Record<string, unknown>): boolean {
    try {
      const stmt = db.prepare(`
        INSERT INTO performance_metrics (
          module_name, metric_type, metric_name, metric_value, unit,
          threshold_warning, threshold_critical, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);

      const result = stmt.run(
        metricData.module_name,
        metricData.metric_type,
        metricData.metric_name,
        metricData.metric_value,
        metricData.unit || null,
        metricData.threshold_warning || null,
        metricData.threshold_critical || null,
        metricData.tags ? JSON.stringify(metricData.tags) : null
      );

      return result.changes > 0;
    } catch (error) {
      logger.error('记录性能指标失败:', error);
      return false;
    }
  }

  /**
   * 获取性能指标
   */
  getPerformanceMetrics(moduleName?: string, metricType?: string, hours: number = 24): Record<string, unknown>[] {
    try {
      let query = `
        SELECT * FROM performance_metrics 
        WHERE recorded_at >= datetime('now', '-${hours} hours')
      `;
      const params: unknown[] = [];

      if (moduleName) {
        query += ' AND module_name = ?';
        params.push(moduleName);
      }

      if (metricType) {
        query += ' AND metric_type = ?';
        params.push(metricType);
      }

      query += ' ORDER BY recorded_at DESC';

      const stmt = db.prepare(query);
      return stmt.all(...params) as Record<string, unknown>[];
    } catch (error) {
      logger.error('获取性能指标失败:', error);
      return [];
    }
  }

  /**
   * 获取性能指标统计
   */
  getPerformanceStats(moduleName: string, metricName: string, hours: number = 24): Record<string, unknown> | null {
    try {
      const stmt = db.prepare(`
        SELECT 
          COUNT(*) as count,
          AVG(metric_value) as avg_value,
          MIN(metric_value) as min_value,
          MAX(metric_value) as max_value,
          unit
        FROM performance_metrics 
        WHERE module_name = ? AND metric_name = ? 
          AND recorded_at >= datetime('now', '-${hours} hours')
        GROUP BY unit
      `);

      const result = stmt.get(moduleName, metricName);
      return result ? (result as Record<string, unknown>) : null;
    } catch (error) {
      logger.error('获取性能指标统计失败:', error);
      return null;
    }
  }

  /**
   * 记录系统事件
   */
  recordSystemEvent(eventData: Record<string, unknown>): number | null {
    try {
      const stmt = db.prepare(`
        INSERT INTO system_events (
          event_type, event_category, severity, source_module, title, 
          description, event_data, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      `);

      const result = stmt.run(
        eventData.event_type,
        eventData.event_category,
        eventData.severity,
        eventData.source_module,
        eventData.title,
        eventData.description || null,
        eventData.event_data ? JSON.stringify(eventData.event_data) : null,
        eventData.user_id || null
      );

      return result.lastInsertRowid as number;
    } catch (error) {
      logger.error('记录系统事件失败:', error);
      return null;
    }
  }

  /**
   * 获取系统事件
   */
  getSystemEvents(filters: Event = {}, limit: number = 100): SystemEvent[] {
    try {
      let query = 'SELECT * FROM system_events WHERE 1=1';
      const params: unknown[] = [];

      if (filters.eventType) {
        query += ' AND event_type = ?';
        params.push(filters.eventType);
      }

      if (filters.severity) {
        query += ' AND severity = ?';
        params.push(filters.severity);
      }

      if (filters.sourceModule) {
        query += ' AND source_module = ?';
        params.push(filters.sourceModule);
      }

      if (filters.resolved !== undefined) {
        query += ' AND resolved = ?';
        params.push(filters.resolved);
      }

      if (filters.hours) {
        query += ` AND created_at >= datetime('now', '-${filters.hours} hours')`;
      }

      query += ' ORDER BY created_at DESC LIMIT ?';
      params.push(limit);

      const stmt = db.prepare(query);
      return stmt.all(...params) as SystemEvent[];
    } catch (error) {
      logger.error('获取系统事件失败:', error);
      return [];
    }
  }

  /**
   * 解决系统事件
   */
  resolveSystemEvent(eventId: number, resolvedBy: string): boolean {
    try {
      const stmt = db.prepare(`
        UPDATE system_events 
        SET resolved = TRUE, resolved_by = ?, resolved_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `);

      const result = stmt.run(resolvedBy, eventId);
      return result.changes > 0;
    } catch (error) {
      logger.error('解决系统事件失败:', error);
      return false;
    }
  }

  /**
   * 获取事件统计
   */
  getEventStatistics(hours: number = 24): Record<string, unknown> | null {
    try {
      const stmt = db.prepare(`
        SELECT 
          severity,
          COUNT(*) as count,
          COUNT(CASE WHEN resolved = TRUE THEN 1 END) as resolved_count
        FROM system_events 
        WHERE created_at >= datetime('now', '-${hours} hours')
        GROUP BY severity
      `);

      const stats = stmt.all() as Record<string, unknown>[];
      
      // 转换为对象格式
      const result: Record<string, unknown> = {
        total: 0,
        resolved: 0,
        by_severity: {} as Record<string, unknown>
      };

      stats.forEach((stat: Record<string, unknown>) => {
        const count = stat.count as number;
        const resolvedCount = stat.resolved_count as number;
        const severity = stat.severity as string;
        
        (result.total as number) += count;
        (result.resolved as number) += resolvedCount;
        (result.by_severity as Record<string, unknown>)[severity] = {
          count: count,
          resolved: resolvedCount,
          unresolved: count - resolvedCount
        };
      });

      result.unresolved = (result.total as number) - (result.resolved as number);
      return result;
    } catch (error) {
      logger.error('获取事件统计失败:', error);
      return null;
    }
  }

  /**
   * 清理过期数据
   */
  cleanupOldData(retentionDays: number = 30): number {
    try {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - retentionDays);
      
      // 清理过期的性能指标
      const metricsStmt = db.prepare(`
        DELETE FROM performance_metrics 
        WHERE recorded_at < ?
      `);
      const metricsResult = metricsStmt.run(cutoffDate.toISOString());

      // 清理已解决的过期事件
      const eventsStmt = db.prepare(`
        DELETE FROM system_events 
        WHERE resolved = TRUE AND resolved_at < ?
      `);
      const eventsResult = eventsStmt.run(cutoffDate.toISOString());

      const totalCleaned = metricsResult.changes + eventsResult.changes;
      logger.info(`清理了 ${totalCleaned} 条过期数据`);
      
      return totalCleaned;
    } catch (error) {
      logger.error('清理过期数据失败:', error);
      return 0;
    }
  }
}

/**
 * 系统配置数据访问对象
 */
export class SystemConfigDAO {
  /**
   * 初始化系统配置表
   */
  initialize(): void {
    try {
      // 创建系统配置表
      db.exec(`
        CREATE TABLE IF NOT EXISTS system_config (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          config_key TEXT UNIQUE NOT NULL,
          config_value TEXT NOT NULL,
          config_type TEXT NOT NULL CHECK(config_type IN ('string', 'number', 'boolean', 'json')),
          description TEXT,
          category TEXT,
          is_sensitive BOOLEAN DEFAULT FALSE,
          is_readonly BOOLEAN DEFAULT FALSE,
          validation_rule TEXT,
          created_by TEXT,
          updated_by TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // 创建配置变更历史表
      db.exec(`
        CREATE TABLE IF NOT EXISTS config_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          config_key TEXT NOT NULL,
          old_value TEXT,
          new_value TEXT NOT NULL,
          changed_by TEXT NOT NULL,
          change_reason TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
      `);

      // 创建索引
      db.exec(`
        CREATE INDEX IF NOT EXISTS idx_config_key ON system_config(config_key);
        CREATE INDEX IF NOT EXISTS idx_config_category ON system_config(category);
        CREATE INDEX IF NOT EXISTS idx_config_history_key ON config_history(config_key);
        CREATE INDEX IF NOT EXISTS idx_config_history_created ON config_history(created_at);
      `);

      // 插入默认配置
      this.insertDefaultConfigs();

      logger.info('系统配置DAO初始化完成');
    } catch (error) {
      logger.error('系统配置DAO初始化失败:', error);
      throw error;
    }
  }

  /**
   * 插入默认配置
   */
  private insertDefaultConfigs(): void {
    const defaultConfigs = [
      {
        config_key: 'system.emergency_stop_enabled',
        config_value: 'false',
        config_type: 'boolean',
        description: '系统紧急停止开关',
        category: 'emergency'
      },
      {
        config_key: 'system.max_concurrent_strategies',
        config_value: '100',
        config_type: 'number',
        description: '最大并发策略数量',
        category: 'performance'
      },
      {
        config_key: 'system.health_check_interval',
        config_value: '30000',
        config_type: 'number',
        description: '健康检查间隔(毫秒)',
        category: 'monitoring'
      },
      {
        config_key: 'system.alert_thresholds',
        config_value: JSON.stringify({
          cpu_warning: 70,
          cpu_critical: 90,
          memory_warning: 80,
          memory_critical: 95,
          disk_warning: 85,
          disk_critical: 95
        }),
        config_type: 'json',
        description: '系统警报阈值配置',
        category: 'monitoring'
      },
      {
        config_key: 'system.data_retention_days',
        config_value: '30',
        config_type: 'number',
        description: '数据保留天数',
        category: 'maintenance'
      }
    ];

    const stmt = db.prepare(`
      INSERT OR IGNORE INTO system_config (
        config_key, config_value, config_type, description, category
      ) VALUES (?, ?, ?, ?, ?)
    `);

    defaultConfigs.forEach(config => {
      stmt.run(
        config.config_key,
        config.config_value,
        config.config_type,
        config.description,
        config.category
      );
    });
  }

  /**
   * 获取配置值
   */
  getConfig(key: string): Record<string, unknown> {
    try {
      const stmt = db.prepare('SELECT * FROM system_config WHERE config_key = ?');
      const config = stmt.get(key) as ConfigItem | undefined;
      
      if (!config) return null;

      // 根据类型转换值
      switch (config.config_type) {
        case 'number':
          return { ...config, config_value: Number(config.config_value) };
        case 'boolean':
          return { ...config, config_value: config.config_value === 'true' };
        case 'json':
          return { ...config, config_value: JSON.parse(config.config_value) };
        default:
          return config as unknown as Record<string, unknown>;
      }
    } catch (error) {
      logger.error('获取配置失败:', error);
      return null;
    }
  }

  /**
   * 获取所有配置
   */
  getAllConfigs(category?: string): Record<string, unknown>[] {
    try {
      let query = 'SELECT * FROM system_config';
      const params: any[] = [];

      if (category) {
        query += ' WHERE category = ?';
        params.push(category);
      }

      query += ' ORDER BY category, config_key';

      const stmt = db.prepare(query);
      const configs = stmt.all(...params);

      // 转换值类型
      return (configs as ConfigItem[]).map((config: ConfigItem) => {
        switch (config.config_type) {
          case 'number':
            return { ...config, config_value: Number(config.config_value) };
          case 'boolean':
            return { ...config, config_value: config.config_value === 'true' };
          case 'json':
            return { ...config, config_value: JSON.parse(config.config_value) };
          default:
            return config;
        }
      });
    } catch (error) {
      logger.error('获取所有配置失败:', error);
      return [];
    }
  }

  /**
   * 更新配置
   */
  updateConfig(key: string, value: Record<string, unknown>, updatedBy: string, reason?: string): boolean {
    try {
      // 获取当前配置
      const currentConfig = this.getConfig(key);
      if (!currentConfig) {
        logger.error(`配置项 ${key} 不存在`);
        return false;
      }

      if (currentConfig.is_readonly) {
        logger.error(`配置项 ${key} 为只读，无法修改`);
        return false;
      }

      // 转换值为字符串
      let stringValue: string;
      switch (currentConfig.config_type) {
        case 'json':
          stringValue = JSON.stringify(value);
          break;
        default:
          stringValue = String(value);
      }

      // 记录变更历史
      const historyStmt = db.prepare(`
        INSERT INTO config_history (
          config_key, old_value, new_value, changed_by, change_reason
        ) VALUES (?, ?, ?, ?, ?)
      `);
      
      historyStmt.run(
        key,
        currentConfig.config_value,
        stringValue,
        updatedBy,
        reason || null
      );

      // 更新配置
      const updateStmt = db.prepare(`
        UPDATE system_config 
        SET config_value = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
        WHERE config_key = ?
      `);

      const result = updateStmt.run(stringValue, updatedBy, key);
      return result.changes > 0;
    } catch (error) {
      logger.error('更新配置失败:', error);
      return false;
    }
  }

  /**
   * 获取配置变更历史
   */
  getConfigHistory(key?: string, limit: number = 50): Record<string, unknown>[] {
    try {
      let query = 'SELECT * FROM config_history';
      const params: any[] = [];

      if (key) {
        query += ' WHERE config_key = ?';
        params.push(key);
      }

      query += ' ORDER BY created_at DESC LIMIT ?';
        params.push(limit);

      const stmt = db.prepare(query);
      return stmt.all(...params) as Record<string, unknown>[];
    } catch (error) {
      logger.error('获取配置变更历史失败:', error);
      return [];
    }
  }
}

// 创建DAO实例
export const systemMonitorDAO = new SystemMonitorDAO();
export const systemConfigDAO = new SystemConfigDAO();

// 默认导出
export default {
  systemMonitorDAO,
  systemConfigDAO
};