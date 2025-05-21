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

# 排除上传的文件和目录
EXCLUDED_EXTENSIONS = ['.db', '.db-journal', '.log', '.pyc', '.pyo', '.pyd']  # 排除的文件扩展名
EXCLUDED_DIRECTORIES = ['__pycache__', 'backups', 'logs', '.git']  # 排除的目录名
EXCLUDED_PATHS = []  # 排除的特定路径（相对于根目录）

# 读取排除配置文件
def load_exclude_config(config_file='exclude.conf'):
    """从配置文件加载排除规则
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        排除规则元组 (extensions, directories, paths)
    """
    try:
        extensions = list(EXCLUDED_EXTENSIONS)
        directories = list(EXCLUDED_DIRECTORIES)
        paths = list(EXCLUDED_PATHS)
        
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r', encoding=DEFAULT_ENCODING) as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    if line.startswith('ext:'):
                        # 文件扩展名
                        ext = line[4:].strip()
                        if ext and ext not in extensions:
                            extensions.append(ext)
                    elif line.startswith('dir:'):
                        # 目录名
                        dir_name = line[4:].strip()
                        if dir_name and dir_name not in directories:
                            directories.append(dir_name)
                    elif line.startswith('path:'):
                        # 特定路径
                        path = line[5:].strip()
                        if path and path not in paths:
                            paths.append(path)
            
            logger.info(f"已从配置文件 {config_file} 加载排除规则")
        
        return (extensions, directories, paths)
    except Exception as e:
        logger.error(f"加载排除配置文件失败: {str(e)}")
        return (EXCLUDED_EXTENSIONS, EXCLUDED_DIRECTORIES, EXCLUDED_PATHS)

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
