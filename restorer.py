#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具恢复模块

负责文件恢复功能，包括按时间范围恢复文件等
"""

import os
import time
import shutil
from pathlib import Path

from config import logger
from database import FileDatabase

class FileRestorer:
    """文件恢复工具"""

    def __init__(self):
        """初始化恢复工具"""
        # 获取当前脚本所在目录
        self.script_dir = Path(__file__).resolve().parent

        # 初始化数据库
        self.db = FileDatabase(self.script_dir / "file_sync.db")

        # 设置备份目录
        self.backup_dir = self.script_dir / "backups"

        logger.info("文件恢复工具初始化完成")

    def restore_files_by_time_range(self, start_time, end_time):
        """根据时间范围恢复文件

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            恢复的文件数量
        """
        # 获取备份文件列表
        backup_files = self.db.get_backup_files_by_time_range(start_time, end_time)

        if not backup_files:
            logger.info(f"在指定时间范围内没有找到备份文件: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))} - {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
            return 0

        logger.info(f"找到 {len(backup_files)} 个备份文件")

        # 按原始路径分组，只保留每个路径最新的备份
        latest_backups = {}
        for backup in backup_files:
            original_path = backup['original_path']
            if original_path not in latest_backups or backup['backup_time'] > latest_backups[original_path]['backup_time']:
                latest_backups[original_path] = backup

        # 恢复文件
        restored_count = 0
        parent_dir = self.script_dir.parent

        for original_path, backup in latest_backups.items():
            # 构建完整的目标路径
            full_dest_path = parent_dir / original_path

            # 构建完整的备份文件路径
            backup_path = self.script_dir / backup['backup_path']

            if not backup_path.exists():
                logger.warning(f"备份文件不存在: {backup_path}")
                continue

            # 确保目标目录存在
            full_dest_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                # 复制备份文件到原始位置
                shutil.copy2(backup_path, full_dest_path)

                # 恢复文件修改时间
                os.utime(full_dest_path, (time.time(), backup['modified_time']))

                # 更新数据库
                self.db.cursor.execute('''
                INSERT OR REPLACE INTO files (path, size, modified_time, hash, last_sync_time)
                VALUES (?, ?, ?, ?, ?)
                ''', (original_path, backup['size'], backup['modified_time'], backup['hash'], time.time()))

                restored_count += 1
                logger.info(f"已恢复文件 ({restored_count}/{len(latest_backups)}): {original_path}")
            except Exception as e:
                logger.error(f"恢复文件失败: {original_path}, 错误: {str(e)}")

        self.db.conn.commit()
        logger.info(f"文件恢复完成，共恢复 {restored_count} 个文件")
        return restored_count

    def close(self):
        """关闭恢复工具"""
        self.db.close()
        logger.info("文件恢复工具已关闭")
