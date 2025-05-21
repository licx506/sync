#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具命令行界面模块

负责命令行界面和交互式菜单
"""

import argparse
from datetime import datetime

from config import DEFAULT_PORT, logger
from server import SyncServer
from client import SyncClient
from restorer import FileRestorer

def show_menu():
    """显示菜单"""
    print("\n文件同步工具")
    print("=" * 30)
    print("1. 启动服务端")
    print("2. 启动客户端")
    print("3. 恢复文件")
    print("0. 退出")
    print("=" * 30)

    choice = input("请选择: ")
    return choice

def start_server_interactive():
    """交互式启动服务端"""
    port = input("请输入服务端端口 (默认 8765): ")
    if not port:
        port = DEFAULT_PORT
    else:
        port = int(port)

    log_dir = input("请输入日志目录 (默认 ./logs): ")
    if not log_dir:
        log_dir = None

    server = SyncServer(port=port, log_dir=log_dir)
    server.start()

def start_client_interactive():
    """交互式启动客户端"""
    server_ip = input("请输入服务端IP地址: ")
    while not server_ip:
        print("服务端IP地址不能为空")
        server_ip = input("请输入服务端IP地址: ")

    port = input("请输入服务端端口 (默认 8765): ")
    if not port:
        port = DEFAULT_PORT
    else:
        port = int(port)

    client = SyncClient(server_ip=server_ip, port=port)
    client.start()

def restore_files_interactive():
    """交互式恢复文件"""
    print("\n文件恢复")
    print("=" * 30)
    print("请选择恢复方式:")
    print("1. 按时间范围恢复")
    print("0. 返回")

    choice = input("请选择: ")

    if choice == "1":
        # 按时间范围恢复
        start_time_str = input("请输入开始时间 (格式: YYYY-MM-DD HH:MM:SS): ")
        end_time_str = input("请输入结束时间 (格式: YYYY-MM-DD HH:MM:SS): ")

        try:
            start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S").timestamp()
            end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S").timestamp()

            restorer = FileRestorer()
            restorer.restore_files_by_time_range(start_time, end_time)
            restorer.close()
        except ValueError:
            print("时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式")
    elif choice == "0":
        return
    else:
        print("无效的选择")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="文件同步工具")
    parser.add_argument("--server", action="store_true", help="启动服务端")
    parser.add_argument("--client", action="store_true", help="启动客户端")
    parser.add_argument("--restore", action="store_true", help="恢复文件")
    parser.add_argument("--server-ip", help="服务端IP地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="服务端端口")
    parser.add_argument("--log-dir", help="日志目录")
    parser.add_argument("--start-time", help="恢复文件的开始时间 (格式: YYYY-MM-DD HH:MM:SS)")
    parser.add_argument("--end-time", help="恢复文件的结束时间 (格式: YYYY-MM-DD HH:MM:SS)")

    return parser.parse_args()

def run_cli():
    """运行命令行界面"""
    args = parse_args()

    # 通过命令行参数启动
    if args.server:
        server = SyncServer(port=args.port, log_dir=args.log_dir)
        server.start()
    elif args.client:
        if not args.server_ip:
            print("客户端模式需要指定服务端IP地址")
            return

        client = SyncClient(server_ip=args.server_ip, port=args.port)
        client.start()
    elif args.restore:
        if not args.start_time or not args.end_time:
            print("恢复文件需要指定开始时间和结束时间")
            return

        try:
            start_time = datetime.strptime(args.start_time, "%Y-%m-%d %H:%M:%S").timestamp()
            end_time = datetime.strptime(args.end_time, "%Y-%m-%d %H:%M:%S").timestamp()

            restorer = FileRestorer()
            restorer.restore_files_by_time_range(start_time, end_time)
            restorer.close()
        except ValueError:
            print("时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式")
    else:
        # 交互式菜单
        while True:
            choice = show_menu()

            if choice == "1":
                start_server_interactive()
                break
            elif choice == "2":
                start_client_interactive()
                break
            elif choice == "3":
                restore_files_interactive()
            elif choice == "0":
                print("再见!")
                break
            else:
                print("无效的选择，请重试")
