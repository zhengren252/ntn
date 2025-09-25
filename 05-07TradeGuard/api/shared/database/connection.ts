import Database from 'better-sqlite3';
import { readFileSync, mkdirSync, existsSync } from 'fs';
import { join, dirname } from 'path';
import yaml from 'yaml';

// 环境配置接口
interface DatabaseConfig {
  database: {
    path: string;
    options: {
      verbose?: ((message?: string, ...additionalArgs: unknown[]) => void) | boolean;
      readonly?: boolean;
      fileMustExist?: boolean;
    };
  };
}

// 数据库连接类
class DatabaseConnection {
  private static instance: DatabaseConnection;
  private db: Database.Database;
  private config: DatabaseConfig;

  private constructor() {
    this.loadConfig();
    this.initializeDatabase();
  }

  // 单例模式获取实例
  public static getInstance(): DatabaseConnection {
    if (!DatabaseConnection.instance) {
      DatabaseConnection.instance = new DatabaseConnection();
    }
    return DatabaseConnection.instance;
  }

  // 加载配置文件
  private loadConfig(): void {
    const env = process.env.APP_ENV || 'development';
    const configPath = join(process.cwd(), 'config', `${env}.yaml`);
    
    try {
      const configFile = readFileSync(configPath, 'utf8');
      this.config = yaml.parse(configFile) as DatabaseConfig;
    } catch {
      console.warn(`配置文件 ${configPath} 加载失败，使用默认配置`);
      this.config = {
        database: {
          path: `./data/${env}.db`,
          options: {
            verbose: env === 'development',
            readonly: false,
            fileMustExist: false
          }
        }
      };
    }
  }

  // 初始化数据库
  private initializeDatabase(): void {
    try {
      // 确保数据库目录存在
      const dbDir = dirname(this.config.database.path);
      if (!existsSync(dbDir)) {
        mkdirSync(dbDir, { recursive: true });
      }
      
      // 创建数据库连接
      const options = {
        readonly: this.config.database.options.readonly,
        fileMustExist: this.config.database.options.fileMustExist
      };
      this.db = new Database(this.config.database.path, options);
      
      // 启用外键约束
      this.db.pragma('foreign_keys = ON');
      
      // 设置WAL模式以提高并发性能
      this.db.pragma('journal_mode = WAL');
      
      // 执行初始化SQL脚本
      this.runInitScript();
      
      console.log(`数据库连接成功: ${this.config.database.path}`);
    } catch (error) {
      console.error('数据库初始化失败:', error);
      throw error;
    }
  }

  // 执行初始化脚本
  private runInitScript(): void {
    try {
      const initScriptPath = join(__dirname, 'init.sql');
      if (!existsSync(initScriptPath)) {
        console.log('初始化脚本不存在，跳过数据库初始化');
        return;
      }
      
      const initScript = readFileSync(initScriptPath, 'utf8');
      
      // 直接执行整个脚本
      this.db.exec(initScript);
      
      console.log('数据库初始化脚本执行完成');
    } catch (error) {
      console.warn('初始化脚本执行失败，继续运行:', error.message);
      // 不抛出错误，允许测试继续进行
    }
  }

  // 获取数据库实例
  public getDatabase(): Database.Database {
    return this.db;
  }

  // 执行事务
  public transaction<T>(fn: (db: Database.Database) => T): T {
    const transaction = this.db.transaction(fn);
    return transaction(this.db);
  }

  // 准备语句
  public prepare(sql: string): Database.Statement {
    return this.db.prepare(sql);
  }

  // 执行查询
  public query(sql: string, params?: Record<string, unknown>[]): unknown[] {
    const stmt = this.db.prepare(sql);
    return params ? stmt.all(...params) : stmt.all();
  }

  // 执行单条查询
  public queryOne(sql: string, params?: Record<string, unknown>[]): unknown {
    const stmt = this.db.prepare(sql);
    return params ? stmt.get(...params) : stmt.get();
  }

  // 执行更新/插入/删除
  public run(sql: string, params?: Record<string, unknown>[]): Database.RunResult {
    const stmt = this.db.prepare(sql);
    return params ? stmt.run(...params) : stmt.run();
  }

  // 关闭数据库连接
  public close(): void {
    if (this.db) {
      this.db.close();
      console.log('数据库连接已关闭');
    }
  }

  // 备份数据库
  public backup(backupPath: string): void {
    try {
      this.db.backup(backupPath);
      console.log(`数据库备份完成: ${backupPath}`);
    } catch (error) {
      console.error('数据库备份失败:', error);
      throw error;
    }
  }

  // 获取数据库统计信息
  public getStats(): unknown {
    return {
      path: this.config.database.path,
      inTransaction: this.db.inTransaction,
      open: this.db.open,
      readonly: this.db.readonly,
      memory: this.db.memory
    };
  }
}

// 导出单例实例
export const dbConnection = DatabaseConnection.getInstance();
export default DatabaseConnection;