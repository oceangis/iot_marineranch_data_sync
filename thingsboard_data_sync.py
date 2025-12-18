#!/usr/bin/env python3
"""
ThingsBoard 数据同步脚本
从源设备获取数据，复制到多个目标设备
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ThingsBoard 配置
THINGSBOARD_HOST = "http://8.155.1.77:8080"

# 源设备访问令牌和ID
SOURCE_DEVICE_TOKEN = "c0mtY8cl4SdUrhAuOAPr"
SOURCE_DEVICE_ID = "23bfe860-b478-11f0-9be1-bfd0710a93d3"  # 设备名: 861556078781175

# 目标设备令牌
TARGET_DEVICES = {
    "863482063082305-2": "ywyOTF0Pm2VnAaGKx0f7",
    "860549070048066-2": "CTssSyLPJFXw7qW8haoQ",
    "861556078780730-2": "go7DaTbvms4EZsaGjIu1",
}

# 管理员账户 (用于读取源设备数据)
ADMIN_USERNAME = "tenant@thingsboard.org"
ADMIN_PASSWORD = "Obsis@123456"


class ThingsBoardSync:
    """ThingsBoard 数据同步类"""

    def __init__(self, host: str):
        self.host = host.rstrip('/')
        self.jwt_token = None

    def login(self, username: str, password: str) -> bool:
        """登录获取JWT令牌"""
        url = f"{self.host}/api/auth/login"
        payload = {"username": username, "password": password}
        try:
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                self.jwt_token = response.json().get("token")
                logger.info("登录成功")
                return True
            else:
                logger.error(f"登录失败: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"登录异常: {e}")
            return False

    def _headers(self) -> Dict:
        return {
            "Content-Type": "application/json",
            "X-Authorization": f"Bearer {self.jwt_token}"
        }

    def get_device_by_token(self, token: str) -> Dict:
        """通过令牌获取设备信息"""
        # 先发送一个空请求获取设备信息
        url = f"{self.host}/api/v1/{token}/attributes"
        try:
            response = requests.get(url)
            return response.json() if response.status_code == 200 else {}
        except:
            return {}

    def get_device_id_by_name(self, name: str) -> str:
        """通过设备名称获取设备ID"""
        url = f"{self.host}/api/tenant/devices?deviceName={name}"
        try:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                return response.json().get("id", {}).get("id")
        except:
            pass
        return None

    def get_telemetry_keys(self, device_id: str) -> List[str]:
        """获取设备遥测数据键"""
        url = f"{self.host}/api/plugins/telemetry/DEVICE/{device_id}/keys/timeseries"
        try:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return []

    def get_latest_telemetry(self, device_id: str, keys: List[str] = None) -> Dict:
        """获取最新遥测数据"""
        if keys:
            keys_param = ",".join(keys)
            url = f"{self.host}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys={keys_param}"
        else:
            url = f"{self.host}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
        try:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def get_telemetry_history(self, device_id: str, keys: List[str],
                              start_ts: int, end_ts: int, limit: int = 10000) -> Dict:
        """获取历史遥测数据"""
        keys_param = ",".join(keys)
        url = (f"{self.host}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries"
               f"?keys={keys_param}&startTs={start_ts}&endTs={end_ts}&limit={limit}")
        try:
            response = requests.get(url, headers=self._headers())
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return {}

    def send_telemetry(self, token: str, data: Dict, ts: int = None) -> bool:
        """发送遥测数据到设备"""
        url = f"{self.host}/api/v1/{token}/telemetry"
        payload = {"ts": ts, "values": data} if ts else data
        try:
            response = requests.post(url, json=payload)
            return response.status_code == 200
        except:
            return False

    def send_telemetry_batch(self, token: str, data_list: List[Dict]) -> int:
        """批量发送遥测数据，返回成功数量"""
        url = f"{self.host}/api/v1/{token}/telemetry"
        success_count = 0
        for item in data_list:
            try:
                response = requests.post(url, json=item)
                if response.status_code == 200:
                    success_count += 1
                time.sleep(0.005)  # 避免请求过快
            except:
                pass
        return success_count


def sync_latest(sync: ThingsBoardSync, source_device_id: str):
    """同步最新数据"""
    keys = sync.get_telemetry_keys(source_device_id)
    if not keys:
        logger.warning("源设备没有遥测数据")
        return

    logger.info(f"遥测键: {keys}")

    telemetry = sync.get_latest_telemetry(source_device_id, keys)
    if not telemetry:
        logger.warning("无法获取遥测数据")
        return

    # 转换数据格式
    data = {}
    ts = None
    for key, values in telemetry.items():
        if values:
            data[key] = values[0].get("value")
            if ts is None:
                ts = values[0].get("ts")

    logger.info(f"同步数据: {json.dumps(data, ensure_ascii=False)}")

    # 发送到所有目标设备
    for name, token in TARGET_DEVICES.items():
        if sync.send_telemetry(token, data, ts):
            logger.info(f"-> {name} 成功")
        else:
            logger.error(f"-> {name} 失败")


def sync_history(sync: ThingsBoardSync, source_device_id: str, hours: int = 24):
    """同步历史数据"""
    keys = sync.get_telemetry_keys(source_device_id)
    if not keys:
        logger.warning("源设备没有遥测数据")
        return

    end_ts = int(datetime.now().timestamp() * 1000)
    start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

    logger.info(f"同步最近 {hours} 小时历史数据...")

    history = sync.get_telemetry_history(source_device_id, keys, start_ts, end_ts)
    if not history:
        logger.warning("无历史数据")
        return

    # 按时间戳整理数据
    ts_data = {}
    for key, values in history.items():
        for item in values:
            ts = item.get("ts")
            value = item.get("value")
            if ts not in ts_data:
                ts_data[ts] = {}
            ts_data[ts][key] = value

    data_list = [{"ts": ts, "values": values} for ts, values in sorted(ts_data.items())]
    logger.info(f"共 {len(data_list)} 条记录")

    # 发送到所有目标设备
    for name, token in TARGET_DEVICES.items():
        count = sync.send_telemetry_batch(token, data_list)
        logger.info(f"-> {name}: {count}/{len(data_list)} 条成功")


def continuous_sync(sync: ThingsBoardSync, source_device_id: str, interval: int = 10):
    """持续同步模式"""
    logger.info(f"持续同步模式，间隔 {interval} 秒 (Ctrl+C 停止)")

    while True:
        try:
            sync_latest(sync, source_device_id)
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("同步已停止")
            break
        except Exception as e:
            logger.error(f"同步错误: {e}")
            time.sleep(interval)


def find_source_device(sync: ThingsBoardSync) -> str:
    """查找源设备ID"""
    # 方法1: 列出所有设备，找到匹配令牌的
    url = f"{sync.host}/api/tenant/devices?pageSize=1000&page=0"
    try:
        response = requests.get(url, headers=sync._headers())
        if response.status_code == 200:
            devices = response.json().get("data", [])
            for device in devices:
                device_id = device.get("id", {}).get("id")
                # 获取设备凭证
                cred_url = f"{sync.host}/api/device/{device_id}/credentials"
                cred_resp = requests.get(cred_url, headers=sync._headers())
                if cred_resp.status_code == 200:
                    cred = cred_resp.json().get("credentialsId")
                    if cred == SOURCE_DEVICE_TOKEN:
                        logger.info(f"找到源设备: {device.get('name')} (ID: {device_id})")
                        return device_id
    except Exception as e:
        logger.error(f"查找设备异常: {e}")
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description='ThingsBoard 数据同步工具')
    parser.add_argument('--mode', choices=['latest', 'history', 'continuous'],
                        default='latest', help='同步模式: latest/history/continuous')
    parser.add_argument('--hours', type=int, default=24, help='历史数据小时数 (默认24)')
    parser.add_argument('--interval', type=int, default=10, help='持续同步间隔秒数 (默认10)')
    args = parser.parse_args()

    print("=" * 50)
    print("ThingsBoard 数据同步工具")
    print("=" * 50)
    print(f"服务器: {THINGSBOARD_HOST}")
    print(f"源设备令牌: {SOURCE_DEVICE_TOKEN}")
    print(f"目标设备: {list(TARGET_DEVICES.keys())}")
    print("=" * 50)

    sync = ThingsBoardSync(THINGSBOARD_HOST)

    # 登录
    if not sync.login(ADMIN_USERNAME, ADMIN_PASSWORD):
        logger.error("登录失败，请检查配置")
        return

    # 使用预配置的源设备ID
    source_device_id = SOURCE_DEVICE_ID
    logger.info(f"源设备ID: {source_device_id}")

    if args.mode == "latest":
        sync_latest(sync, source_device_id)
    elif args.mode == "history":
        sync_history(sync, source_device_id, args.hours)
    elif args.mode == "continuous":
        continuous_sync(sync, source_device_id, args.interval)


if __name__ == "__main__":
    main()
