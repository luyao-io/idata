import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

# 日志包含两个模块，用户问题日志和程序运行日志
# 用户问题日志函数调用：log_user_question("user", "question")
# 程序运行日志函数调用：SysLogger.info("info_msg") SysLogger.error("error_msg")....

class TZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt = None):
        tz = timezone(timedelta(hours=8))
        dt = datetime.fromtimestamp(record.created, tz)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()



def setup_logging():
    """
    初始化所有日志记录器
    :return:
    """
    # 初始化用户问题日志
    init_user_question_logger()
    # 初始化程序运行日志
    init_system_logger()


def log_user_question(user: str, question: str):
    """
    用户问题日志，路径：程序根目录/logger/user_question_logger
    :param user: 用户名
    :param question: 用户问题
    :return:
    """
    user_question_logger = init_user_question_logger()
    user_question_logger.info(question, extra={"user": user})


def init_user_question_logger():
    """
    日志初始化
    :return:
    """
    # 使用 getLogger 获取已存在的 logger，避免重复创建
    logger = logging.getLogger("user_question_logger")

    # 如果 logger 已经有 handlers，说明已经初始化过了，直接返回
    if logger.handlers:
        return logger

    # 设置 logger 级别
    logger.setLevel(logging.INFO)

    # 创建日志目录
    base_dir = Path(__file__).resolve().parent
    log_folder = base_dir / "logger"
    log_folder.mkdir(exist_ok=True)

    # 创建日志文件路径
    log_file = log_folder / "user_question.log"

    # 创建 RotatingFileHandler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=2 * 1024 * 1024,  # 2MB大小限制
        backupCount=100,  # 保留100个
        encoding="utf-8"
    )

    # 设置格式化器
    formatter = TZFormatter(
        "%(asctime)s\t%(user)s\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    # 将 handler 添加到 logger
    logger.addHandler(handler)

    return logger


def log_system_info(message: str):
    """
    记录系统信息日志
    :param message: 信息内容
    """
    sys_logger = init_system_logger()
    sys_logger.info(message)


def log_system_error(message: str):
    """
    记录系统错误日志
    :param message: 错误信息
    """
    sys_logger = init_system_logger()
    sys_logger.error(message)


def log_system_warning(message: str):
    """
    记录系统警告日志
    :param message: 警告信息
    """
    sys_logger = init_system_logger()
    sys_logger.warning(message)


def log_system_debug(message: str):
    """
    记录系统调试日志
    :param message: 调试信息
    """
    sys_logger = init_system_logger()
    sys_logger.debug(message)


def log_system_exception(message: str, exc_info=True):
    """
    记录系统异常日志（包含异常堆栈）
    :param message: 异常信息
    :param exc_info: 是否包含异常堆栈信息
    """
    sys_logger = init_system_logger()
    sys_logger.exception(message, exc_info=exc_info)


def init_system_logger():
    """
    系统日志初始化
    :return:
    """
    # 使用 getLogger 获取已存在的 logger，避免重复创建
    logger = logging.getLogger("system_logger")
    # 如果 logger 已经有 handlers，说明已经初始化过了，直接返回
    if logger.handlers:
        return logger
    # 设置 logger 级别
    logger.setLevel(logging.DEBUG)
    # 创建日志目录
    base_dir = Path(__file__).resolve().parent
    log_folder = base_dir / "logger"
    log_folder.mkdir(exist_ok=True)
    # 创建日志文件路径
    log_file = log_folder / "system.log"
    # 创建 RotatingFileHandler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB大小限制
        backupCount=50,  # 保留50个
        encoding="utf-8"
    )
    # 设置格式化器
    formatter = TZFormatter(
        "%(asctime)s\t%(levelname)s\t%(module)s\t%(funcName)s:%(lineno)d\t%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    # 将 handler 添加到 logger
    logger.addHandler(handler)
    return logger


# 全局系统日志记录器实例
class SysLogger:
    """系统日志记录器类，提供静态方法"""

    @staticmethod
    def info(message: str):
        """记录信息日志"""
        log_system_info(message)

    @staticmethod
    def error(message: str):
        """记录错误日志"""
        log_system_error(message)

    @staticmethod
    def warning(message: str):
        """记录警告日志"""
        log_system_warning(message)

    @staticmethod
    def debug(message: str):
        """记录调试日志"""
        log_system_debug(message)

    @staticmethod
    def exception(message: str, exc_info=True):
        """记录异常日志"""
        log_system_exception(message, exc_info)
