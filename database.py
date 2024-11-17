import psycopg2
from psycopg2.extras import Json, DictCursor
import streamlit as st
from datetime import datetime
import json
import bcrypt

class Database:
    def __init__(self):
        try:
            # 打印连接参数（注意隐藏密码）
            connection_params = st.secrets["postgres"]
            print(f"数据库连接参数: host={connection_params['host']}, port={connection_params['port']}, user={connection_params['user']}, database={connection_params['database']}")
        except Exception as e:
            print(f"初始化数据库时出错: {str(e)}")
            raise e

    def get_connection(self):
        try:
            conn = psycopg2.connect(
                host=st.secrets["postgres"]["host"],
                port=st.secrets["postgres"]["port"],
                user=st.secrets["postgres"]["user"],
                password=st.secrets["postgres"]["password"],
                database=st.secrets["postgres"]["database"]
            )
            return conn
        except Exception as e:
            print(f"获取数据库连接时出错: {str(e)}")
            raise e

    def test_connection(self):
        """测试数据库连接"""
        try:
            print("开始测试数据库连接...")
            conn = self.get_connection()
            with conn.cursor() as c:
                print("执行测试查询...")
                c.execute('SELECT version()')
                version = c.fetchone()
                print(f"数据库连接成功! PostgreSQL 版本: {version[0]}")
                
                # 测试表是否存在
                print("检查数据表...")
                c.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = c.fetchall()
                print("现有数据表:")
                for table in tables:
                    print(f"- {table[0]}")
                
                return True
        except Exception as e:
            print(f"数据库连接测试失败: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                print("数据库连接已关闭") 
