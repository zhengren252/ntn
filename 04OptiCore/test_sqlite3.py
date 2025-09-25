#!/usr/bin/env python3
"""
快速测试 sqlite3 标准库导入
Test sqlite3 standard library import
"""

def test_sqlite3_import():
    """测试 sqlite3 模块是否可以正常导入和使用"""
    try:
        import sqlite3
        print("✅ sqlite3 模块导入成功")
        
        # 创建内存数据库连接测试
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()
        
        # 创建测试表
        cursor.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        
        # 插入测试数据
        cursor.execute("INSERT INTO test_table (name) VALUES (?)", ("test_name",))
        conn.commit()
        
        # 查询测试数据
        cursor.execute("SELECT * FROM test_table")
        result = cursor.fetchall()
        
        if result:
            print(f"✅ sqlite3 数据库操作成功: {result}")
        else:
            print("❌ sqlite3 数据库操作失败")
            
        conn.close()
        print("✅ sqlite3 测试完成，模块工作正常")
        return True
        
    except ImportError as e:
        print(f"❌ sqlite3 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ sqlite3 操作失败: {e}")
        return False

if __name__ == "__main__":
    print("=== OptiCore sqlite3 模块测试 ===")
    success = test_sqlite3_import()
    exit(0 if success else 1)