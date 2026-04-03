from Crypto.Cipher import ARC4
import base64
import httpx
from config import load_config

# Load configuration
config = load_config()
max_connections = config.app.max_connections
max_keepalive_connections = config.app.max_keepalive_connections

async def my_post(url: str, payload: dict, headers: dict = None, encrypt: bool=True):
    """
    通用post请求方法
    :param url:
    :param payload:
    :param headers:
    :param encrypt:
    :return:
    """
    key = config.app.rc4key
    if encrypt:
        payload = rc4_encrypt(payload, key)

        headers = {"Content-Type": "application/json",
                   "api_ver":"2",
                   "api_key":"SELF_QUERY_WEBSRV2"}
    else:
        headers = headers or {"Content-Type": "application/json"}

    limits = httpx.Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive_connections)
    async with httpx.AsyncClient(limits=limits) as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            # 直接抛出原始异常，而不是包装成字符串
            raise e
        except httpx.RequestError as e:
            # 直接抛出原始异常
            raise e
        except Exception as e:
            # 直接抛出原始异常
            raise e


def rc4_encrypt(data, key):
    if not isinstance(data, str):
        data = str(data)
    cipher = ARC4.new(key.encode('utf-8'))
    encrypted_data = cipher.encrypt(data.encode('utf-8'))
    return base64.b64encode(encrypted_data).decode('utf-8')

# if __name__ == '__main__':
#     data = {
#             "head": {
#                 "user": "baoyaoyao",
#                 "requestType": "SELF_QUERY_WEBSRV2"
#             },
#             "body": {
#                 "serviceCd": "idxDetail",
#                 "params": {
#                     "indx_cd": "unv"
#                 }
#             }
#         }
#     key = "FullG@l2025"
#     response = rc4_encrypt(data, key)
#     print(response)