"""
SQLAgent 文件系统工具 - 限制在用户空间内操作
提供 read_file, write_file, edit_file, list_directory 四个工具
只允许操作用户各自空间内的文件
"""

import os
from pathlib import Path
from typing import Any, Dict
from langchain.tools import tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from config.context import request_user
from config.context import  request_user

def _resolve_user_path(path: str) -> Path:
    """
    安全路径解析 - 只允许在用户空间内操作
    """
    # 获取当前用户ID
    user_id = request_user.get()
    
    # 用户空间基目录
    base_path = Path(f"longtermmemory/users/{user_id}/skills").resolve()
    print('base_path:', base_path)
    # 处理相对路径
    target_path = (base_path / path).resolve()
    print('target_path:',target_path)
    # 验证路径是否在用户空间内
    try:
        target_path.relative_to(base_path)
    except ValueError:
        raise PermissionError(f"Path '{path}' is outside allowed user space for user '{user_id}'")

    return target_path


@tool
def read_file(path: str) -> str:
    """
    读取用户空间内的文件内容。

    参数:
    - path: 文件路径，相对于用户技能目录 (skills/users/{user_id}/)
    """
    try:
        file_path = _resolve_user_path(path)

        if not file_path.exists():
            return f"Error: File not found: {path}"

        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        content = file_path.read_text(encoding="utf-8")
        return f"File: {path}\n\n{content}"

    except PermissionError as e:
        return f"Permission Error: {str(e)}"
    except UnicodeDecodeError:
        return f"Error: Cannot decode file as UTF-8: {path}"
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool
def write_file(path: str, content: str) -> str:
    """
    在用户空间内写入文件内容。

    参数:
    - path: 文件路径，相对于用户技能目录 (skills/users/{user_id}/)
    - content: 要写入的内容
    """
    try:
        file_path = _resolve_user_path(path)

        # 创建父目录（如果不存在）
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入文件
        file_path.write_text(content, encoding="utf-8")

        return f"Successfully wrote {len(content)} characters to {path}"

    except PermissionError as e:
        return f"Permission Error: {str(e)}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool
def edit_file(path: str, old_text: str, new_text: str) -> str:
    """
    编辑用户空间内的文件内容 - 替换文本。

    参数:
    - path: 文件路径，相对于用户技能目录 (skills/users/{user_id}/)
    - old_text: 要替换的原文
    - new_text: 新文本
    """
    try:
        file_path = _resolve_user_path(path)

        if not file_path.exists():
            return f"Error: File not found: {path}"

        if not file_path.is_file():
            return f"Error: Path is not a file: {path}"

        content = file_path.read_text(encoding="utf-8")

        if old_text not in content:
            return f"Error: Text not found in file '{path}': {old_text[:100]}..."

        # 计算出现次数，如果是多个匹配则警告
        count = content.count(old_text)
        if count > 1:
            return f"Warning: Text appears {count} times in file. Please be more specific to avoid unintended replacements."

        new_content = content.replace(old_text, new_text, 1)
        file_path.write_text(new_content, encoding="utf-8")

        return f"Successfully edited {path}"

    except PermissionError as e:
        return f"Permission Error: {str(e)}"
    except Exception as e:
        return f"Error editing file: {str(e)}"


@tool
def list_directory(path: str = ".") -> str:
    """
    列出用户空间内的目录内容。

    参数:
    - path: 目录路径，相对于用户技能目录 (skills/users/{user_id}/)
    """
    try:
        dir_path = _resolve_user_path(path)

        if not dir_path.exists():
            return f"Error: Directory not found: {path}"

        if not dir_path.is_dir():
            return f"Error: Path is not a directory: {path}"

        # 获取目录项
        items = []
        for item in dir_path.iterdir():
            if item.is_dir():
                items.append(f"DIR  {item.name}/")
            else:
                try:
                    size = item.stat().st_size
                    items.append(f"FILE {item.name:<30} ({size} bytes)")
                except:
                    items.append(f"FILE {item.name}")

        if not items:
            return f"Directory: {path}\nEmpty directory."

        return f"Directory: {path}\nItems:\n" + "\n".join(f"  {item}" for item in items)

    except PermissionError as e:
        return f"Permission Error: {str(e)}"
    except Exception as e:
        return f"Error listing directory: {str(e)}"


# 导出工具列表
filesystem_tools = [
    read_file,
    write_file,
    edit_file,
    list_directory
]