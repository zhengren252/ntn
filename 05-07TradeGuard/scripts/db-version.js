/**
 * 交易执行铁三角项目 - 数据库版本管理工具
 * 用途：管理数据库版本、执行迁移、回滚等操作
 */

const fs = require('fs');
const path = require('path');
const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');

// 配置
const CONFIG = {
  MIGRATIONS_DIR: './migrations',
  DATA_DIR: './data',
  BACKUP_DIR: './backups',
  ENVIRONMENTS: ['development', 'staging', 'production']
};

// 日志工具
class Logger {
  static info(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [INFO] ${message}`);
    if (data) console.log(data);
  }

  static success(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`\x1b[32m[${timestamp}] [SUCCESS] ${message}\x1b[0m`);
    if (data) console.log(data);
  }

  static warning(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`\x1b[33m[${timestamp}] [WARNING] ${message}\x1b[0m`);
    if (data) console.log(data);
  }

  static error(message, data = null) {
    const timestamp = new Date().toISOString();
    console.log(`\x1b[31m[${timestamp}] [ERROR] ${message}\x1b[0m`);
    if (data) console.log(data);
  }
}

// 数据库版本管理类
class DatabaseVersionManager {
  constructor(environment = 'development') {
    this.environment = environment;
    this.dbPath = path.join(CONFIG.DATA_DIR, `${environment}.db`);
    this.db = null;
  }

  // 连接数据库
  async connect() {
    return new Promise((resolve, reject) => {
      // 确保数据目录存在
      if (!fs.existsSync(CONFIG.DATA_DIR)) {
        fs.mkdirSync(CONFIG.DATA_DIR, { recursive: true });
      }

      this.db = new sqlite3.Database(this.dbPath, (err) => {
        if (err) {
          Logger.error('数据库连接失败:', err);
          reject(err);
        } else {
          Logger.info(`已连接到数据库: ${this.dbPath}`);
          resolve();
        }
      });
    });
  }

  // 关闭数据库连接
  async close() {
    if (this.db) {
      return new Promise((resolve) => {
        this.db.close((err) => {
          if (err) {
            Logger.error('关闭数据库连接失败:', err);
          } else {
            Logger.info('数据库连接已关闭');
          }
          resolve();
        });
      });
    }
  }

  // 执行SQL查询
  async query(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.all(sql, params, (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  // 执行SQL语句
  async run(sql, params = []) {
    return new Promise((resolve, reject) => {
      this.db.run(sql, params, function(err) {
        if (err) {
          reject(err);
        } else {
          resolve({ lastID: this.lastID, changes: this.changes });
        }
      });
    });
  }

  // 初始化迁移表
  async initializeMigrationTable() {
    const sql = `
      CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        checksum TEXT,
        execution_time INTEGER
      )
    `;
    
    await this.run(sql);
    Logger.info('迁移表已初始化');
  }

  // 获取所有迁移文件
  getMigrationFiles() {
    if (!fs.existsSync(CONFIG.MIGRATIONS_DIR)) {
      Logger.warning('迁移目录不存在');
      return [];
    }

    const files = fs.readdirSync(CONFIG.MIGRATIONS_DIR)
      .filter(file => file.endsWith('.sql'))
      .sort();

    return files.map(file => {
      const version = path.basename(file, '.sql');
      const filePath = path.join(CONFIG.MIGRATIONS_DIR, file);
      return { version, file, filePath };
    });
  }

  // 获取已应用的迁移
  async getAppliedMigrations() {
    try {
      const rows = await this.query('SELECT version FROM schema_migrations ORDER BY version');
      return rows.map(row => row.version);
    } catch (err) {
      // 如果表不存在，返回空数组
      return [];
    }
  }

  // 获取待应用的迁移
  async getPendingMigrations() {
    const allMigrations = this.getMigrationFiles();
    const appliedMigrations = await this.getAppliedMigrations();
    
    return allMigrations.filter(migration => 
      !appliedMigrations.includes(migration.version)
    );
  }

  // 解析迁移文件
  parseMigrationFile(filePath) {
    const content = fs.readFileSync(filePath, 'utf8');
    
    // 分离UP和DOWN部分
    const upMatch = content.match(/-- 向前迁移 \(UP\)([\s\S]*?)-- 回滚迁移 \(DOWN\)/i);
    const downMatch = content.match(/-- 回滚迁移 \(DOWN\)([\s\S]*?)$/i);
    
    const upSql = upMatch ? upMatch[1].trim() : '';
    const downSql = downMatch ? downMatch[1].trim() : '';
    
    return { upSql, downSql };
  }

  // 计算文件校验和
  calculateChecksum(content) {
    const crypto = require('crypto');
    return crypto.createHash('md5').update(content).digest('hex');
  }

  // 应用单个迁移
  async applyMigration(migration) {
    const startTime = Date.now();
    
    try {
      Logger.info(`应用迁移: ${migration.version}`);
      
      const { upSql } = this.parseMigrationFile(migration.filePath);
      
      if (!upSql) {
        Logger.warning(`迁移文件 ${migration.version} 中没有找到向前迁移的SQL`);
        return;
      }
      
      // 计算校验和
      const content = fs.readFileSync(migration.filePath, 'utf8');
      const checksum = this.calculateChecksum(content);
      
      // 开始事务
      await this.run('BEGIN TRANSACTION');
      
      try {
        // 执行迁移SQL
        const statements = upSql.split(';').filter(stmt => stmt.trim());
        for (const statement of statements) {
          if (statement.trim()) {
            await this.run(statement.trim());
          }
        }
        
        // 记录迁移
        const executionTime = Date.now() - startTime;
        await this.run(
          'INSERT INTO schema_migrations (version, checksum, execution_time) VALUES (?, ?, ?)',
          [migration.version, checksum, executionTime]
        );
        
        // 提交事务
        await this.run('COMMIT');
        
        Logger.success(`迁移应用成功: ${migration.version} (耗时: ${executionTime}ms)`);
        
      } catch (err) {
        // 回滚事务
        await this.run('ROLLBACK');
        throw err;
      }
      
    } catch (err) {
      Logger.error(`迁移应用失败: ${migration.version}`, err);
      throw err;
    }
  }

  // 回滚单个迁移
  async rollbackMigration(migration) {
    const startTime = Date.now();
    
    try {
      Logger.info(`回滚迁移: ${migration.version}`);
      
      const { downSql } = this.parseMigrationFile(migration.filePath);
      
      if (!downSql) {
        Logger.warning(`迁移文件 ${migration.version} 中没有找到回滚迁移的SQL`);
        return;
      }
      
      // 开始事务
      await this.run('BEGIN TRANSACTION');
      
      try {
        // 执行回滚SQL
        const statements = downSql.split(';').filter(stmt => stmt.trim());
        for (const statement of statements) {
          if (statement.trim()) {
            await this.run(statement.trim());
          }
        }
        
        // 删除迁移记录
        await this.run('DELETE FROM schema_migrations WHERE version = ?', [migration.version]);
        
        // 提交事务
        await this.run('COMMIT');
        
        const executionTime = Date.now() - startTime;
        Logger.success(`迁移回滚成功: ${migration.version} (耗时: ${executionTime}ms)`);
        
      } catch (err) {
        // 回滚事务
        await this.run('ROLLBACK');
        throw err;
      }
      
    } catch (err) {
      Logger.error(`迁移回滚失败: ${migration.version}`, err);
      throw err;
    }
  }

  // 运行所有待应用的迁移
  async migrate() {
    await this.connect();
    await this.initializeMigrationTable();
    
    const pendingMigrations = await this.getPendingMigrations();
    
    if (pendingMigrations.length === 0) {
      Logger.info('没有待应用的迁移');
      return;
    }
    
    Logger.info(`发现 ${pendingMigrations.length} 个待应用的迁移`);
    
    for (const migration of pendingMigrations) {
      await this.applyMigration(migration);
    }
    
    Logger.success('所有迁移应用完成');
  }

  // 回滚指定数量的迁移
  async rollback(steps = 1) {
    await this.connect();
    await this.initializeMigrationTable();
    
    const appliedMigrations = await this.getAppliedMigrations();
    
    if (appliedMigrations.length === 0) {
      Logger.info('没有已应用的迁移可以回滚');
      return;
    }
    
    const migrationsToRollback = appliedMigrations
      .slice(-steps)
      .reverse();
    
    Logger.info(`准备回滚 ${migrationsToRollback.length} 个迁移`);
    
    const allMigrations = this.getMigrationFiles();
    
    for (const version of migrationsToRollback) {
      const migration = allMigrations.find(m => m.version === version);
      if (migration) {
        await this.rollbackMigration(migration);
      } else {
        Logger.warning(`找不到迁移文件: ${version}`);
      }
    }
    
    Logger.success('迁移回滚完成');
  }

  // 显示迁移状态
  async status() {
    await this.connect();
    await this.initializeMigrationTable();
    
    const allMigrations = this.getMigrationFiles();
    const appliedMigrations = await this.getAppliedMigrations();
    
    Logger.info(`数据库迁移状态 - 环境: ${this.environment}`);
    console.log('='.repeat(60));
    
    if (allMigrations.length === 0) {
      console.log('没有找到迁移文件');
      return;
    }
    
    console.log('\x1b[32m已应用的迁移:\x1b[0m');
    let appliedCount = 0;
    for (const migration of allMigrations) {
      if (appliedMigrations.includes(migration.version)) {
        console.log(`  ✓ ${migration.version}`);
        appliedCount++;
      }
    }
    
    if (appliedCount === 0) {
      console.log('  无');
    }
    
    console.log('\n\x1b[33m待应用的迁移:\x1b[0m');
    let pendingCount = 0;
    for (const migration of allMigrations) {
      if (!appliedMigrations.includes(migration.version)) {
        console.log(`  ○ ${migration.version}`);
        pendingCount++;
      }
    }
    
    if (pendingCount === 0) {
      console.log('  无');
    }
    
    console.log('\n' + '='.repeat(60));
    console.log(`总计: ${allMigrations.length} 个迁移, ${appliedCount} 个已应用, ${pendingCount} 个待应用`);
  }

  // 创建新的迁移文件
  static createMigration(name) {
    if (!name) {
      Logger.error('请提供迁移文件名称');
      return;
    }
    
    // 确保迁移目录存在
    if (!fs.existsSync(CONFIG.MIGRATIONS_DIR)) {
      fs.mkdirSync(CONFIG.MIGRATIONS_DIR, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const filename = `${timestamp}_${name}.sql`;
    const filepath = path.join(CONFIG.MIGRATIONS_DIR, filename);
    
    const template = `-- 迁移文件: ${filename}
-- 环境: all
-- 创建时间: ${new Date().toISOString()}
-- 描述: ${name}

-- ==========================================
-- 向前迁移 (UP)
-- ==========================================

-- 在此处添加向前迁移的SQL语句
-- 例如: CREATE TABLE, ALTER TABLE, INSERT等


-- ==========================================
-- 回滚迁移 (DOWN)
-- ==========================================

-- 在此处添加回滚迁移的SQL语句
-- 例如: DROP TABLE, ALTER TABLE, DELETE等
-- 注意: 回滚语句应该能够撤销上面的向前迁移

`;
    
    fs.writeFileSync(filepath, template);
    Logger.success(`迁移文件已创建: ${filepath}`);
    Logger.info('请编辑该文件并添加相应的SQL语句');
  }

  // 备份数据库
  async backup() {
    const backupDir = path.join(CONFIG.BACKUP_DIR, this.environment);
    if (!fs.existsSync(backupDir)) {
      fs.mkdirSync(backupDir, { recursive: true });
    }
    
    const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
    const backupFile = path.join(backupDir, `backup_${timestamp}.db`);
    
    if (fs.existsSync(this.dbPath)) {
      fs.copyFileSync(this.dbPath, backupFile);
      Logger.success(`数据库备份完成: ${backupFile}`);
    } else {
      Logger.warning('数据库文件不存在，无法备份');
    }
  }
}

// 命令行接口
class CLI {
  static async run() {
    const args = process.argv.slice(2);
    const command = args[0];
    const environment = args[1] || 'development';
    
    if (!CONFIG.ENVIRONMENTS.includes(environment)) {
      Logger.error(`无效的环境: ${environment}`);
      Logger.info(`支持的环境: ${CONFIG.ENVIRONMENTS.join(', ')}`);
      process.exit(1);
    }
    
    const manager = new DatabaseVersionManager(environment);
    
    try {
      switch (command) {
        case 'create':
          const name = args[1];
          DatabaseVersionManager.createMigration(name);
          break;
          
        case 'migrate':
          await manager.migrate();
          break;
          
        case 'rollback':
          const steps = parseInt(args[2]) || 1;
          await manager.rollback(steps);
          break;
          
        case 'status':
          await manager.status();
          break;
          
        case 'backup':
          await manager.backup();
          break;
          
        default:
          CLI.showHelp();
          break;
      }
    } catch (err) {
      Logger.error('操作失败:', err);
      process.exit(1);
    } finally {
      await manager.close();
    }
  }
  
  static showHelp() {
    console.log('交易执行铁三角项目数据库版本管理工具');
    console.log('');
    console.log('用法: node scripts/db-version.js <命令> [参数]');
    console.log('');
    console.log('命令:');
    console.log('  create <name>           创建新的迁移文件');
    console.log('  migrate [env]           运行待应用的迁移');
    console.log('  rollback [env] [steps]  回滚迁移 (默认回滚1步)');
    console.log('  status [env]            显示迁移状态');
    console.log('  backup [env]            备份数据库');
    console.log('');
    console.log('环境选项:');
    console.log('  development  - 开发环境 (默认)');
    console.log('  staging      - 预发布环境');
    console.log('  production   - 生产环境');
    console.log('');
    console.log('示例:');
    console.log('  node scripts/db-version.js create add_user_table');
    console.log('  node scripts/db-version.js migrate development');
    console.log('  node scripts/db-version.js rollback production 2');
    console.log('  node scripts/db-version.js status staging');
    console.log('  node scripts/db-version.js backup production');
  }
}

// 如果直接运行此文件
if (require.main === module) {
  CLI.run();
}

module.exports = DatabaseVersionManager;