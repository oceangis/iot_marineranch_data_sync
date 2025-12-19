#!/usr/bin/env python3
"""
同步历史数据到合并设备
一次性执行，用于初始化历史数据
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ThingsBoard 配置
THINGSBOARD_HOST = "http://8.155.1.77:8080"
ADMIN_USERNAME = "tenant@thingsboard.org"
ADMIN_PASSWORD = "Obsis@123456"

# 鑫智配置
XINZHI_SOURCE_ID = "3d465bf0-d324-11f0-9be1-bfd0710a93d3"  # 863482063082305
XINZHI_REF_ID = "23bfe860-b478-11f0-9be1-bfd0710a93d3"     # 861556078781175 (提供dst800_water_temp, turbidity)
XINZHI_TARGET_TOKEN = "bNKptyoymZnrAJF7nsS0"               # 863482063082305-3

# 涛声依旧配置
TAOSHENG_SOURCE_ID = "61a0c870-b491-11f0-9be1-bfd0710a93d3"  # 861556078780730
TAOSHENG_REF1_ID = "b6eabb90-c8e8-11f0-9be1-bfd0710a93d3"    # 860549070048066 (提供dst800_water_temp)
TAOSHENG_REF2_ID = "173122a0-dc17-11f0-9be1-bfd0710a93d3"    # 861556078780730-2 (提供salinity)
TAOSHENG_REF3_ID = "23bfe860-b478-11f0-9be1-bfd0710a93d3"    # 861556078781175 (备用salinity填充)
TAOSHENG_TARGET_TOKEN = "gcDQy609RwagbzK6OXie"               # 861556078780730-3

# 敬武配置
JINGWU_SOURCE_ID = "23bfe860-b478-11f0-9be1-bfd0710a93d3"    # 861556078781175
JINGWU_REF_ID = "3d465bf0-d324-11f0-9be1-bfd0710a93d3"       # 863482063082305 (提供wind_speed, wind_dir)
JINGWU_TARGET_TOKEN = "OvHRcXUMuvlSkDvpFyks"                  # 861556078781175-2

# sensor_wave配置
SENSOR_WAVE_SOURCE_ID = "ff8bbc60-c9a5-11f0-9be1-bfd0710a93d3"  # sensor_wave_gnssm10s
SENSOR_WAVE_TARGET_TOKEN = "2XrliENQlPWJaV8osIMv"                # sensor_wave_gnssm10s_2


class HistorySync:
    def __init__(self):
        self.jwt_token = None

    def login(self) -> bool:
        url = f"{THINGSBOARD_HOST}/api/auth/login"
        try:
            resp = requests.post(url, json={
                "username": ADMIN_USERNAME,
                "password": ADMIN_PASSWORD
            }, timeout=10)
            if resp.status_code == 200:
                self.jwt_token = resp.json().get("token")
                logger.info("登录成功")
                return True
        except Exception as e:
            logger.error(f"登录失败: {e}")
        return False

    def _headers(self) -> Dict:
        return {"X-Authorization": f"Bearer {self.jwt_token}"}

    def get_keys(self, device_id: str) -> List[str]:
        url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{device_id}/keys/timeseries"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return []

    def get_history(self, device_id: str, keys: List[str], start_ts: int, end_ts: int) -> Dict:
        keys_param = ",".join(keys)
        url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys={keys_param}&startTs={start_ts}&endTs={end_ts}&limit=100000"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=60)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}")
        return {}

    def send_telemetry(self, token: str, ts: int, data: Dict) -> bool:
        url = f"{THINGSBOARD_HOST}/api/v1/{token}/telemetry"
        try:
            resp = requests.post(url, json={"ts": ts, "values": data}, timeout=10)
            return resp.status_code == 200
        except:
            return False

    def sync_xinzhi_history(self, hours: int = 72):
        """同步鑫智历史数据"""
        logger.info(f"同步鑫智历史数据 (最近{hours}小时)...")

        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        # 获取源设备的所有键
        source_keys = self.get_keys(XINZHI_SOURCE_ID)
        if not source_keys:
            logger.error("无法获取源设备键")
            return

        logger.info(f"源设备键: {len(source_keys)} 个")

        # 获取源设备历史数据
        source_history = self.get_history(XINZHI_SOURCE_ID, source_keys, start_ts, end_ts)
        if not source_history:
            logger.error("无法获取源设备历史数据")
            return

        # 获取参考设备的历史数据 (dst800_water_temp, turbidity)
        ref_history = self.get_history(XINZHI_REF_ID, ["dst800_water_temp", "turbidity"], start_ts, end_ts)

        # 整理源数据按时间戳
        ts_data = {}
        for key, values in source_history.items():
            for item in values:
                ts = item.get("ts")
                value = item.get("value")
                if ts not in ts_data:
                    ts_data[ts] = {}
                ts_data[ts][key] = value

        logger.info(f"源数据: {len(ts_data)} 条记录")

        # 整理参考数据按时间戳
        ref_ts_data = {}
        if ref_history:
            for key, values in ref_history.items():
                for item in values:
                    ts = item.get("ts")
                    value = item.get("value")
                    if ts not in ref_ts_data:
                        ref_ts_data[ts] = {}
                    if key == "turbidity":
                        ref_ts_data[ts]["turbidity1"] = value
                    else:
                        ref_ts_data[ts][key] = value

        logger.info(f"参考数据: {len(ref_ts_data)} 条记录")

        # 合并并发送
        success = 0
        total = len(ts_data)
        for i, (ts, data) in enumerate(sorted(ts_data.items())):
            # 查找最接近的参考数据
            if ref_ts_data:
                closest_ts = min(ref_ts_data.keys(), key=lambda x: abs(x - ts))
                if abs(closest_ts - ts) < 600000:  # 10分钟内
                    data.update(ref_ts_data[closest_ts])

            if self.send_telemetry(XINZHI_TARGET_TOKEN, ts, data):
                success += 1

            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i+1}/{total}")
            time.sleep(0.01)

        logger.info(f"鑫智历史同步完成: {success}/{total}")

    def sync_taosheng_history(self, hours: int = 72):
        """同步涛声依旧历史数据"""
        logger.info(f"同步涛声依旧历史数据 (最近{hours}小时)...")

        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        # 获取源设备的所有键
        source_keys = self.get_keys(TAOSHENG_SOURCE_ID)
        if not source_keys:
            logger.error("无法获取源设备键")
            return

        logger.info(f"源设备键: {len(source_keys)} 个")

        # 获取源设备历史数据
        source_history = self.get_history(TAOSHENG_SOURCE_ID, source_keys, start_ts, end_ts)
        if not source_history:
            logger.error("无法获取源设备历史数据")
            return

        # 获取参考设备1的历史数据 (dst800_water_temp)
        ref1_history = self.get_history(TAOSHENG_REF1_ID, ["dst800_water_temp"], start_ts, end_ts)

        # 获取参考设备2的历史数据 (salinity)
        ref2_history = self.get_history(TAOSHENG_REF2_ID, ["salinity"], start_ts, end_ts)

        # 获取参考设备3的历史数据 (salinity备用填充 - 敬武861556078781175)
        ref3_history = self.get_history(TAOSHENG_REF3_ID, ["salinity"], start_ts, end_ts)

        # 整理源数据按时间戳
        ts_data = {}
        for key, values in source_history.items():
            for item in values:
                ts = item.get("ts")
                value = item.get("value")
                if ts not in ts_data:
                    ts_data[ts] = {}
                ts_data[ts][key] = value

        logger.info(f"源数据: {len(ts_data)} 条记录")

        # 整理参考数据1按时间戳
        ref1_ts_data = {}
        if ref1_history:
            for key, values in ref1_history.items():
                for item in values:
                    ts = item.get("ts")
                    value = item.get("value")
                    ref1_ts_data[ts] = {"dst800_water_temp": value}

        # 整理参考数据2按时间戳
        ref2_ts_data = {}
        if ref2_history:
            for key, values in ref2_history.items():
                for item in values:
                    ts = item.get("ts")
                    value = item.get("value")
                    ref2_ts_data[ts] = {"salinity1": value}

        # 整理参考数据3按时间戳 (备用salinity)
        ref3_ts_data = {}
        if ref3_history:
            for key, values in ref3_history.items():
                for item in values:
                    ts = item.get("ts")
                    value = item.get("value")
                    ref3_ts_data[ts] = {"salinity1": value}

        logger.info(f"参考数据1: {len(ref1_ts_data)} 条, 参考数据2: {len(ref2_ts_data)} 条, 参考数据3(备用): {len(ref3_ts_data)} 条")

        # 合并并发送
        success = 0
        total = len(ts_data)
        for i, (ts, data) in enumerate(sorted(ts_data.items())):
            # 查找最接近的参考数据1
            if ref1_ts_data:
                closest_ts = min(ref1_ts_data.keys(), key=lambda x: abs(x - ts))
                if abs(closest_ts - ts) < 600000:  # 10分钟内
                    data.update(ref1_ts_data[closest_ts])

            # 查找最接近的参考数据2，如果没有则用参考数据3填充
            salinity_found = False
            if ref2_ts_data:
                closest_ts = min(ref2_ts_data.keys(), key=lambda x: abs(x - ts))
                if abs(closest_ts - ts) < 600000:  # 10分钟内
                    data.update(ref2_ts_data[closest_ts])
                    salinity_found = True

            # 如果ref2没有找到salinity，使用ref3(敬武)的数据填充
            if not salinity_found and ref3_ts_data:
                closest_ts = min(ref3_ts_data.keys(), key=lambda x: abs(x - ts))
                if abs(closest_ts - ts) < 600000:  # 10分钟内
                    data.update(ref3_ts_data[closest_ts])

            if self.send_telemetry(TAOSHENG_TARGET_TOKEN, ts, data):
                success += 1

            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i+1}/{total}")
            time.sleep(0.01)

        logger.info(f"涛声依旧历史同步完成: {success}/{total}")

    def sync_jingwu_history(self, hours: int = 72):
        """同步敬武历史数据"""
        logger.info(f"同步敬武历史数据 (最近{hours}小时)...")

        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        # 获取源设备的所有键
        source_keys = self.get_keys(JINGWU_SOURCE_ID)
        if not source_keys:
            logger.error("无法获取源设备键")
            return

        logger.info(f"源设备键: {len(source_keys)} 个")

        # 获取源设备历史数据
        source_history = self.get_history(JINGWU_SOURCE_ID, source_keys, start_ts, end_ts)
        if not source_history:
            logger.error("无法获取源设备历史数据")
            return

        # 获取参考设备的历史数据 (air_temp, wind_speed, wind_dir)
        ref_history = self.get_history(JINGWU_REF_ID, ["air_temp", "wind_speed", "wind_dir"], start_ts, end_ts)

        # 整理源数据按时间戳
        ts_data = {}
        for key, values in source_history.items():
            for item in values:
                ts = item.get("ts")
                value = item.get("value")
                if ts not in ts_data:
                    ts_data[ts] = {}
                ts_data[ts][key] = value

        logger.info(f"源数据: {len(ts_data)} 条记录")

        # 整理参考数据按时间戳
        ref_ts_data = {}
        if ref_history:
            for key, values in ref_history.items():
                for item in values:
                    ts = item.get("ts")
                    value = item.get("value")
                    if ts not in ref_ts_data:
                        ref_ts_data[ts] = {}
                    if key == "air_temp":
                        ref_ts_data[ts]["air_temp1"] = value
                    elif key == "wind_speed":
                        ref_ts_data[ts]["wind_speed1"] = value
                    elif key == "wind_dir":
                        ref_ts_data[ts]["wind_dir1"] = value

        logger.info(f"参考数据: {len(ref_ts_data)} 条记录")

        # 合并并发送
        success = 0
        total = len(ts_data)
        for i, (ts, data) in enumerate(sorted(ts_data.items())):
            # 查找最接近的参考数据
            if ref_ts_data:
                closest_ts = min(ref_ts_data.keys(), key=lambda x: abs(x - ts))
                if abs(closest_ts - ts) < 600000:  # 10分钟内
                    data.update(ref_ts_data[closest_ts])

            if self.send_telemetry(JINGWU_TARGET_TOKEN, ts, data):
                success += 1

            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i+1}/{total}")
            time.sleep(0.01)

        logger.info(f"敬武历史同步完成: {success}/{total}")

    def sync_sensor_wave_history(self, hours: int = 72):
        """同步sensor_wave历史数据 (完全复制)"""
        logger.info(f"同步sensor_wave历史数据 (最近{hours}小时)...")

        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(hours=hours)).timestamp() * 1000)

        # 获取源设备的所有键
        source_keys = self.get_keys(SENSOR_WAVE_SOURCE_ID)
        if not source_keys:
            logger.error("无法获取源设备键")
            return

        logger.info(f"源设备键: {len(source_keys)} 个")

        # 获取源设备历史数据
        source_history = self.get_history(SENSOR_WAVE_SOURCE_ID, source_keys, start_ts, end_ts)
        if not source_history:
            logger.error("无法获取源设备历史数据")
            return

        # 整理源数据按时间戳
        ts_data = {}
        for key, values in source_history.items():
            for item in values:
                ts = item.get("ts")
                value = item.get("value")
                if ts not in ts_data:
                    ts_data[ts] = {}
                ts_data[ts][key] = value

        logger.info(f"源数据: {len(ts_data)} 条记录")

        # 发送到目标设备
        success = 0
        total = len(ts_data)
        for i, (ts, data) in enumerate(sorted(ts_data.items())):
            if self.send_telemetry(SENSOR_WAVE_TARGET_TOKEN, ts, data):
                success += 1

            if (i + 1) % 100 == 0:
                logger.info(f"进度: {i+1}/{total}")
            time.sleep(0.01)

        logger.info(f"sensor_wave历史同步完成: {success}/{total}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='同步历史数据')
    parser.add_argument('--hours', type=int, default=72, help='同步多少小时的历史数据 (默认72)')
    parser.add_argument('--target', choices=['xinzhi', 'taosheng', 'jingwu', 'sensor_wave', 'all'], default='all', help='同步目标')
    args = parser.parse_args()

    sync = HistorySync()
    if not sync.login():
        return

    if args.target in ['xinzhi', 'all']:
        sync.sync_xinzhi_history(args.hours)

    if args.target in ['taosheng', 'all']:
        sync.sync_taosheng_history(args.hours)

    if args.target in ['jingwu', 'all']:
        sync.sync_jingwu_history(args.hours)

    if args.target in ['sensor_wave', 'all']:
        sync.sync_sensor_wave_history(args.hours)


if __name__ == "__main__":
    main()
