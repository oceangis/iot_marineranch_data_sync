#!/usr/bin/env python3
"""测试ThingsBoard API连接"""

import requests
import json

THINGSBOARD_HOST = "http://8.155.1.77:8080"
ADMIN_USERNAME = "tenant@thingsboard.org"
ADMIN_PASSWORD = "Obsis@123456"
SOURCE_TOKEN = "c0mtY8cl4SdUrhAuOAPr"

# 1. 登录
print("1. 登录测试...")
login_url = f"{THINGSBOARD_HOST}/api/auth/login"
login_resp = requests.post(login_url, json={
    "username": ADMIN_USERNAME,
    "password": ADMIN_PASSWORD
})
print(f"   状态码: {login_resp.status_code}")

if login_resp.status_code != 200:
    print(f"   登录失败: {login_resp.text}")
    exit(1)

jwt_token = login_resp.json().get("token")
headers = {"X-Authorization": f"Bearer {jwt_token}"}
print("   登录成功!")

# 2. 分页获取所有设备并查找源设备
print("\n2. 查找源设备 (分页遍历)...")
source_device_id = None
source_device_name = None
page = 0
total_devices = 0

while True:
    devices_url = f"{THINGSBOARD_HOST}/api/tenant/devices?pageSize=100&page={page}"
    devices_resp = requests.get(devices_url, headers=headers)

    if devices_resp.status_code != 200:
        print(f"   获取设备列表失败: {devices_resp.text}")
        break

    data = devices_resp.json()
    devices = data.get("data", [])
    total_devices += len(devices)
    print(f"   第{page+1}页: {len(devices)} 个设备")

    for device in devices:
        device_id = device.get("id", {}).get("id")
        device_name = device.get("name")

        # 获取设备凭证
        cred_url = f"{THINGSBOARD_HOST}/api/device/{device_id}/credentials"
        cred_resp = requests.get(cred_url, headers=headers)
        if cred_resp.status_code == 200:
            token = cred_resp.json().get("credentialsId")
            if token == SOURCE_TOKEN:
                print(f"\n   找到源设备: {device_name}")
                print(f"   设备ID: {device_id}")
                source_device_id = device_id
                source_device_name = device_name
                break

    if source_device_id or not data.get("hasNext", False):
        break
    page += 1

print(f"   总设备数: {total_devices}")

if source_device_id:
    # 3. 获取遥测键
    print("\n3. 获取遥测数据键...")
    keys_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{source_device_id}/keys/timeseries"
    keys_resp = requests.get(keys_url, headers=headers)
    print(f"   状态码: {keys_resp.status_code}")

    if keys_resp.status_code == 200:
        keys = keys_resp.json()
        print(f"   遥测键: {keys}")

        # 4. 获取最新遥测数据
        if keys:
            print("\n4. 获取最新遥测数据...")
            keys_param = ",".join(keys)
            telemetry_url = f"{THINGSBOARD_HOST}/api/plugins/telemetry/DEVICE/{source_device_id}/values/timeseries?keys={keys_param}"
            telemetry_resp = requests.get(telemetry_url, headers=headers)
            print(f"   状态码: {telemetry_resp.status_code}")

            if telemetry_resp.status_code == 200:
                telemetry = telemetry_resp.json()
                print(f"   数据: {json.dumps(telemetry, ensure_ascii=False, indent=2)}")
else:
    print("\n   未找到源设备!")

print("\n测试完成!")
