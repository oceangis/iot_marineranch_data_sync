# -*- coding: utf-8 -*-
"""
鑫智海洋牧场数据上传到ThingsBoard测试脚本
使用MQTT协议上传遥测数据
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tb_device_mqtt import TBDeviceMqttClient
from datetime import datetime
import time

# ThingsBoard 服务器配置
THINGSBOARD_HOST = "8.155.1.77"
THINGSBOARD_PORT = 1883  # MQTT默认端口

# 鑫智牧场设备信息
XINZHI_CONFIG = {
    "name": "鑫智海洋牧场",
    "thingsboard_id": "3d465bf0-d324-11f0-9be1-bfd0710a93d3",
    "token": "CVqpyb9S2cgrVL49i72r",
    "ranch_id": 133,
}


def upload_telemetry(client, telemetry_data):
    """上传遥测数据"""
    print(f"\n上传数据: {telemetry_data}")
    result = client.send_telemetry(telemetry_data)
    print(f"发送结果: {result}")
    return result


def main():
    """主函数"""
    print("=" * 60)
    print("鑫智海洋牧场 - ThingsBoard数据上传测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"服务器: {THINGSBOARD_HOST}:{THINGSBOARD_PORT}")
    print(f"设备Token: {XINZHI_CONFIG['token']}")
    print("=" * 60)

    # 创建MQTT客户端
    client = TBDeviceMqttClient(
        host=THINGSBOARD_HOST,
        port=THINGSBOARD_PORT,
        username=XINZHI_CONFIG['token']
    )

    try:
        # 连接到ThingsBoard
        print("\n[1] 连接ThingsBoard...")
        client.connect()
        print("[SUCCESS] 连接成功!")

        # 等待连接稳定
        time.sleep(1)

        # 准备测试遥测数据（模拟监测数据）
        now = datetime.now()
        telemetry = {
            # 气象数据
            "temp": 18.5,              # 气温
            "humidity": 65.0,          # 湿度
            "windSpeed": 3.2,          # 风速
            "windDirection": 180,      # 风向
            "pressure": 1013.25,       # 气压

            # 水质数据
            "waterTemperature": 12.3,  # 水温
            "waterDepth": 15.5,        # 水深
            "salinity": 32.5,          # 盐度
            "oxygen": 8.2,             # 溶解氧
            "ph": 8.1,                 # pH值
            "chlorophyll": 2.5,        # 叶绿素
            "turbidity": 5.0,          # 浊度

            # 海流数据
            "averageVelocity": 0.35,   # 平均流速
            "firstVelocity": 0.42,     # 第一层流速
            "secondVelocity": 0.38,    # 第二层流速
            "thirdVelocity": 0.35,     # 第三层流速
            "fourthVelocity": 0.30,    # 第四层流速
            "fifthVelocity": 0.25,     # 第五层流速

            # 波浪数据（鑫智无波浪传感器，设为0）
            "waveHeigh": 0,            # 波高
            "wavePeriod": 0,           # 波周期
            "waveDirection": 0,        # 波向

            # 时间戳
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 上传遥测数据
        print("\n[2] 上传遥测数据...")
        result = upload_telemetry(client, telemetry)

        # 等待数据发送完成
        time.sleep(2)

        # 也可以发送带时间戳的数据
        print("\n[3] 上传带时间戳的数据...")
        ts_telemetry = {
            "ts": int(now.timestamp() * 1000),  # 毫秒时间戳
            "values": {
                "temp": 18.6,
                "humidity": 64.5,
                "waterTemperature": 12.4,
            }
        }
        client.send_telemetry(ts_telemetry)
        print(f"发送数据: {ts_telemetry}")

        time.sleep(2)

        print("\n[SUCCESS] 数据上传完成!")
        print(f"请在ThingsBoard控制台查看设备 '{XINZHI_CONFIG['name']}' 的遥测数据")

    except Exception as e:
        print(f"\n[ERROR] 错误: {type(e).__name__}: {e}")

    finally:
        # 断开连接
        print("\n[4] 断开连接...")
        client.disconnect()
        print("已断开连接")


if __name__ == "__main__":
    main()
