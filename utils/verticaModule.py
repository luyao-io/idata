import vertica_python
import pandas as pd
import os
from config.loader import load_config
import asyncio

# 加载配置
config = load_config()


class VerticaDatabase:
    def __init__(self, user=None, password=None):
        """
        初始化Vertica数据库连接类
        
        Args:
            user (str, optional): 数据库用户名
            password (str, optional): 数据库密码
        """
        # 默认的连接信息
        self.conn_info = {
            "database": config.verticadb.database,
            "host": config.verticadb.host,
            "port": config.verticadb.port,
            "user": user,
            "password": password,
            "tlsmode": config.verticadb.tlsmode
        }
  
    async def execute_query(self, query):
        """异步执行查询语句并返回结果"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_execute_query, query)
    
    def _sync_execute_query(self, query):
        """同步执行查询语句并返回结果"""
        with vertica_python.connect(**self.conn_info) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            return pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])

    async def execute_dml(self, query):
        """异步执行DML语句"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_execute_dml, query)
    
    def _sync_execute_dml(self, query):
        """同步执行DML语句"""
        with vertica_python.connect(**self.conn_info) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()

    async def execute_sql_file(self, sqlpath):
        """异步执行SQL文件"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_execute_sql_file, sqlpath)
    
    def _sync_execute_sql_file(self, sqlpath):
        """同步执行SQL文件"""
        conn = None
        cursor = None
        try:
            with open(sqlpath, 'r', encoding='utf-8') as file:
                print('读取sql文件：')
                view_cfg = file.read()
                conn = vertica_python.connect(**self.conn_info)
                cursor = conn.cursor()
                for command in view_cfg.split(';'):
                    if command.strip():
                        print('开始执行：', command)
                        cursor.execute(command)
                conn.commit()
        except Exception as err:
            print("执行sql出错，错误是 " + str(err))
        finally:
            # 关闭游标
            if cursor:
                cursor.close()
            # 关闭连接
            if conn:
                conn.close()
