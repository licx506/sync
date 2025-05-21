@echo off
title 文件同步工具

echo 文件同步工具启动脚本
echo ============================

if "%1"=="server" (
    echo 正在启动服务端...
    python sync_tool.py --server --port %2
    goto :eof
)

if "%1"=="client" (
    echo 正在启动客户端...
    python sync_tool.py --client --server-ip %2 --port %3
    goto :eof
)

if "%1"=="restore" (
    echo 正在恢复文件...
    python sync_tool.py --restore --start-time %2 --end-time %3
    goto :eof
)

echo 请选择启动模式:
echo 1. 服务端
echo 2. 客户端
echo 3. 恢复文件
echo 0. 退出

set /p choice=请输入选择:

if "%choice%"=="1" (
    set /p port=请输入端口(默认8765):
    if "%port%"=="" set port=8765
    echo 正在启动服务端，端口: %port%...
    python sync_tool.py --server --port %port%
) else if "%choice%"=="2" (
    set /p server_ip=请输入服务端IP地址:
    set /p port=请输入端口(默认8765):
    if "%port%"=="" set port=8765
    echo 正在启动客户端...
    python sync_tool.py --client --server-ip %server_ip% --port %port%
) else if "%choice%"=="3" (
    echo 恢复文件
    echo ============================
    echo 请选择恢复方式:
    echo 1. 按时间范围恢复
    echo 0. 返回

    set /p restore_choice=请选择:

    if "%restore_choice%"=="1" (
        set /p start_time=请输入开始时间 (格式: YYYY-MM-DD HH:MM:SS):
        set /p end_time=请输入结束时间 (格式: YYYY-MM-DD HH:MM:SS):
        echo 正在恢复文件...
        python sync_tool.py --restore --start-time "%start_time%" --end-time "%end_time%"
    )
) else if "%choice%"=="0" (
    echo 再见!
) else (
    echo 无效的选择!
)

pause
