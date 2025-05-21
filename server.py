#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具服务端模块

负责服务端功能，包括接收客户端连接、处理同步请求等
"""

import os
import time
import socket
import json
import threading
import queue
import shutil
from pathlib import Path

from config import DEFAULT_PORT, DEFAULT_BUFFER_SIZE, logger, setup_file_logger
from database import FileDatabase
from utils import calculate_file_hash, send_data, receive_data

class SyncServer:
    """同步服务端"""

    def __init__(self, port=DEFAULT_PORT, log_dir=None):
        """初始化服务端

        Args:
            port: 服务端监听端口
            log_dir: 日志目录，默认为当前目录下的logs文件夹
        """
        self.port = port

        # 设置日志目录
        if log_dir is None:
            self.log_dir = Path("logs")
        else:
            self.log_dir = Path(log_dir)

        # 创建日志目录
        self.log_dir.mkdir(exist_ok=True)

        # 设置文件日志
        setup_file_logger(self.log_dir)

        # 创建socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # 客户端连接队列
        self.clients = queue.Queue()

        # 获取当前脚本所在目录
        self.script_dir = Path(__file__).resolve().parent

        # 设置备份目录
        self.backup_dir = self.script_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # 初始化数据库
        self.db = FileDatabase(self.script_dir / "file_sync.db")

        # 扫描上一级目录
        self.scan_parent_directory()

        logger.info(f"服务端初始化完成，监听端口: {self.port}")

    def scan_parent_directory(self):
        """扫描上一级目录"""
        parent_dir = self.script_dir.parent
        logger.info(f"开始扫描上一级目录: {parent_dir}")
        file_count = self.db.scan_directory(parent_dir)
        logger.info(f"扫描完成，共发现 {file_count} 个文件")

    def start(self):
        """启动服务端"""
        try:
            # 绑定地址和端口
            self.server_socket.bind(('0.0.0.0', self.port))
            # 开始监听
            self.server_socket.listen(5)
            logger.info(f"服务端已启动，监听地址: 0.0.0.0:{self.port}")

            # 启动客户端处理线程
            client_handler = threading.Thread(target=self.handle_clients)
            client_handler.daemon = True
            client_handler.start()

            # 接受客户端连接
            while True:
                client_socket, client_address = self.server_socket.accept()
                logger.info(f"接受客户端连接: {client_address[0]}:{client_address[1]}")
                self.clients.put((client_socket, client_address))

        except KeyboardInterrupt:
            logger.info("接收到中断信号，服务端正在关闭...")
        except Exception as e:
            logger.error(f"服务端发生错误: {str(e)}")
        finally:
            self.server_socket.close()
            self.db.close()
            logger.info("服务端已关闭")

    def handle_clients(self):
        """处理客户端连接"""
        while True:
            try:
                client_socket, client_address = self.clients.get(timeout=1)
                threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理客户端连接时发生错误: {str(e)}")

    def handle_client(self, client_socket, client_address):
        """处理单个客户端连接

        Args:
            client_socket: 客户端socket
            client_address: 客户端地址
        """
        client_ip = client_address[0]

        # 为当前线程创建单独的数据库连接
        thread_db = FileDatabase(self.script_dir / "file_sync.db")

        try:
            # 持续处理客户端请求，直到连接关闭或出错
            while True:
                # 接收客户端请求类型
                request_data = receive_data(client_socket)
                if not request_data or request_data == "{}":
                    logger.info(f"客户端 {client_ip} 关闭连接")
                    break

                try:
                    request = json.loads(request_data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析JSON数据失败: {str(e)}")
                    send_data(client_socket, json.dumps({"status": "error", "message": "Invalid JSON data"}))
                    continue

                request_type = request.get('type')
                logger.info(f"收到客户端 {client_ip} 请求: {request_type}")

                if request_type == 'time_sync':
                    # 处理时间同步请求
                    self.handle_time_sync(client_socket, request)
                elif request_type == 'db_download':
                    # 处理数据库下载请求
                    self.handle_db_download(client_socket)
                elif request_type == 'file_sync':
                    # 处理文件同步请求
                    self.handle_file_sync(client_socket, client_ip, request, thread_db)
                elif request_type == 'close':
                    # 客户端请求关闭连接
                    logger.info(f"客户端 {client_ip} 请求关闭连接")
                    break
                else:
                    logger.warning(f"未知的请求类型: {request_type}")
                    send_data(client_socket, json.dumps({"status": "error", "message": "Unknown request type"}))

        except Exception as e:
            logger.error(f"处理客户端 {client_ip} 时发生错误: {str(e)}")
            try:
                send_data(client_socket, json.dumps({"status": "error", "message": str(e)}))
            except:
                pass
        finally:
            # 关闭线程数据库连接
            thread_db.close()
            client_socket.close()
            logger.info(f"客户端 {client_ip} 连接已关闭")

    def handle_time_sync(self, client_socket, request):
        """处理时间同步请求

        Args:
            client_socket: 客户端socket
            request: 请求数据
        """
        client_time = request.get('client_time')
        server_time = time.time()

        response = {
            "status": "ok",
            "server_time": server_time,
            "client_time": client_time,
            "time_diff": server_time - client_time
        }

        send_data(client_socket, json.dumps(response))
        logger.info(f"时间同步完成，时间差: {server_time - client_time:.2f}秒")

    def handle_db_download(self, client_socket):
        """处理数据库下载请求

        Args:
            client_socket: 客户端socket
        """
        try:
            db_path = self.script_dir / "file_sync.db"
            logger.info(f"收到数据库下载请求，数据库路径: {db_path}")

            if not db_path.exists():
                logger.error(f"数据库文件不存在: {db_path}")
                send_data(client_socket, json.dumps({"status": "error", "message": "Database file not found"}))
                return

            # 发送数据库文件大小
            file_size = db_path.stat().st_size
            logger.info(f"准备发送数据库文件，大小: {file_size} 字节")
            send_data(client_socket, json.dumps({"status": "ok", "size": file_size}))

            # 接收客户端准备就绪信息
            logger.info("等待客户端准备就绪...")
            response_data = receive_data(client_socket)

            if not response_data:
                logger.error("未收到客户端准备就绪信息")
                return

            try:
                response = json.loads(response_data)
            except json.JSONDecodeError as e:
                logger.error(f"解析客户端准备就绪信息失败: {str(e)}")
                return

            if response.get("status") != "ready":
                logger.error(f"客户端未准备就绪: {response}")
                return

            logger.info("开始发送数据库文件...")
            # 发送数据库文件
            try:
                with open(db_path, 'rb') as f:
                    sent_size = 0
                    while True:
                        chunk = f.read(DEFAULT_BUFFER_SIZE)
                        if not chunk:
                            break
                        client_socket.sendall(chunk)
                        sent_size += len(chunk)
                        if sent_size % (DEFAULT_BUFFER_SIZE * 10) == 0:  # 每发送约40KB记录一次日志
                            logger.info(f"已发送 {sent_size}/{file_size} 字节 ({sent_size/file_size*100:.1f}%)")

                logger.info(f"数据库文件发送完成，总共发送: {sent_size} 字节")
            except Exception as e:
                logger.error(f"发送数据库文件时发生错误: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"处理数据库下载请求时发生错误: {str(e)}")
            try:
                send_data(client_socket, json.dumps({"status": "error", "message": str(e)}))
            except:
                logger.error("无法发送错误信息到客户端")
                pass

    def handle_file_sync(self, client_socket, client_ip, request, thread_db=None):
        """处理文件同步请求

        Args:
            client_socket: 客户端socket
            client_ip: 客户端IP
            request: 请求数据
            thread_db: 线程特定的数据库连接，如果为None则使用全局数据库连接
        """
        # 如果没有提供线程特定的数据库连接，则使用全局数据库连接
        db = thread_db if thread_db is not None else self.db
        files_to_sync = request.get('files', [])
        file_count = len(files_to_sync)

        logger.info(f"客户端 {client_ip} 请求同步 {file_count} 个文件")

        # 发送准备就绪信息
        send_data(client_socket, json.dumps({"status": "ready"}))

        # 接收文件
        received_files = 0
        parent_dir = self.script_dir.parent

        for file_info in files_to_sync:
            rel_path = file_info.get('path')
            file_size = file_info.get('size')
            file_hash = file_info.get('hash')
            modified_time = file_info.get('modified_time')

            # 构建完整的目标路径
            full_dest_path = parent_dir / rel_path

            # 确保目标目录存在
            full_dest_path.parent.mkdir(parents=True, exist_ok=True)

            # 如果文件已存在，备份它
            if full_dest_path.exists():
                # 生成备份文件名
                backup_filename = f"{full_dest_path.name}_{int(time.time())}"
                backup_path = self.backup_dir / backup_filename

                # 复制文件到备份目录
                shutil.copy2(full_dest_path, backup_path)

                # 记录备份信息
                original_file_stat = full_dest_path.stat()
                db.backup_file(
                    rel_path,
                    str(backup_path.relative_to(self.script_dir)),
                    original_file_stat.st_size,
                    original_file_stat.st_mtime,
                    calculate_file_hash(full_dest_path)
                )

                logger.info(f"已备份文件: {rel_path} -> {backup_path}")

            # 发送准备接收文件的信息
            send_data(client_socket, json.dumps({"status": "ready_for_file"}))

            # 接收文件内容
            with open(full_dest_path, 'wb') as f:
                received_size = 0
                while received_size < file_size:
                    chunk = client_socket.recv(min(DEFAULT_BUFFER_SIZE, file_size - received_size))
                    if not chunk:
                        break
                    f.write(chunk)
                    received_size += len(chunk)

            # 验证文件哈希
            received_hash = calculate_file_hash(full_dest_path)
            if received_hash != file_hash:
                logger.warning(f"文件哈希不匹配: {rel_path}")
                send_data(client_socket, json.dumps({"status": "hash_mismatch"}))
            else:
                # 更新文件修改时间
                os.utime(full_dest_path, (time.time(), modified_time))

                # 更新数据库
                db.cursor.execute('''
                INSERT OR REPLACE INTO files (path, size, modified_time, hash, last_sync_time)
                VALUES (?, ?, ?, ?, ?)
                ''', (rel_path, file_size, modified_time, file_hash, time.time()))
                db.conn.commit()

                send_data(client_socket, json.dumps({"status": "file_received"}))
                received_files += 1
                logger.info(f"已接收文件 ({received_files}/{file_count}): {rel_path}")

        # 发送同步完成信息
        send_data(client_socket, json.dumps({
            "status": "sync_complete",
            "received_files": received_files
        }))

        logger.info(f"客户端 {client_ip} 同步完成，共接收 {received_files}/{file_count} 个文件")
