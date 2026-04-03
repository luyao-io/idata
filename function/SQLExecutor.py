import json
import pandas as pd
import os
from dotenv import load_dotenv

from config.context import request_user
from function.APIRequest import my_post
import asyncio
import re

load_dotenv()

from config import load_config

# 加载配置
config = load_config()
timeout = config.app.time_out

async def run_sql(sql: str) -> pd.DataFrame:
    """
    执行SQL查询并返回结果数据框

    Args:
        sql (str): 要执行的SQL查询语句

    Returns:
        pd.DataFrame: 查询结果的数据框
    """
    try:
        # 从配置获取用户信息
        # user = config.app.user
        user = request_user.get()
        # 强制添加limit限制，防止返回过多数据
        # 移除可能存在的分号
        sql = sql.rstrip(';')
        top_k = config.app.maxResultSize
        # 检查SQL是否已经包含LIMIT子句
        # 使用正则表达式检查是否已存在LIMIT子句（忽略大小写）
        has_limit = re.search(r'\bLIMIT\s+\d+\b', sql, re.IGNORECASE)

        # 只有在SQL中没有LIMIT子句时才添加LIMIT
        if not has_limit:
            sql = f"{sql} LIMIT {top_k}"

        # 构造请求负载
        payload = {
            "head": {
                "user": user,
                "requestType": "SELF_QUERY2"
            },
            "body": {
                "originSql": sql,
                "params": {}
            }
        }

        # 获取API URL
        url = config.app.post_url

        # 发送POST请求，设置超时时间
        response = await asyncio.wait_for(my_post(url, payload), timeout=timeout)

        # 检查响应是否为字符串（错误信息）
        if isinstance(response, str):
            error_info = [{"message": f"API请求失败: {response}"}]
            return pd.DataFrame(error_info)

        # 获取响应内容
        response_content = response.content
        response_str = response_content.decode('utf-8')

        # 解析JSON响应
        result = json.loads(response_str)

        # 检查响应是否包含错误信息
        if 'head' in result and 'msgInfo' in result['head']:
            msg_info = result['head']['msgInfo']
            # 检查是否有错误
            if result['head'].get('resFlag') == 'F':
                error_info = [{"message": msg_info}]
                return pd.DataFrame(error_info)

        # 检查响应结构并提取数据
        if 'body' in result and 'data' in result['body']:
            df = pd.DataFrame(result['body']['data'])
            # 确保即使SQL中没有limit，返回的结果也不会超过top_k行
            # 但如果有LIMIT子句，则尊重用户指定的限制
            if not has_limit and len(df) > top_k:
                df = df.head(top_k)
            return df
        else:
            # 如果没有数据，返回空DataFrame
            return pd.DataFrame()

    except asyncio.TimeoutError:
        # 处理超时情况
        timeout_info = [{"message": f"执行 API 请求超时，超时时间为：{timeout}秒"}]
        return pd.DataFrame(timeout_info)
    except json.JSONDecodeError as e:
        # 处理JSON解析错误
        error_info = [{"message": f"JSON解析错误: {str(e)}"}]
        return pd.DataFrame(error_info)
    except Exception as e:
        # 处理其他异常
        error_info = [{"message": f"执行 API 请求时出错: {str(e)}"}]
        return pd.DataFrame(error_info)

# if __name__ == "__main__":
#     # 示例用法
#     request_user.set("baoyaoyao")
#     sql = "SELECT * FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx a left join dtlab_r.v_dws_mkt_all_chnn_trd_indx b on 1=1"
#     result = asyncio.run(run_sql(sql))
#     print(result)