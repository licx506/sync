# 文件同步工具

这是一个高级文件同步工具，具有以下功能：

1. 系统启动时扫描上一级文件夹内所有文件，记录文件大小、修改日期到SQLite数据库
2. 客户端连接服务端时对比时间差值，下载服务端数据库文件并对比文件清单
3. 找出不一致的文件并同步，服务端备份被替换的文件
4. 支持按时间段恢复文件功能

## 项目结构

代码已按功能模块化拆分，便于维护和扩展：

```
sync/
├── __init__.py        # 包初始化文件
├── config.py          # 配置文件，包含常量和日志设置
├── database.py        # 数据库操作相关代码
├── utils.py           # 通用工具函数
├── server.py          # 服务端相关代码
├── client.py          # 客户端相关代码
├── restorer.py        # 文件恢复相关代码
├── cli.py             # 命令行界面和交互式菜单
└── sync_tool.py       # 主入口文件
```

## 系统要求

- Python 3.6+
- 支持Windows、Linux和macOS

## 安装

无需安装，直接运行Python脚本即可。

## 使用方法

### 通过启动脚本

#### Windows

```
# 交互式菜单
start_sync.bat

# 直接启动服务端（端口可选，默认8765）
start_sync.bat server [端口]

# 直接启动客户端
start_sync.bat client 服务端IP 端口

# 恢复文件
start_sync.bat restore "开始时间" "结束时间"
# 例如：start_sync.bat restore "2023-01-01 00:00:00" "2023-01-02 00:00:00"
```

#### Linux/Mac

```
# 确保脚本有执行权限
chmod +x start_sync.sh

# 交互式菜单
./start_sync.sh

# 直接启动服务端（端口可选，默认8765）
./start_sync.sh server [端口]

# 直接启动客户端
./start_sync.sh client 服务端IP 端口

# 恢复文件
./start_sync.sh restore "开始时间" "结束时间"
# 例如：./start_sync.sh restore "2023-01-01 00:00:00" "2023-01-02 00:00:00"
```

### 直接使用Python脚本

```
# 交互式菜单
python sync/sync_tool.py

# 启动服务端
python sync/sync_tool.py --server [--port PORT] [--log-dir LOG_DIR]

# 启动客户端
python sync/sync_tool.py --client --server-ip IP [--port PORT]

# 恢复文件
python sync/sync_tool.py --restore --start-time "YYYY-MM-DD HH:MM:SS" --end-time "YYYY-MM-DD HH:MM:SS"
```

### 作为Python模块导入

代码已模块化，可以在其他Python脚本中导入使用：

```python
# 导入服务端
from sync.server import SyncServer
server = SyncServer(port=8765)
server.start()

# 导入客户端
from sync.client import SyncClient
client = SyncClient(server_ip="192.168.1.100", port=8765)
client.start()

# 导入文件恢复工具
from sync.restorer import FileRestorer
restorer = FileRestorer()
restorer.restore_files_by_time_range(start_time, end_time)
restorer.close()
```

## 工作原理

### 服务端

1. 启动时扫描上一级目录中的所有文件，记录文件信息到SQLite数据库
2. 监听指定端口，等待客户端连接
3. 处理客户端的时间同步、数据库下载和文件同步请求
4. 在接收客户端文件前，备份本地文件到备份目录
5. 记录备份信息到数据库，以便后续恢复

### 客户端

1. 启动时扫描上一级目录中的所有文件，记录文件信息到本地SQLite数据库
2. 连接服务端，同步时间
3. 下载服务端数据库文件
4. 对比本地和服务端数据库中的文件信息，找出需要同步的文件
5. 将需要同步的文件发送到服务端

### 文件恢复

1. 指定时间范围，查找该时间范围内的备份文件
2. 对于每个原始文件路径，选择最新的备份文件
3. 将备份文件恢复到原始位置
4. 更新数据库记录

## 文件对比规则

文件在以下情况下会被认为需要同步：

1. 服务端没有该文件
2. 文件大小差异超过阈值（默认10字节）
3. 文件修改时间差异超过阈值（默认60秒）
4. 文件哈希值不同（只有在满足上述条件之一时才会计算哈希值）

## 注意事项

1. 确保服务端和客户端之间的网络连接正常
2. 确保服务端有足够的磁盘空间
3. 同步过程中，服务端会备份被替换的文件
4. 恢复文件时，请确保指定正确的时间范围
5. 时间格式必须为 YYYY-MM-DD HH:MM:SS

## 代码重构说明

本项目已经进行了模块化重构，主要变更如下：

1. **模块化拆分**：将原来的单一文件拆分为多个功能模块，每个模块负责特定的功能
2. **改进错误处理**：增强了网络通信中的错误处理和重试机制
3. **增加日志记录**：添加了更详细的日志记录，便于问题诊断
4. **优化代码结构**：遵循单一职责原则，使代码更易于维护和扩展
5. **保留原有功能**：保持与原版本完全相同的功能，确保兼容性

原始的sync_tool.py文件已备份为sync_tool.py.bak，可以随时查看原始代码。
