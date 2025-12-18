# IoT Marine Ranch Data Sync

ThingsBoard 数据同步工具，用于将源设备的遥测数据复制到多个目标设备。

## 功能特性

- 从源设备读取遥测数据并同步到多个目标设备
- 支持最新数据同步、历史数据同步、持续同步三种模式
- 定时同步服务，支持后台运行
- 自动刷新JWT令牌
- 完整的日志记录
- 支持Windows开机自启动

## 文件说明

| 文件 | 说明 |
|------|------|
| `thingsboard_data_sync.py` | 主同步脚本，支持命令行参数 |
| `thingsboard_sync_service.py` | 定时同步服务 |
| `test_thingsboard.py` | API连接测试脚本 |
| `start_sync_service.bat` | Windows批处理启动脚本 |
| `start_sync_silent.vbs` | Windows静默启动脚本 |

## 安装依赖

```bash
pip install requests schedule
```

## 配置

编辑 `thingsboard_sync_service.py` 或 `thingsboard_data_sync.py`：

```python
# ThingsBoard 配置
THINGSBOARD_HOST = "http://your-server:8080"
ADMIN_USERNAME = "your-username"
ADMIN_PASSWORD = "your-password"

# 源设备
SOURCE_DEVICE_ID = "your-source-device-id"

# 目标设备令牌
TARGET_DEVICES = {
    "device-name-1": "device-token-1",
    "device-name-2": "device-token-2",
    "device-name-3": "device-token-3",
}
```

## 使用方法

### 单次同步

```bash
# 同步最新数据
python thingsboard_data_sync.py --mode latest

# 同步历史数据 (最近48小时)
python thingsboard_data_sync.py --mode history --hours 48
```

### 定时同步服务

```bash
# 每5分钟同步一次 (默认60秒)
python thingsboard_sync_service.py --interval 300

# 后台静默运行
pythonw thingsboard_sync_service.py --interval 300
```

### Windows开机自启动

将 `start_sync_silent.vbs` 复制到启动文件夹：
```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
```

## 日志

同步日志保存在 `sync_service.log` 文件中。

## 同步数据字段

支持同步的遥测数据包括：
- GPS: 经度、纬度
- 电池: 电压、电流
- 气象: 气温、湿度、气压、风速、风向
- 水质: 水温、溶解氧、pH、浊度、盐度
- 测深: 水深、水温
- 海流: 表层流速/流向、多层流速/流向

## License

MIT License
