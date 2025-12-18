@echo off
chcp 65001 >nul
cd /d "f:\opensource\marine_ranching\observationnetwork"
echo 启动ThingsBoard同步服务...
pythonw thingsboard_sync_service.py --interval 300
