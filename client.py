#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具客户端模块

负责客户端功能，包括连接服务端、同步文件等
"""

import time
import socket
import json
import sqlite3
import os
from pathlib import Path

from config import (
    DEFAULT_PORT, DEFAULT_BUFFER_SIZE, DEFAULT_TIME_THRESHOLD, DEFAULT_SIZE_THRESHOLD, 
    logger, load_exclude_config, EXCLUDED_EXTENSIONS, EXCLUDED_DIRECTORIES, EXCLUDED_PATHS
)
from database import FileDatabase
from utils import calculate_file_hash, send_data, receive_data, parse_json_response

class SyncClient:
    """同步客户端"""

    def __init__(self, server_ip, port=DEFAULT_PORT, exclude_config='exclude.conf'):
        """初始化客户端

        Args:
            server_ip: 服务端IP地址
            port: 服务端端口
            exclude_config: 排除配置文件路径
        """
        self.server_ip = server_ip
        self.port = port

        # 获取当前脚本所在目录
        self.script_dir = Path(__file__).resolve().parent

        # 加载排除规则
        self.excluded_extensions, self.excluded_directories, self.excluded_paths = load_exclude_config(exclude_config)
        logger.info(f"已加载排除规则: {len(self.excluded_extensions)} 个扩展名, {len(self.excluded_directories)} 个目录, {len(self.excluded_paths)} 个路径")

        # 初始化数据库
        self.db = FileDatabase(self.script_dir / "file_sync_client.db")

        # 时间差值
        self.time_diff = 0

        # 扫描上一级目录
        self.scan_parent_directory()

        logger.info(f"客户端初始化完成，服务端地址: {server_ip}:{port}")

    def scan_parent_directory(self):
        """扫描上一级目录"""
        parent_dir = self.script_dir.parent
        logger.info(f"开始扫描上一级目录: {parent_dir}")
        file_count = self.db.scan_directory(parent_dir)
        logger.info(f"扫描完成，共发现 {file_count} 个文件")

    def start(self):
        """启动客户端"""
        client_socket = None
        max_retries = 3  # 最大重试次数
        retry_count = 0
        
        try:
            while retry_count < max_retries:
                try:
                    # 如果已经有socket连接，先关闭
                    if client_socket:
                        try:
                            client_socket.close()
                        except:
                            pass
                    
                    # 创建新的socket连接
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect((self.server_ip, self.port))
                    logger.info(f"已连接到服务端: {self.server_ip}:{self.port}")

                    # 同步时间
                    self.sync_time(client_socket)

                    # 下载服务端数据库
                    server_db_path = self.download_server_db(client_socket)

                    if not server_db_path:
                        retry_count += 1
                        logger.warning(f"下载服务端数据库失败，尝试重试 ({retry_count}/{max_retries})...")
                        time.sleep(2)  # 等待2秒后重试
                        continue

                    # 对比文件清单，找出需要同步的文件
                    files_to_sync = self.compare_files(server_db_path)

                    # 同步文件
                    self.sync_files(client_socket, files_to_sync)
                    
                    # 如果成功完成，跳出循环
                    break
                    
                except ConnectionRefusedError:
                    retry_count += 1
                    logger.error(f"无法连接到服务端: {self.server_ip}:{self.port}")
                    if retry_count < max_retries:
                        logger.info(f"将在5秒后重试 ({retry_count}/{max_retries})...")
                        time.sleep(5)
                    else:
                        logger.error("已达到最大重试次数，放弃连接")
                except json.JSONDecodeError as e:
                    retry_count += 1
                    logger.error(f"解析JSON数据失败: {str(e)}")
                    if retry_count < max_retries:
                        logger.info(f"将在3秒后重试 ({retry_count}/{max_retries})...")
                        time.sleep(3)
                    else:
                        logger.error("已达到最大重试次数，放弃操作")
                except socket.timeout:
                    retry_count += 1
                    logger.error("连接超时")
                    if retry_count < max_retries:
                        logger.info(f"将在3秒后重试 ({retry_count}/{max_retries})...")
                        time.sleep(3)
                    else:
                        logger.error("已达到最大重试次数，放弃操作")
                except Exception as e:
                    retry_count += 1
                    logger.error(f"同步过程中发生错误: {str(e)}")
                    if retry_count < max_retries:
                        logger.info(f"将在3秒后重试 ({retry_count}/{max_retries})...")
                        time.sleep(3)
                    else:
                        logger.error("已达到最大重试次数，放弃操作")
                        raise

        except Exception as e:
            logger.error(f"同步过程中发生严重错误: {str(e)}")
        finally:
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
            self.db.close()
            logger.info("客户端已关闭")

    def sync_time(self, client_socket):
        """同步时间

        Args:
            client_socket: 客户端socket

        Returns:
            时间差值（服务端时间 - 客户端时间）
        """
        # 发送时间同步请求
        request = {
            "type": "time_sync",
            "client_time": time.time()
        }
        send_data(client_socket, json.dumps(request))

        # 接收服务端响应
        response_data = receive_data(client_socket)
        if not response_data:
            logger.error("时间同步失败: 未收到响应数据")
            return 0
            
        try:
            response = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"时间同步失败: JSON解析错误 - {str(e)}")
            return 0

        if response.get("status") != "ok":
            logger.error(f"时间同步失败: {response}")
            return 0

        self.time_diff = response.get("time_diff", 0)
        logger.info(f"时间同步完成，时间差: {self.time_diff:.2f}秒")
        return self.time_diff

    def download_server_db(self, client_socket):
        """下载服务端数据库

        Args:
            client_socket: 客户端socket

        Returns:
            服务端数据库文件路径
        """
        try:
            # 发送数据库下载请求
            logger.info("发送数据库下载请求...")
            request = {
                "type": "db_download"
            }
            send_data(client_socket, json.dumps(request))

            # 接收服务端响应
            logger.info("等待服务端响应...")
            response_data = receive_data(client_socket)
            if not response_data:
                logger.error("数据库下载请求失败: 未收到响应数据")
                return None
                
            try:
                response = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"数据库下载请求失败: JSON解析错误 - {str(e)}")
                return None

            if response.get("status") != "ok":
                logger.error(f"数据库下载请求失败: {response}")
                return None

            # 获取数据库文件大小
            file_size = response.get("size", 0)
            logger.info(f"服务端数据库大小: {file_size} 字节")

            # 发送准备就绪信息
            logger.info("发送准备就绪信息...")
            send_data(client_socket, json.dumps({"status": "ready"}))

            # 接收数据库文件
            logger.info("开始接收数据库文件...")
            server_db_path = self.script_dir / "server_file_sync.db"
            
            # 设置socket超时
            original_timeout = client_socket.gettimeout()
            client_socket.settimeout(30)  # 设置30秒超时
            
            try:
                with open(server_db_path, 'wb') as f:
                    received_size = 0
                    last_log_time = time.time()
                    
                    while received_size < file_size:
                        try:
                            chunk = client_socket.recv(min(DEFAULT_BUFFER_SIZE, file_size - received_size))
                            if not chunk:
                                logger.warning("接收数据库文件时连接关闭")
                                break
                                
                            f.write(chunk)
                            received_size += len(chunk)
                            
                            # 每秒记录一次进度
                            current_time = time.time()
                            if current_time - last_log_time >= 1:
                                logger.info(f"已接收 {received_size}/{file_size} 字节 ({received_size/file_size*100:.1f}%)")
                                last_log_time = current_time
                                
                        except socket.timeout:
                            logger.warning("接收数据库文件时超时")
                            break
                        except Exception as e:
                            logger.error(f"接收数据库文件时发生错误: {str(e)}")
                            break
            finally:
                # 恢复原始超时设置
                client_socket.settimeout(original_timeout)

            if received_size < file_size:
                logger.warning(f"数据库文件下载不完整: 已接收 {received_size}/{file_size} 字节")
                # 如果文件下载不完整，尝试重新连接
                if received_size > 0:
                    logger.info("保留已下载的部分数据库文件")
                return None

            logger.info(f"数据库文件下载完成，大小: {received_size} 字节")
            return server_db_path
            
        except Exception as e:
            logger.error(f"下载服务端数据库时发生错误: {str(e)}")
            return None
            
    def should_exclude_file(self, path):
        """检查文件是否应该被排除
        
        Args:
            path: 文件相对路径
            
        Returns:
            如果文件应该被排除，返回True，否则返回False
        """
        # 检查特定路径
        str_path = str(path)
        for excluded_path in self.excluded_paths:
            if str_path == excluded_path or str_path.startswith(excluded_path + '/'):
                logger.debug(f"排除文件(路径匹配): {path}")
                return True
        
        # 检查文件扩展名
        suffix = Path(path).suffix.lower()
        if suffix in self.excluded_extensions:
            logger.debug(f"排除文件(扩展名匹配): {path}")
            return True
        
        # 检查目录名
        parts = Path(path).parts
        for part in parts:
            if part in self.excluded_directories:
                logger.debug(f"排除文件(目录匹配): {path}")
                return True
        
        return False

    def compare_files(self, server_db_path):
        """对比文件清单，找出需要同步的文件

        Args:
            server_db_path: 服务端数据库文件路径

        Returns:
            需要同步的文件列表
        """
        # 连接服务端数据库
        server_db = sqlite3.connect(server_db_path)
        server_cursor = server_db.cursor()

        # 获取服务端文件列表
        server_cursor.execute('''
        SELECT path, size, modified_time, hash, last_sync_time
        FROM files
        ORDER BY path
        ''')

        server_files = {}
        for row in server_cursor.fetchall():
            server_files[row[0]] = {
                'path': row[0],
                'size': row[1],
                'modified_time': row[2],
                'hash': row[3],
                'last_sync_time': row[4]
            }

        # 获取客户端文件列表
        client_files = {}
        for file_info in self.db.get_all_files():
            client_files[file_info['path']] = file_info

        # 找出需要同步的文件
        files_to_sync = []
        parent_dir = self.script_dir.parent
        excluded_count = 0

        # 遍历客户端文件
        for path, client_file in client_files.items():
            # 检查文件是否应该被排除
            if self.should_exclude_file(path):
                excluded_count += 1
                continue
                
            server_file = server_files.get(path)

            # 如果服务端没有该文件，或者文件大小不同，或者修改时间差异超过阈值
            if (not server_file or
                abs(client_file['size'] - server_file['size']) > DEFAULT_SIZE_THRESHOLD or
                abs(client_file['modified_time'] - server_file['modified_time']) > DEFAULT_TIME_THRESHOLD):

                # 计算文件哈希
                full_path = parent_dir / path
                if full_path.exists():
                    file_hash = calculate_file_hash(full_path)
                    file_size = full_path.stat().st_size
                    file_mtime = full_path.stat().st_mtime

                    # 如果服务端有该文件，且哈希值相同，则不需要同步
                    if server_file and server_file['hash'] == file_hash:
                        continue

                    files_to_sync.append({
                        'path': path,
                        'size': file_size,
                        'modified_time': file_mtime,
                        'hash': file_hash
                    })

        server_db.close()
        logger.info(f"文件对比完成，需要同步 {len(files_to_sync)} 个文件，排除 {excluded_count} 个文件")
        return files_to_sync

    def sync_files(self, client_socket, files_to_sync):
        """同步文件

        Args:
            client_socket: 客户端socket
            files_to_sync: 需要同步的文件列表
        """
        if not files_to_sync:
            logger.info("没有文件需要同步")
            return

        # 发送文件同步请求
        request = {
            "type": "file_sync",
            "files": files_to_sync
        }
        send_data(client_socket, json.dumps(request))

        # 接收服务端准备就绪信息
        response_data = receive_data(client_socket)
        if not response_data:
            logger.error("文件同步失败: 未收到服务端响应")
            return
            
        try:
            response = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.error(f"文件同步失败: JSON解析错误 - {str(e)}")
            return

        if response.get("status") != "ready":
            logger.error(f"服务端未准备就绪: {response}")
            return

        # 发送文件
        sent_files = 0
        file_count = len(files_to_sync)
        parent_dir = self.script_dir.parent

        for file_info in files_to_sync:
            rel_path = file_info['path']
            file_size = file_info['size']
            file_hash = file_info['hash']

            # 接收服务端准备接收文件的信息
            response_data = receive_data(client_socket)
            if not response_data:
                logger.error(f"文件发送失败: {rel_path}, 未收到服务端响应")
                continue
                
            try:
                response = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"文件发送失败: {rel_path}, JSON解析错误 - {str(e)}")
                continue

            if response.get("status") != "ready_for_file":
                logger.error(f"服务端未准备接收文件: {response}")
                continue

            # 发送文件内容
            full_path = parent_dir / rel_path
            with open(full_path, 'rb') as f:
                while True:
                    chunk = f.read(DEFAULT_BUFFER_SIZE)
                    if not chunk:
                        break
                    client_socket.sendall(chunk)

            # 接收文件接收状态
            response_data = receive_data(client_socket)
            if not response_data:
                logger.error(f"文件发送状态未知: {rel_path}, 未收到服务端响应")
                continue
                
            try:
                response = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"文件发送状态未知: {rel_path}, JSON解析错误 - {str(e)}")
                continue

            if response.get("status") == "file_received":
                sent_files += 1
                logger.info(f"已发送文件 ({sent_files}/{file_count}): {rel_path}")
            else:
                logger.warning(f"文件发送失败: {rel_path}, 状态: {response.get('status')}")

        # 接收同步完成信息
        response_data = receive_data(client_socket)
        if not response_data:
            logger.warning("同步完成状态未知: 未收到服务端响应")
            return
            
        try:
            response = json.loads(response_data)
        except json.JSONDecodeError as e:
            logger.warning(f"同步完成状态未知: JSON解析错误 - {str(e)}")
            return

        if response.get("status") == "sync_complete":
            received_files = response.get("received_files", 0)
            logger.info(f"同步完成，服务端成功接收 {received_files}/{file_count} 个文件")
        else:
            logger.warning(f"同步未正常完成: {response}")
