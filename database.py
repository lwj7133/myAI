import psycopg2
from psycopg2.extras import Json, DictCursor
import streamlit as st
from datetime import datetime
import json
import bcrypt

class Database:
    def __init__(self):
        try:
            self.connection_string = st.secrets["postgres"]["connection_string"]
            print("数据库连接字符串已加载")
        except Exception as e:
            print(f"初始化数据库时出错: {str(e)}")
            raise e

    def get_connection(self):
        try:
            return psycopg2.connect(self.connection_string)
        except Exception as e:
            print(f"获取数据库连接时出错: {str(e)}")
            raise e

    def register_user(self, username, password, is_admin=False):
        """注册新用户"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查用户名是否已存在
            cursor.execute('SELECT 1 FROM users WHERE username = %s', (username,))
            if cursor.fetchone():
                return False, "用户名已存在"
            
            # 对密码进行加密
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # 插入新用户
            cursor.execute("""
                INSERT INTO users (username, password, is_admin) 
                VALUES (%s, %s, %s) 
                RETURNING id
            """, (username, hashed.decode('utf-8'), is_admin))
            
            user_id = cursor.fetchone()[0]
            conn.commit()
            return True, "注册成功"
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"注册用户时出错: {str(e)}")
            return False, f"注册失败: {str(e)}"
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def verify_user(self, username, password):
        """验证用户登录"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # 查询用户
            cursor.execute("""
                SELECT id, password, is_admin 
                FROM users 
                WHERE username = %s
            """, (username,))
            
            result = cursor.fetchone()
            
            if result:
                stored_password = result['password'].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_password):
                    return True, result['id']
            return False, None
            
        except Exception as e:
            print(f"验证用户时出错: {str(e)}")
            return False, None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def create_admin_if_not_exists(self):
        """确保管理员账户存在"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 检查管理员是否存在
            cursor.execute('SELECT 1 FROM users WHERE username = %s', ('admin',))
            if not cursor.fetchone():
                # 创建默认管理员账户
                hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
                cursor.execute("""
                    INSERT INTO users (username, password, is_admin) 
                    VALUES (%s, %s, %s)
                """, ('admin', hashed.decode('utf-8'), True))
                conn.commit()
                print("已创建默认管理员账户")
                
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"创建管理员账户时出错: {str(e)}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def test_connection(self):
        """测试数据库连接"""
        conn = None
        try:
            print("开始测试数据库连接...")
            conn = self.get_connection()
            cursor = conn.cursor()
            
            print("执行测试查询...")
            cursor.execute('SELECT version()')
            version = cursor.fetchone()
            print(f"数据库连接成功! PostgreSQL 版本: {version[0]}")
            
            # 测试表是否存在
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            print("现有数据表:")
            for table in tables:
                print(f"- {table[0]}")
            
            return True
            
        except Exception as e:
            print(f"数据库连接测试失败: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
            print("数据库连接已关闭")
    
    def save_user_sessions(self, user_id, sessions):
        """保存用户的会话数据"""
        try:
            # 将会话数据转换为JSON字符串
            sessions_json = json.dumps(sessions, ensure_ascii=False)
            
            # 更新数据库中的会话数据
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_sessions (user_id, sessions)
                    VALUES (?, ?)
                """, (user_id, sessions_json))
                conn.commit()
            return True
        except Exception as e:
            print(f"保存会话数据时出错: {str(e)}")
            return False
    
    def load_user_sessions(self, user_id):
        """加载用户的会话数据"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as c:
                c.execute("""
                    SELECT session_id, title, chat_history, chat_context, 
                           timestamp, is_favorite 
                    FROM sessions 
                    WHERE user_id = %s
                    ORDER BY timestamp DESC
                """, (user_id,))
                
                results = c.fetchall()
                
                # 将查询结果转换为字典格式
                sessions = {}
                for row in results:
                    sessions[row['session_id']] = {
                        'title': row['title'],
                        'chat_history': row['chat_history'],
                        'chat_context': row['chat_context'],
                        'timestamp': row['timestamp'].isoformat() if row['timestamp'] else None,
                        'is_favorite': row['is_favorite']
                    }
                
                return sessions
        except Exception as e:
            print(f"加载会话出错: {str(e)}")
            return {}  # 返回空字典而不是 None
        finally:
            conn.close()
    
    def save_user_settings(self, user_id, api_key, api_base, model):
        """保存用户的API设置"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute('''
            INSERT OR REPLACE INTO user_settings (user_id, api_key, api_base, model)
            VALUES (?, ?, ?, ?)
            ''', (user_id, api_key, api_base, model))
            
            conn.commit()
            return True, "设置保存成功"
        except Exception as e:
            return False, f"保存失败: {str(e)}"
        finally:
            conn.close()
    
    def load_user_settings(self, user_id):
        """加载用户的API设置"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute('SELECT api_key, api_base, model FROM user_settings WHERE user_id = ?',
                     (user_id,))
            result = c.fetchone()
            
            if result:
                return {
                    'api_key': result[0],
                    'api_base': result[1],
                    'model': result[2]
                }
            return None
        finally:
            conn.close()
    
    def verify_admin(self, user_id):
        """验证用户是否为管理员"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
            result = c.fetchone()
            
            return bool(result and result[0])
        finally:
            conn.close()
    
    def get_all_users(self):
        """获取所有用户信息"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute('''
            SELECT id, username, is_admin, created_at 
            FROM users
            ORDER BY created_at DESC
            ''')
            
            return c.fetchall()
        finally:
            conn.close()
    
    def delete_user(self, user_id):
        """删除用户"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # 删除用户的所有会话
            c.execute('DELETE FROM sessions WHERE user_id = ?', (user_id,))
            # 删除用户的设置
            c.execute('DELETE FROM user_settings WHERE user_id = ?', (user_id,))
            # 删除用户
            c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            
            conn.commit()
            return True, "用户删除成功"
        except Exception as e:
            return False, f"删除失败: {str(e)}"
        finally:
            conn.close()
    
    def toggle_admin_status(self, user_id):
        """切换用户的管理员状态"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # 获取当前管理员状态
            c.execute('SELECT is_admin FROM users WHERE id = ?', (user_id,))
            current_status = c.fetchone()[0]
            
            # 切换状态
            new_status = not bool(current_status)
            c.execute('UPDATE users SET is_admin = ? WHERE id = ?', (new_status, user_id))
            
            conn.commit()
            return True, "管理员状态更新成功"
        except Exception as e:
            return False, f"更新失败: {str(e)}"
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as c:
                c.execute('SELECT id, username, is_admin FROM users WHERE id = %s', (user_id,))
                result = c.fetchone()
                return result
        except Exception as e:
            print(f"获取用户信息出错: {str(e)}")
            return None
        finally:
            conn.close()
    
    def get_user_settings(self, user_id):
        """获取用户设置"""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as c:
                c.execute("""
                    SELECT api_key, api_base, model 
                    FROM user_settings 
                    WHERE user_id = %s
                """, (user_id,))
                result = c.fetchone()
                return result if result else {}
        except Exception as e:
            print(f"获取用户设置出错: {str(e)}")
            return {}
        finally:
            conn.close() 
