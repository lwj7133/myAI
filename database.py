import psycopg2
from psycopg2.extras import Json, DictCursor
import streamlit as st
from datetime import datetime
import json
import bcrypt

class Database:
    def __init__(self):
        try:
            # 使用直接连接字符串
            self.connection_string = st.secrets["postgres"]["connection_string"]
            print("数据库连接字符串已加载")
        except Exception as e:
            print(f"初始化数据库时出错: {str(e)}")
            raise e

    def get_connection(self):
        try:
            conn = psycopg2.connect(self.connection_string)
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
                return True
        except Exception as e:
            print(f"数据库连接测试失败: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
                print("数据库连接已关闭")
