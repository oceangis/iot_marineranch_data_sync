# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2025-12-19

### Added
- 涛声依旧数据合并功能
  - 从原始设备 (861556078780730) 获取基础数据
  - 从参考设备1获取 dst800_water_temp
  - 从参考设备2获取 salinity，生成 salinity1 字段
  - 同步到目标设备 (861556078780730-3)
- 敬武数据合并功能
  - 从原始设备 (861556078781175) 获取基础数据
  - 从参考设备获取 air_temp, wind_speed, wind_dir
  - 生成 air_temp1, wind_speed1, wind_dir1 字段
  - 同步到目标设备 (861556078781175-2)
- sensor_wave 数据完全复制功能
  - 从 sensor_wave_gnssm10s 复制到 sensor_wave_gnssm10s_2
- 历史数据同步脚本 `sync_history.py`
  - 支持鑫智、涛声依旧、敬武、sensor_wave 历史数据同步
  - 涛声依旧支持备用数据源填充 salinity1

### Changed
- `thingsboard_sync_service.py` 新增3个同步方法
  - sync_taosheng() - 涛声依旧数据合并
  - sync_jingwu() - 敬武数据合并
  - sync_sensor_wave() - sensor_wave数据复制
- sync_once() 现在执行5个同步任务

## [1.1.0] - 2025-12-19

### Added
- 鑫智数据合并功能
  - 从原始设备 (863482063082305) 获取基础数据
  - 从参考设备获取正确的 dst800_water_temp 和 turbidity
  - 合并后生成新字段 dst800_water_temp 和 turbidity1
  - 同步到目标设备 (863482063082305-3)
- 优化设备ID配置，避免每次启动查找设备

### Changed
- `thingsboard_sync_service.py` 重构
  - sync_once() 现在同时执行数据复制和鑫智数据合并
  - 移除运行时设备查找，使用预配置设备ID
  - 简化代码结构

### Fixed
- 修复设备查找耗时过长的问题

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
