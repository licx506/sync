#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具数据库模块

负责数据库操作，包括文件信息的存储和检索
"""

import time
import sqlite3
from pathlib import Path
import os

from config import logger

class FileDatabase:
    """文件数据库管理类"""

    def __init__(self, db_path=None):
        """初始化数据库

        Args:
            db_path: 数据库文件路径，默认为当前目录下的file_sync.db
        """
        if db_path is None:
            self.db_path = Path("file_sync.db")
        else:
            self.db_path = Path(db_path)

        self.conn = None
        self.cursor = None

        # 初始化数据库
        self.init_db()

    def init_db(self):
        """初始化数据库"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()

            # 创建文件表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                hash TEXT,
                last_sync_time REAL,
                UNIQUE(path)
            )
            ''')

            # 创建备份文件表
            self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS backup_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT NOT NULL,
                backup_path TEXT NOT NULL,
                size INTEGER NOT NULL,
                modified_time REAL NOT NULL,
                backup_time REAL NOT NULL,
                hash TEXT
            )
            ''')

            self.conn.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"数据库初始化失败: {str(e)}")
            if self.conn:
                self.conn.close()
            raise

    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def scan_directory(self, directory):
        """扫描目录并更新数据库

        Args:
            directory: 要扫描的目录

        Returns:
            扫描到的文件数量
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            logger.error(f"目录不存在或不是一个有效的目录: {directory}")
            return 0

        file_count = 0
        current_time = time.time()

        try:
            for root, _, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = Path(root) / filename
                    rel_path = file_path.relative_to(directory)

                    # 获取文件信息
                    file_size = file_path.stat().st_size
                    file_mtime = file_path.stat().st_mtime

                    # 更新数据库
                    self.cursor.execute('''
                    INSERT OR REPLACE INTO files (path, size, modified_time, last_sync_time)
                    VALUES (?, ?, ?, ?)
                    ''', (str(rel_path), file_size, file_mtime, current_time))

                    file_count += 1

            self.conn.commit()
            logger.info(f"扫描完成，共处理 {file_count} 个文件")
            return file_count
        except Exception as e:
            logger.error(f"扫描目录时发生错误: {str(e)}")
            self.conn.rollback()
            return 0

    def get_file_info(self, file_path):
        """获取文件信息

        Args:
            file_path: 文件相对路径

        Returns:
            文件信息字典，如果文件不存在则返回None
        """
        try:
            self.cursor.execute('''
            SELECT path, size, modified_time, hash, last_sync_time
            FROM files
            WHERE path = ?
            ''', (str(file_path),))

            row = self.cursor.fetchone()
            if row:
                return {
                    'path': row[0],
                    'size': row[1],
                    'modified_time': row[2],
                    'hash': row[3],
                    'last_sync_time': row[4]
                }
            return None
        except sqlite3.Error as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return None

    def get_all_files(self):
        """获取所有文件信息

        Returns:
            文件信息列表
        """
        try:
            self.cursor.execute('''
            SELECT path, size, modified_time, hash, last_sync_time
            FROM files
            ORDER BY path
            ''')

            files = []
            for row in self.cursor.fetchall():
                files.append({
                    'path': row[0],
                    'size': row[1],
                    'modified_time': row[2],
                    'hash': row[3],
                    'last_sync_time': row[4]
                })
            return files
        except sqlite3.Error as e:
            logger.error(f"获取所有文件信息失败: {str(e)}")
            return []

    def backup_file(self, original_path, backup_path, size, modified_time, hash_value=None):
        """备份文件记录

        Args:
            original_path: 原始文件路径
            backup_path: 备份文件路径
            size: 文件大小
            modified_time: 文件修改时间
            hash_value: 文件哈希值

        Returns:
            是否成功
        """
        try:
            backup_time = time.time()
            self.cursor.execute('''
            INSERT INTO backup_files (original_path, backup_path, size, modified_time, backup_time, hash)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (str(original_path), str(backup_path), size, modified_time, backup_time, hash_value))

            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"备份文件记录失败: {str(e)}")
            self.conn.rollback()
            return False

    def get_backup_files_by_time_range(self, start_time, end_time):
        """根据时间范围获取备份文件

        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳

        Returns:
            备份文件列表
        """
        try:
            self.cursor.execute('''
            SELECT original_path, backup_path, size, modified_time, backup_time, hash
            FROM backup_files
            WHERE backup_time BETWEEN ? AND ?
            ORDER BY backup_time DESC
            ''', (start_time, end_time))

            backup_files = []
            for row in self.cursor.fetchall():
                backup_files.append({
                    'original_path': row[0],
                    'backup_path': row[1],
                    'size': row[2],
                    'modified_time': row[3],
                    'backup_time': row[4],
                    'hash': row[5]
                })
            return backup_files
        except sqlite3.Error as e:
            logger.error(f"获取备份文件失败: {str(e)}")
            return []
