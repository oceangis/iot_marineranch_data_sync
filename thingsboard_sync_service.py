#!/usr/bin/env python3
"""
ThingsBoard 定时同步服务
支持后台运行和定时任务
"""

import requests
import time
import logging
import schedule
from datetime import datetime
from typing import Dict, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync_service.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ThingsBoard 配置
THINGSBOARD_HOST = "http://8.155.1.77:8080"
ADMIN_USERNAME = "tenant@thingsboard.org"
ADMIN_PASSWORD = "Obsis@123456"

# 源设备 (861556078781175)
SOURCE_DEVICE_ID = "23bfe860-b478-11f0-9be1-bfd0710a93d3"

# 目标设备令牌 (数据复制)
TARGET_DEVICES = {
    "863482063082305-2": "ywyOTF0Pm2VnAaGKx0f7",
    "860549070048066-2": "CTssSyLPJFXw7qW8haoQ",
    "861556078780730-2": "go7DaTbvms4EZsaGjIu1",
}

# ========== 鑫智数据合并配置 ==========
# 原始设备 (鑫智原始数据) - 863482063082305
XINZHI_SOURCE_DEVICE_ID = "3d465bf0-d324-11f0-9be1-bfd0710a93d3"

# 参考设备 (提供正确的dst800_water_temp和turbidity) - 使用源设备861556078781175的数据
XINZHI_REF_DEVICE_ID = SOURCE_DEVICE_ID  # 23bfe860-b478-11f0-9be1-bfd0710a93d3

# 目标设备 (合并后的鑫智数据)
XINZHI_TARGET = {
    "863482063082305-3": "bNKptyoymZnrAJF7nsS0",
}


class SyncService:
    def __init__(self):
        self.jwt_token = None
        self.token_time = None

    def login(self) -> bool:
        """登录获取JWT令牌"""
        url = f"{THINGSBOARD_HOST}/api/auth/login"
        try:
            resp = requests.post(url, json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }, timeout=10)
            if resp.status_code == 200:
                self.jwt_token = resp.json().get("token")
                self.token_time = datetime.now()
                return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
        return False

    def ensure_token(self):
        """确保令牌有效 (每小时刷新)"""
        if self.jwt_token is None or self.token_time is None:
            return self.login()
        if (datetime.now() - self.token_time).seconds > 3600:
            return self.login()
        return True

    def get_latest_telemetry(self) -> Dict:
        """获取源设备最新遥测数据"""
        if not self.ensure_token():
            return {}

        headers = {"X-Authorization": f"Bearer {self.jwt_token}"}

        # 获取遥测键
        keys_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{SOURCE_DEVICE_ID}/keys/timeseries"
        try:
            resp = requests.get(keys_url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return {}
            keys = resp.json()

            # 获取最新值
            keys_param = ",".join(keys)
            data_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{SOURCE_DEVICE_ID}/values/timeseries?keys={keys_param}"
            resp = requests.get(data_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"获取数据失败: {e}")
        return {}

    def send_telemetry(self, token: str, data: Dict, ts: int) -> bool:
        """发送遥测数据"""
        url = f"{THINGSBOARD_HOST}/api/v1/{token}/telemetry"
        try:
            resp = requests.post(url, json={"ts": ts, "values": data}, timeout=10)
            return resp.status_code == 200
        except:
            return False

    def get_device_telemetry(self, device_id: str, keys: List[str] = None) -> Dict:
        """获取指定设备的遥测数据"""
        if not self.ensure_token():
            return {}

        headers = {"X-Authorization": f"Bearer {self.jwt_token}"}

        try:
            if keys is None:
                # 先获取所有键
                keys_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{device_id}/keys/timeseries"
                resp = requests.get(keys_url, headers=headers, timeout=10)
                if resp.status_code != 200:
                    return {}
                keys = resp.json()

            if not keys:
                return {}

            keys_param = ",".join(keys)
            data_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys={keys_param}"
            resp = requests.get(data_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"获取设备数据失败: {e}")

        return {}

    def sync_xinzhi(self):
        """同步鑫智数据 (合并原始数据和参考设备的水温/浊度)"""
        logger.info("同步鑫智数据...")

        # 获取原始设备数据 (863482063082305)
        source_telemetry = self.get_device_telemetry(XINZHI_SOURCE_DEVICE_ID)
        if not source_telemetry:
            logger.warning("  无法获取鑫智源数据")
            return

        # 获取参考设备数据 (dst800_water_temp 和 turbidity)
        ref_telemetry = self.get_device_telemetry(XINZHI_REF_DEVICE_ID, ["dst800_water_temp", "turbidity"])

        # 转换源数据格式
        data = {}
        ts = None
        for key, values in source_telemetry.items():
            if values:
                data[key] = values[0].get("value")
                if ts is None:
                    ts = values[0].get("ts")

        # 添加参考设备的水温和浊度
        if ref_telemetry:
            if "dst800_water_temp" in ref_telemetry and ref_telemetry["dst800_water_temp"]:
                data["dst800_water_temp"] = ref_telemetry["dst800_water_temp"][0].get("value")
                logger.info(f"  添加 dst800_water_temp: {data['dst800_water_temp']}")

            if "turbidity" in ref_telemetry and ref_telemetry["turbidity"]:
                data["turbidity1"] = ref_telemetry["turbidity"][0].get("value")
                logger.info(f"  添加 turbidity1: {data['turbidity1']}")

        # 发送到目标设备
        for name, token in XINZHI_TARGET.items():
            if self.send_telemetry(token, data, ts):
                logger.info(f"  -> {name} 成功")
            else:
                logger.error(f"  -> {name} 失败")

    def sync_once(self):
        """执行一次同步 (包括数据复制和鑫智数据合并)"""
        # 1. 数据复制同步
        logger.info("开始数据复制同步...")

        telemetry = self.get_latest_telemetry()
        if not telemetry:
            logger.warning("无法获取源数据")
        else:
            # 转换格式
            data = {}
            ts = None
            for key, values in telemetry.items():
                if values:
                    data[key] = values[0].get("value")
                    if ts is None:
                        ts = values[0].get("ts")

            # 发送到目标设备
            success = 0
            for name, token in TARGET_DEVICES.items():
                if self.send_telemetry(token, data, ts):
                    success += 1
                    logger.info(f"  -> {name} 成功")
                else:
                    logger.error(f"  -> {name} 失败")

            logger.info(f"数据复制完成: {success}/{len(TARGET_DEVICES)} 成功")

        # 2. 鑫智数据合并同步
        self.sync_xinzhi()


def run_service(interval_seconds: int = 60):
    """运行定时同步服务"""
    service = SyncService()

    logger.info("=" * 50)
    logger.info("ThingsBoard 定时同步服务")
    logger.info(f"同步间隔: {interval_seconds} 秒")
    logger.info(f"目标设备: {list(TARGET_DEVICES.keys())}")
    logger.info("=" * 50)

    # 立即执行一次
    service.sync_once()

    # 设置定时任务
    schedule.every(interval_seconds).seconds.do(service.sync_once)

    logger.info(f"定时任务已启动，每 {interval_seconds} 秒同步一次 (Ctrl+C 停止)")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("服务已停止")


def run_scheduled():
    """按固定时间点同步 (每分钟/每小时)"""
    service = SyncService()

    logger.info("=" * 50)
    logger.info("ThingsBoard 定时同步服务 (固定时间点)")
    logger.info("=" * 50)

    # 每分钟的第0秒同步
    schedule.every().minute.at(":00").do(service.sync_once)

    # 或者每小时同步
    # schedule.every().hour.at(":00").do(service.sync_once)

    # 或者每天固定时间同步
    # schedule.every().day.at("08:00").do(service.sync_once)
    # schedule.every().day.at("12:00").do(service.sync_once)
    # schedule.every().day.at("18:00").do(service.sync_once)

    logger.info("定时任务已启动 (Ctrl+C 停止)")

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("服务已停止")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='ThingsBoard 定时同步服务')
    parser.add_argument('--interval', type=int, default=60, help='同步间隔秒数 (默认60)')
    parser.add_argument('--scheduled', action='store_true', help='使用固定时间点模式')
    args = parser.parse_args()

    if args.scheduled:
        run_scheduled()
    else:
        run_service(args.interval)
