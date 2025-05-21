#!/bin/bash

echo "文件同步工具启动脚本"
echo "============================"

if [ "$1" == "server" ]; then
    echo "正在启动服务端..."
    python3 sync_tool.py --server --port $2
    exit 0
fi

if [ "$1" == "client" ]; then
    echo "正在启动客户端..."
    python3 sync_tool.py --client --server-ip $2 --port $3
    exit 0
fi

if [ "$1" == "restore" ]; then
    echo "正在恢复文件..."
    python3 sync_tool.py --restore --start-time "$2" --end-time "$3"
    exit 0
fi

echo "请选择启动模式:"
echo "1. 服务端"
echo "2. 客户端"
echo "3. 恢复文件"
echo "0. 退出"

read -p "请输入选择: " choice

if [ "$choice" == "1" ]; then
    read -p "请输入端口(默认8765): " port
    if [ -z "$port" ]; then
        port=8765
    fi
    echo "正在启动服务端，端口: $port..."
    python3 sync_tool.py --server --port $port
elif [ "$choice" == "2" ]; then
    read -p "请输入服务端IP地址: " server_ip
    read -p "请输入端口(默认8765): " port
    if [ -z "$port" ]; then
        port=8765
    fi
    echo "正在启动客户端..."
    python3 sync_tool.py --client --server-ip $server_ip --port $port
elif [ "$choice" == "3" ]; then
    echo "恢复文件"
    echo "============================"
    echo "请选择恢复方式:"
    echo "1. 按时间范围恢复"
    echo "0. 返回"

    read -p "请选择: " restore_choice

    if [ "$restore_choice" == "1" ]; then
        read -p "请输入开始时间 (格式: YYYY-MM-DD HH:MM:SS): " start_time
        read -p "请输入结束时间 (格式: YYYY-MM-DD HH:MM:SS): " end_time
        echo "正在恢复文件..."
        python3 sync_tool.py --restore --start-time "$start_time" --end-time "$end_time"
    fi
elif [ "$choice" == "0" ]; then
    echo "再见!"
else
    echo "无效的选择!"
fi
