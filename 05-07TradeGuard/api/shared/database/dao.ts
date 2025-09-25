import { dbConnection } from './connection';
import { DatabaseResult, PaginationParams, PaginatedResult, QueryFilter } from './models';
import Database from 'better-sqlite3';

// 基础DAO类
export abstract class BaseDAO<T = Record<string, unknown>> {
  protected db: Database.Database;
  protected tableName: string;

  constructor(tableName: string) {
    this.db = dbConnection.getDatabase();
    this.tableName = tableName;
  }

  // 查询所有记录
  public findAll(filters?: QueryFilter[], pagination?: PaginationParams): PaginatedResult<T> | T[] {
    try {
      let sql = `SELECT * FROM ${this.tableName}`;
      const params: unknown[] = [];

      // 添加过滤条件
      if (filters && filters.length > 0) {
        const whereClause = this.buildWhereClause(filters, params);
        sql += ` WHERE ${whereClause}`;
      }

      // 如果有分页参数
      if (pagination) {
        // 获取总数
        const countSql = sql.replace('SELECT *', 'SELECT COUNT(*) as total');
        const countResult = this.db.prepare(countSql).get(...params) as { total: number };
        const total = countResult.total;

        // 添加排序和分页
        if (pagination.sortBy) {
          sql += ` ORDER BY ${pagination.sortBy} ${pagination.sortOrder || 'ASC'}`;
        }
        sql += ` LIMIT ? OFFSET ?`;
        params.push(pagination.pageSize, (pagination.page - 1) * pagination.pageSize);

        const data = this.db.prepare(sql).all(...params) as T[];
        
        return {
          data,
          total,
          page: pagination.page,
          pageSize: pagination.pageSize,
          totalPages: Math.ceil(total / pagination.pageSize)
        };
      }

      return this.db.prepare(sql).all(...params) as T[];
    } catch (error) {
      console.error(`查询 ${this.tableName} 失败:`, error);
      throw error;
    }
  }

  // 根据ID查询单条记录
  public findById(id: number): T | null {
    try {
      const sql = `SELECT * FROM ${this.tableName} WHERE id = ?`;
      const result = this.db.prepare(sql).get(id) as T;
      return result || null;
    } catch (error) {
      console.error(`根据ID查询 ${this.tableName} 失败:`, error);
      throw error;
    }
  }

  // 根据条件查询单条记录
  public findOne(filters: QueryFilter[]): T | null {
    try {
      let sql = `SELECT * FROM ${this.tableName}`;
      const params: unknown[] = [];

      if (filters && filters.length > 0) {
        const whereClause = this.buildWhereClause(filters, params);
        sql += ` WHERE ${whereClause}`;
      }

      sql += ' LIMIT 1';
      const result = this.db.prepare(sql).get(...params) as T;
      return result || null;
    } catch (error) {
      console.error(`查询单条 ${this.tableName} 记录失败:`, error);
      throw error;
    }
  }

  // 插入记录
  public create(data: Partial<T>): DatabaseResult {
    try {
      const fields = Object.keys(data).filter(key => key !== 'id');
      const placeholders = fields.map(() => '?').join(', ');
      const sql = `INSERT INTO ${this.tableName} (${fields.join(', ')}) VALUES (${placeholders})`;
      const values = fields.map(field => (data as Record<string, unknown>)[field]);

      const result = this.db.prepare(sql).run(...values);
      
      return {
        success: true,
        lastInsertId: result.lastInsertRowid as number,
        rowsAffected: result.changes
      };
    } catch (error) {
      console.error(`插入 ${this.tableName} 失败:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 批量插入
  public createMany(dataList: Partial<T>[]): DatabaseResult {
    if (!dataList || dataList.length === 0) {
      return { success: false, error: '数据列表为空' };
    }

    try {
      const fields = Object.keys(dataList[0]).filter(key => key !== 'id');
      const placeholders = fields.map(() => '?').join(', ');
      const sql = `INSERT INTO ${this.tableName} (${fields.join(', ')}) VALUES (${placeholders})`;
      
      const stmt = this.db.prepare(sql);
      const transaction = this.db.transaction((data: Partial<T>[]) => {
        let totalChanges = 0;
        for (const item of data) {
          const values = fields.map(field => (item as unknown)[field]);
          const result = stmt.run(...values);
          totalChanges += result.changes;
        }
        return totalChanges;
      });

      const totalChanges = transaction(dataList);
      
      return {
        success: true,
        rowsAffected: totalChanges
      };
    } catch (error) {
      console.error(`批量插入 ${this.tableName} 失败:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 更新记录
  public update(id: number, data: Partial<T>): DatabaseResult {
    try {
      const fields = Object.keys(data).filter(key => key !== 'id');
      if (fields.length === 0) {
        return { success: false, error: '没有要更新的字段' };
      }

      const setClause = fields.map(field => `${field} = ?`).join(', ');
      const sql = `UPDATE ${this.tableName} SET ${setClause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?`;
      const values = [...fields.map(field => (data as Record<string, unknown>)[field]), id];

      const result = this.db.prepare(sql).run(...values);
      
      return {
        success: result.changes > 0,
        rowsAffected: result.changes
      };
    } catch (error) {
      console.error(`更新 ${this.tableName} 失败:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 删除记录
  public delete(id: number): DatabaseResult {
    try {
      const sql = `DELETE FROM ${this.tableName} WHERE id = ?`;
      const result = this.db.prepare(sql).run(id);
      
      return {
        success: result.changes > 0,
        rowsAffected: result.changes
      };
    } catch (error) {
      console.error(`删除 ${this.tableName} 失败:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 根据条件删除
  public deleteWhere(filters: QueryFilter[]): DatabaseResult {
    try {
      let sql = `DELETE FROM ${this.tableName}`;
      const params: unknown[] = [];

      if (filters && filters.length > 0) {
        const whereClause = this.buildWhereClause(filters, params);
        sql += ` WHERE ${whereClause}`;
      } else {
        return { success: false, error: '删除操作必须指定条件' };
      }

      const result = this.db.prepare(sql).run(...params);
      
      return {
        success: true,
        rowsAffected: result.changes
      };
    } catch (error) {
      console.error(`条件删除 ${this.tableName} 失败:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }

  // 统计记录数
  public count(filters?: QueryFilter[]): number {
    try {
      let sql = `SELECT COUNT(*) as total FROM ${this.tableName}`;
      const params: unknown[] = [];

      if (filters && filters.length > 0) {
        const whereClause = this.buildWhereClause(filters, params);
        sql += ` WHERE ${whereClause}`;
      }

      const result = this.db.prepare(sql).get(...params) as { total: number };
      return result.total;
    } catch (error) {
      console.error(`统计 ${this.tableName} 记录数失败:`, error);
      throw error;
    }
  }

  // 检查记录是否存在
  public exists(filters: QueryFilter[]): boolean {
    return this.count(filters) > 0;
  }

  // 构建WHERE子句
  private buildWhereClause(filters: QueryFilter[], params: unknown[]): string {
    const conditions: string[] = [];

    for (const filter of filters) {
      switch (filter.operator) {
        case 'eq':
          conditions.push(`${filter.field} = ?`);
          params.push(filter.value);
          break;
        case 'ne':
          conditions.push(`${filter.field} != ?`);
          params.push(filter.value);
          break;
        case 'gt':
          conditions.push(`${filter.field} > ?`);
          params.push(filter.value);
          break;
        case 'gte':
          conditions.push(`${filter.field} >= ?`);
          params.push(filter.value);
          break;
        case 'lt':
          conditions.push(`${filter.field} < ?`);
          params.push(filter.value);
          break;
        case 'lte':
          conditions.push(`${filter.field} <= ?`);
          params.push(filter.value);
          break;
        case 'like':
          conditions.push(`${filter.field} LIKE ?`);
          params.push(`%${filter.value}%`);
          break;
        case 'in':
          if (Array.isArray(filter.value)) {
            const placeholders = filter.value.map(() => '?').join(', ');
            conditions.push(`${filter.field} IN (${placeholders})`);
            params.push(...filter.value);
          }
          break;
        case 'between':
          if (Array.isArray(filter.value) && filter.value.length === 2) {
            conditions.push(`${filter.field} BETWEEN ? AND ?`);
            params.push(filter.value[0], filter.value[1]);
          }
          break;
      }
    }

    return conditions.join(' AND ');
  }

  // 执行原生SQL查询
  public executeQuery(sql: string, params?: unknown[]): T[] {
    try {
      const stmt = this.db.prepare(sql);
      const result = params ? stmt.all(...params) : stmt.all();
      return result as T[];
    } catch (error) {
      console.error('执行查询失败:', error);
      throw error;
    }
  }

  // 执行原生SQL命令
  public executeCommand(sql: string, params?: unknown[]): DatabaseResult {
    try {
      const stmt = this.db.prepare(sql);
      const result = params ? stmt.run(...params) : stmt.run();
      
      return {
        success: true,
        rowsAffected: result.changes,
        lastInsertId: result.lastInsertRowid as number
      };
    } catch (error) {
      console.error('执行命令失败:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : '未知错误'
      };
    }
  }
}

// 导出基础DAO类
export default BaseDAO;