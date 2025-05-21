#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件同步工具工具模块

包含通用工具函数
"""

import hashlib
import json
import socket
from config import DEFAULT_BUFFER_SIZE, DEFAULT_ENCODING, logger

def calculate_file_hash(file_path):
    """计算文件哈希值

    Args:
        file_path: 文件路径

    Returns:
        文件的MD5哈希值
    """
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def send_data(sock, data):
    """发送数据

    Args:
        sock: socket对象
        data: 要发送的数据
    """
    data_bytes = data.encode(DEFAULT_ENCODING)
    length = len(data_bytes)

    # 发送数据长度
    sock.sendall(length.to_bytes(4, byteorder='big'))

    # 发送数据
    sock.sendall(data_bytes)

def receive_data(sock):
    """接收数据

    Args:
        sock: socket对象

    Returns:
        接收到的数据，如果连接关闭则返回空JSON字符串
    """
    # 接收数据长度
    length_data = sock.recv(4)
    if not length_data:
        logger.warning("接收数据时连接已关闭")
        return "{}"  # 返回空JSON对象字符串，而不是None

    length = int.from_bytes(length_data, byteorder='big')

    # 接收数据
    data = b''
    while len(data) < length:
        chunk = sock.recv(min(DEFAULT_BUFFER_SIZE, length - len(data)))
        if not chunk:
            logger.warning("接收数据时连接中断")
            break
        data += chunk

    if not data:
        return "{}"  # 如果没有接收到数据，返回空JSON对象字符串

    return data.decode(DEFAULT_ENCODING)

def parse_json_response(response_data):
    """解析JSON响应数据

    Args:
        response_data: 响应数据字符串

    Returns:
        解析后的JSON对象，如果解析失败则返回空字典
    """
    if not response_data:
        logger.error("未收到响应数据")
        return {}

    try:
        return json.loads(response_data)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析错误: {str(e)}")
        return {}
