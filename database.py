import psycopg2
from psycopg2.extras import Json, DictCursor
import bcrypt
from datetime import datetime
import json
import streamlit as st

class Database:
    def __init__(self):
        # 从 Streamlit Secrets 获取数据库配置
        self.connection_params = st.secrets["postgres"]
    
    def get_connection(self):
        return psycopg2.connect(
            host=self.connection_params["host"],
            port=self.connection_params["port"],
            user=self.connection_params["user"],
            password=self.connection_params["password"],
            database=self.connection_params["database"]
        )
    
    def register_user(self, username, password):
        """注册新用户"""
        try:
            conn = self.get_connection()
            with conn.cursor() as c:
                # 检查用户名是否已存在
                c.execute('SELECT 1 FROM users WHERE username = %s', (username,))
                if c.fetchone():
                    return False, "用户名已存在"
                
                # 对密码进行加密
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                
                # 插入新用户
                c.execute(
                    'INSERT INTO users (username, password) VALUES (%s, %s)',
                    (username, hashed.decode('utf-8'))
                )
                conn.commit()
                return True, "注册成功"
        except Exception as e:
            return False, f"注册失败: {str(e)}"
        finally:
            conn.close()
    
    def verify_user(self, username, password):
        """验证用户登录"""
        try:
            conn = self.get_connection()
            with conn.cursor() as c:
                c.execute('SELECT id, password FROM users WHERE username = %s', (username,))
                result = c.fetchone()
                
                if result and bcrypt.checkpw(password.encode('utf-8'), result[1].encode('utf-8')):
                    return True, result[0]  # 返回用户ID
                return False, None
        finally:
            conn.close()
    
    def save_user_sessions(self, user_id, sessions_data):
        """保存用户的会话数据"""
        try:
            conn = self.get_connection()
            with conn.cursor() as c:
                # 先删除用户的旧会话
                c.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
                
                # 插入新的会话数据
                for session_id, session in sessions_data.items():
                    c.execute("""
                        INSERT INTO sessions 
                        (user_id, session_id, title, chat_history, chat_context, timestamp, is_favorite)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        session_id,
                        session.get('title', '新会话'),
                        Json(session.get('chat_history', [])),
                        Json(session.get('chat_context', [])),
                        session.get('timestamp'),
                        session.get('is_favorite', False)
                    ))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"保存会话出错: {str(e)}")
            return False
        finally:
            conn.close() 
