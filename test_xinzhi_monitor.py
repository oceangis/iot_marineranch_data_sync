# -*- coding: utf-8 -*-
"""
牧场监测数据接入API测试脚本
测试鑫智国家级海洋牧场示范区监测数据上传
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API端点配置
API_ENDPOINTS = {
    "test1": "http://www.zghymcw.com/ranch/dataReport",      # 测试库 10.16.242.173
    "test2": "http://hymc.qnlm.com.cn/ranch/dataReport",     # 测试库 10.16.182.20
    "prod": "https://58.56.138.6/ranch/dataReport"           # 生产环境
}

# 鑫智牧场ID
XINZHI_RANCH_ID = 133

# 观测数据元素类型列表
DATA_KEYS = {
    # 气象数据
    "temp": "气温",
    "humidity": "湿度",
    "windSpeed": "风速",
    "windDirection": "风向",
    "rainfall": "雨量",
    "pressure": "气压",
    # 水质数据
    "waterTemperature": "水温",
    "waterDepth": "水深",
    "chlorophyll": "叶绿素",
    "salinity": "盐度",
    "oxygen": "溶解氧",
    "ph": "pH值",
    "totalDissolvedSolids": "TDS总溶解固体",
    "turbidity": "浊度",
    # 海流数据
    "averageVelocity": "平均流速",
    "firstVelocity": "第一层流速",
    "secondVelocity": "第二层流速",
    "thirdVelocity": "第三层流速",
    "fourthVelocity": "第四层流速",
    "fifthVelocity": "第五层流速",
    # 波浪数据
    "waveHeigh": "波高",
    "wavePeriod": "波周期",
    "waveDirection": "波向",
    # 营养盐数据
    "nitrate": "硝酸盐",
    "nitrite": "亚硝酸盐",
    "ammoniaNitrogen": "氨氮",
    "phosphate": "磷酸盐",
    "silicate": "硅酸盐",
    # 潮位仪数据
    "waterTemp2": "水温2",
    "waterDep2": "水深2",
}


def build_monitor_data(ranch_id, item_list=None):
    """
    构建监测数据请求体

    Args:
        ranch_id: 牧场ID
        item_list: 观测数据列表，None则使用空列表

    Returns:
        dict: 请求数据
    """
    now = datetime.now()

    data = {
        "ranchId": ranch_id,
        "reportTime": now.strftime("%Y-%m-%d"),
        "itemList": item_list if item_list else []
    }

    return data


def build_sample_data(ranch_id):
    """
    构建示例监测数据（包含一些测试值）

    Args:
        ranch_id: 牧场ID

    Returns:
        dict: 请求数据
    """
    now = datetime.now()
    monitor_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 示例数据
    item_list = [
        {"key": "temp", "value": "18.5", "monitorTime": monitor_time},
        {"key": "humidity", "value": "65.0", "monitorTime": monitor_time},
        {"key": "waterTemperature", "value": "12.3", "monitorTime": monitor_time},
    ]

    data = {
        "ranchId": ranch_id,
        "reportTime": now.strftime("%Y-%m-%d"),
        "itemList": item_list
    }

    return data


def submit_monitor_data(url, data, timeout=30):
    """提交监测数据"""
    print(f"\n{'='*60}")
    print(f"提交监测数据到: {url}")
    print(f"{'='*60}")

    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Accept": "application/json"
    }

    print("\n请求数据:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    try:
        response = requests.post(
            url,
            json=data,
            headers=headers,
            timeout=timeout,
            verify=False
        )

        print(f"\n响应状态码: {response.status_code}")

        try:
            result = response.json()
            print(f"响应数据: {json.dumps(result, ensure_ascii=False)}")

            code = result.get("code")
            msg = result.get("msg", "")

            # code可能是字符串"0"或整数0
            if str(code) == "0":
                print(f"\n[SUCCESS] 数据上传成功!")
                return True, result
            else:
                print(f"\n[FAILED] 上传失败: {msg}")
                return False, result

        except json.JSONDecodeError:
            print(f"\n响应内容 (非JSON): {response.text[:500]}")
            return False, {"error": "响应不是有效的JSON格式", "raw": response.text[:200]}

    except requests.exceptions.ConnectTimeout:
        print(f"连接超时")
        return False, {"error": "连接超时"}
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        return False, {"error": str(e)}
    except Exception as e:
        print(f"请求异常: {type(e).__name__}: {e}")
        return False, {"error": str(e)}


def test_empty_data():
    """测试空数据上传"""
    print("\n" + "#"*60)
    print("# 测试1: 空数据上传 (itemList为空列表)")
    print("#"*60)

    data = build_monitor_data(XINZHI_RANCH_ID, item_list=[])
    url = API_ENDPOINTS["test1"]

    return submit_monitor_data(url, data)


def test_sample_data():
    """测试示例数据上传"""
    print("\n" + "#"*60)
    print("# 测试2: 示例数据上传 (包含气温、湿度、水温)")
    print("#"*60)

    data = build_sample_data(XINZHI_RANCH_ID)
    url = API_ENDPOINTS["test1"]

    return submit_monitor_data(url, data)


def main():
    """主测试函数"""
    print("=" * 60)
    print("牧场监测数据接入API测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"牧场ID: {XINZHI_RANCH_ID} (鑫智)")
    print("=" * 60)

    results = {}

    # 测试1: 空数据
    success1, resp1 = test_empty_data()
    results["empty_data"] = {"success": success1, "response": resp1}

    # 测试2: 示例数据
    success2, resp2 = test_sample_data()
    results["sample_data"] = {"success": success2, "response": resp2}

    # 打印测试摘要
    print("\n\n")
    print("=" * 60)
    print("测试结果摘要")
    print("=" * 60)

    for test_name, result in results.items():
        status = "[OK]" if result["success"] else "[FAIL]"
        resp = result["response"]
        code = resp.get("code", resp.get("error", "N/A"))
        msg = resp.get("msg", resp.get("error", ""))
        print(f"{test_name:15} | {status:6} | code={code} | {msg}")

    return results


if __name__ == "__main__":
    main()
