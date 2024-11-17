import sqlite3
import bcrypt
from datetime import datetime
import json
from psycopg2.extras import DictCursor

class Database:
    def __init__(self, db_file="chat_app.db"):
        self.db_file = db_file
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        """初始化数据库表"""
        conn = self.get_connection()
        c = conn.cursor()
        
        # 创建用户表
        c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建会话表
        c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT NOT NULL,
            title TEXT,
            chat_history TEXT,
            chat_context TEXT,
            timestamp TIMESTAMP,
            is_favorite BOOLEAN DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 创建用户设置表
        c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT,
            api_base TEXT,
            model TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # 检查是否存在默认管理员账户
        c.execute('SELECT 1 FROM users WHERE username = "admin"')
        if not c.fetchone():
            # 创建默认管理员账户，密码为 "admin123"
            hashed = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt())
            c.execute('''
            INSERT INTO users (username, password, is_admin)
            VALUES (?, ?, 1)
            ''', ("admin", hashed.decode('utf-8')))
        
        conn.commit()
        conn.close()
    
    def register_user(self, username, password):
        """注册新用户"""
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # 检查用户名是否已存在
            c.execute('SELECT 1 FROM users WHERE username = ?', (username,))
            if c.fetchone():
                return False, "用户名已存在"
            
            # 对密码进行加密
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # 插入新用户
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                     (username, hashed.decode('utf-8')))
            
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
            c = conn.cursor()
            
            c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
            result = c.fetchone()
            
            if result and bcrypt.checkpw(password.encode('utf-8'), result[1].encode('utf-8')):
                return True, result[0]  # 返回用户ID
            return False, None
        finally:
            conn.close()
    
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
                """， (user_id,))
                result = c.fetchone()
                return result if result else {}
        except Exception as e:
            print(f"获取用户设置出错: {str(e)}")
            return {}
        finally:
            conn.close()
    
    def test_connection(self):
        """测试数据库连接"""
        try:
            conn = self.get_connection()
            with conn.cursor() as c:
                # 测试查询
                c.execute('SELECT version()')
                version = c.fetchone()
                print("数据库连接成功!")
                print(f"PostgreSQL 版本: {version[0]}")
                
                # 测试表是否存在
                c.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                tables = c.fetchall()
                print("\n现有数据表:")
                for table in tables:
                    print(f"- {table[0]}")
                
                return True
        except Exception as e:
            print(f"数据库连接错误: {str(e)}")
            return False
        finally:
            if 'conn' in locals():
                conn.close() 
