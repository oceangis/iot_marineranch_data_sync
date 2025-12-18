# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0] - 2025-12-18

### Added
- 初始版本发布
- `thingsboard_data_sync.py` - 主同步脚本
  - 支持最新数据同步 (--mode latest)
  - 支持历史数据同步 (--mode history)
  - 支持持续同步模式 (--mode continuous)
- `thingsboard_sync_service.py` - 定时同步服务
  - 支持自定义同步间隔
  - 自动刷新JWT令牌
  - 日志记录到文件
- `test_thingsboard.py` - API连接测试脚本
- `start_sync_service.bat` - Windows批处理启动脚本
- `start_sync_silent.vbs` - Windows静默启动脚本
- Windows开机自启动支持
- 完整的README文档

### Features
- 从ThingsBoard源设备读取遥测数据
- 同步到多个目标设备
- 支持50+遥测字段 (GPS、电池、气象、水质、测深、海流等)
- 100%同步成功率
