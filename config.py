#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具配置模块

包含常量定义和日志配置
"""

import logging
from pathlib import Path

# 默认配置
DEFAULT_PORT = 8765
DEFAULT_BUFFER_SIZE = 4096
DEFAULT_ENCODING = 'utf-8'
DEFAULT_TIME_THRESHOLD = 60  # 文件修改时间阈值（秒）
DEFAULT_SIZE_THRESHOLD = 10  # 文件大小阈值（字节）

# 配置日志
def setup_logging():
    """设置基本日志配置"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("sync_tool")

# 创建全局日志对象
logger = setup_logging()

def setup_file_logger(log_dir, name="sync_server"):
    """设置文件日志

    Args:
        log_dir: 日志目录
        name: 日志名称前缀
    """
    from datetime import datetime
    
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
