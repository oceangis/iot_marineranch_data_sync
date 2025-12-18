# -*- coding: utf-8 -*-
"""
ThingsBoard到海洋牧场API数据同步脚本
从ThingsBoard读取设备遥测数据，同步上传到海洋牧场监测数据API
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from datetime import datetime

# ============================================================
# 配置信息
# ============================================================

# ThingsBoard配置
THINGSBOARD_URL = "http://8.155.1.77:8080"
THINGSBOARD_USERNAME = "tenant@thingsboard.org"
THINGSBOARD_PASSWORD = "Obsis@123456"

# 海洋牧场API配置
RANCH_API_URL = "http://www.zghymcw.com/ranch/dataReport"

# 牧场设备配置
RANCHES = {
    "鑫智": {
        "ranch_id": 133,
        "thingsboard_device_id": "3d465bf0-d324-11f0-9be1-bfd0710a93d3",
        "thingsboard_token": "CVqpyb9S2cgrVL49i72r",
        "wave_device_id": None,  # 无波浪设备
    },
    "大栏石": {
        "ranch_id": 132,
        "thingsboard_device_id": "b6eabb90-c8e8-11f0-9be1-bfd0710a93d3",
        "thingsboard_token": "IxllICGedtj0QChYVyTU",
        "wave_device_id": "ff8bbc60-c9a5-11f0-9be1-bfd0710a93d3",  # 波浪设备
        "wave_token": "AxlCN39FomVeaMp1tbng",
    },
    "敬武": {
        "ranch_id": 159,
        "thingsboard_device_id": None,  # 待补充主设备ID
        "thingsboard_token": None,
        "wave_device_id": None,  # 待补充波浪设备ID
    },
}

# ThingsBoard字段 → 海洋牧场API字段映射
FIELD_MAPPING = {
    # 气象数据
    "air_temp": "temp",              # 气温
    "humidity": "humidity",          # 湿度
    "wind_speed": "windSpeed",       # 风速
    "wind_dir": "windDirection",     # 风向
    "pressure": "pressure",          # 气压

    # 水质数据
    "water_temp": "waterTemperature",  # 水温
    "depth": "waterDepth",             # 水深
    "dissolved_oxygen": "oxygen",      # 溶解氧
    "pH": "ph",                        # pH值
    "salinity": "salinity",            # 盐度
    "turbidity": "turbidity",          # 浊度

    # 海流数据 - 使用层数据
    "surface_current_speed": "averageVelocity",  # 平均流速(表层)
    "layer_2m_speed": "firstVelocity",           # 第一层流速(2m)
    "layer_3m_speed": "secondVelocity",          # 第二层流速(3m)
    "layer_4m_speed": "thirdVelocity",           # 第三层流速(4m)
    "layer_5m_speed": "fourthVelocity",          # 第四层流速(5m)
    "layer_6m_speed": "fifthVelocity",           # 第五层流速(6m)
}

# 波浪设备字段映射
WAVE_FIELD_MAPPING = {
    "Hs": "waveHeigh",        # 有效波高
    "Tp": "wavePeriod",       # 峰值周期
    "Dp": "waveDirection",    # 峰值波向
}

# ============================================================
# ThingsBoard API
# ============================================================

class ThingsBoardClient:
    def __init__(self, url, username, password):
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None

    def login(self):
        """登录获取JWT token"""
        login_url = f"{self.url}/api/auth/login"
        resp = requests.post(login_url, json={
            "username": self.username,
            "password": self.password
        }, timeout=30)

        if resp.status_code == 200:
            self.token = resp.json()["token"]
            return True
        else:
            raise Exception(f"登录失败: {resp.status_code} {resp.text}")

    def get_headers(self):
        return {"X-Authorization": f"Bearer {self.token}"}

    def get_device_telemetry(self, device_id, keys=None):
        """获取设备最新遥测数据"""
        if keys:
            keys_str = ",".join(keys) if isinstance(keys, list) else keys
            url = f"{self.url}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys={keys_str}"
        else:
            # 先获取所有键
            keys_url = f"{self.url}/api/plugins/telemetry/DEVICE/{device_id}/keys/timeseries"
            resp = requests.get(keys_url, headers=self.get_headers(), timeout=30)
            all_keys = resp.json()
            keys_str = ",".join(all_keys)
            url = f"{self.url}/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries?keys={keys_str}"

        resp = requests.get(url, headers=self.get_headers(), timeout=30)

        if resp.status_code == 200:
            return resp.json()
        else:
            raise Exception(f"获取遥测数据失败: {resp.status_code} {resp.text}")


# ============================================================
# 数据转换
# ============================================================

def convert_telemetry_to_ranch_format(telemetry, ranch_id):
    """
    将ThingsBoard遥测数据转换为海洋牧场API格式

    Args:
        telemetry: ThingsBoard遥测数据 {key: [{ts, value}]}
        ranch_id: 牧场ID

    Returns:
        dict: 海洋牧场API请求数据
    """
    now = datetime.now()
    monitor_time = now.strftime("%Y-%m-%d %H:%M:%S")

    item_list = []

    # 遍历字段映射，提取数据
    for tb_key, ranch_key in FIELD_MAPPING.items():
        if tb_key in telemetry and telemetry[tb_key]:
            value = telemetry[tb_key][0].get("value")
            ts = telemetry[tb_key][0].get("ts")

            if value is not None:
                # 转换时间戳
                data_time = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")

                # 海流速度单位转换：ThingsBoard是cm/s，API可能需要m/s
                if "Velocity" in ranch_key or "velocity" in ranch_key.lower():
                    # 假设ThingsBoard数据是cm/s，转换为m/s
                    try:
                        value = float(value) / 100.0
                    except:
                        pass

                # 鑫智浊度数据校准：加上4.5
                if ranch_key == "turbidity" and ranch_id == 133:
                    try:
                        value = float(value) + 4.5
                    except:
                        pass

                # 大栏石pH数据校准：减去9
                if ranch_key == "ph" and ranch_id == 132:
                    try:
                        value = float(value) - 9
                    except:
                        pass

                item_list.append({
                    "key": ranch_key,
                    "value": str(value),
                    "monitorTime": data_time
                })

    # 处理波浪设备数据映射
    for tb_key, ranch_key in WAVE_FIELD_MAPPING.items():
        if tb_key in telemetry and telemetry[tb_key]:
            value = telemetry[tb_key][0].get("value")
            ts = telemetry[tb_key][0].get("ts")

            if value is not None:
                data_time = datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
                item_list.append({
                    "key": ranch_key,
                    "value": str(value),
                    "monitorTime": data_time
                })

    # 添加波浪数据（如果没有则设为0）
    wave_keys = ["waveHeigh", "wavePeriod", "waveDirection"]
    for wk in wave_keys:
        # 检查是否已有该数据
        exists = any(item["key"] == wk for item in item_list)
        if not exists:
            item_list.append({
                "key": wk,
                "value": "0",
                "monitorTime": monitor_time
            })

    return {
        "ranchId": ranch_id,
        "reportTime": now.strftime("%Y-%m-%d"),
        "itemList": item_list
    }


# ============================================================
# 海洋牧场API
# ============================================================

def upload_to_ranch_api(data):
    """上传数据到海洋牧场API"""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json"
    }

    resp = requests.post(
        RANCH_API_URL,
        json=data,
        headers=headers,
        timeout=30
    )

    if resp.status_code == 200:
        result = resp.json()
        return result
    else:
        raise Exception(f"上传失败: {resp.status_code} {resp.text}")


# ============================================================
# 同步函数
# ============================================================

def sync_ranch(ranch_name, config):
    """同步单个牧场数据"""
    print(f"\n{'='*60}")
    print(f"同步牧场: {ranch_name}")
    print(f"牧场ID: {config['ranch_id']}")
    print(f"主设备ID: {config.get('thingsboard_device_id', '无')}")
    print(f"波浪设备ID: {config.get('wave_device_id', '无')}")
    print(f"{'='*60}")

    try:
        # 1. 从ThingsBoard读取数据
        print("\n[1] 从ThingsBoard读取遥测数据...")
        tb_client = ThingsBoardClient(
            THINGSBOARD_URL,
            THINGSBOARD_USERNAME,
            THINGSBOARD_PASSWORD
        )
        tb_client.login()

        telemetry = {}

        # 读取主设备数据
        if config.get("thingsboard_device_id"):
            telemetry = tb_client.get_device_telemetry(config["thingsboard_device_id"])
            print(f"    主设备: 读取到 {len(telemetry)} 个遥测键")

        # 读取波浪设备数据
        if config.get("wave_device_id"):
            wave_telemetry = tb_client.get_device_telemetry(config["wave_device_id"])
            print(f"    波浪设备: 读取到 {len(wave_telemetry)} 个遥测键")
            # 合并波浪数据
            telemetry.update(wave_telemetry)

        print(f"    合计: {len(telemetry)} 个遥测键")

        # 打印部分原始数据
        print("\n    原始数据预览:")
        preview_keys = ["air_temp", "water_temp", "dissolved_oxygen", "pH", "salinity", "wind_speed", "pressure"]
        for k in preview_keys:
            if k in telemetry and telemetry[k]:
                v = telemetry[k][0]
                ts = datetime.fromtimestamp(v['ts']/1000).strftime('%H:%M:%S')
                print(f"      {k}: {v['value']} ({ts})")

        # 2. 转换数据格式
        print("\n[2] 转换数据格式...")
        ranch_data = convert_telemetry_to_ranch_format(telemetry, config["ranch_id"])
        print(f"    转换后 {len(ranch_data['itemList'])} 个数据项")

        # 打印转换后的数据
        print("\n    转换后数据预览:")
        for item in ranch_data["itemList"][:10]:
            print(f"      {item['key']}: {item['value']} ({item['monitorTime']})")
        if len(ranch_data["itemList"]) > 10:
            print(f"      ... 共 {len(ranch_data['itemList'])} 项")

        # 3. 上传到海洋牧场API
        print("\n[3] 上传到海洋牧场API...")
        result = upload_to_ranch_api(ranch_data)

        code = result.get("code")
        msg = result.get("msg", "")

        if str(code) == "0":
            print(f"\n[SUCCESS] 同步成功! {msg}")
            return True, result
        else:
            print(f"\n[FAILED] 同步失败: code={code}, msg={msg}")
            return False, result

    except Exception as e:
        print(f"\n[ERROR] 同步异常: {type(e).__name__}: {e}")
        return False, {"error": str(e)}


def main(ranch_filter=None):
    """
    主函数
    Args:
        ranch_filter: 指定要同步的牧场名称，None则同步所有
    """
    print("=" * 60)
    print("ThingsBoard → 海洋牧场API 数据同步")
    print(f"同步时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = {}

    for ranch_name, config in RANCHES.items():
        # 如果指定了过滤器，只同步指定的牧场
        if ranch_filter and ranch_name != ranch_filter:
            continue

        success, result = sync_ranch(ranch_name, config)
        results[ranch_name] = {
            "success": success,
            "result": result
        }

    # 打印同步摘要
    print("\n\n")
    print("=" * 60)
    print("同步结果摘要")
    print("=" * 60)

    for ranch_name, data in results.items():
        status = "[OK]" if data["success"] else "[FAIL]"
        result = data["result"]
        msg = result.get("msg", result.get("error", ""))
        print(f"{ranch_name:10} | {status:6} | {msg}")

    return results


if __name__ == "__main__":
    import sys
    # 支持命令行参数指定牧场: python sync_thingsboard_to_ranch.py 大栏石
    ranch_filter = sys.argv[1] if len(sys.argv) > 1 else None
    main(ranch_filter)
