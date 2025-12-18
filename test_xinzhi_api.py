# -*- coding: utf-8 -*-
"""
牧场基础信息接入API测试脚本
测试鑫智国家级海洋牧场示范区数据接入
"""

import requests
import json
from datetime import datetime

# API端点配置
API_ENDPOINTS = {
    "test1": "http://www.zghymcw.com/ranch/ranchInfo",      # 测试库 10.16.242.173
    "test2": "http://hymc.qnlm.com.cn/ranch/ranchInfo",     # 测试库 10.16.182.20
    "prod": "https://58.56.138.6/ranch/ranchInfo"           # 生产环境
}

# 鑫智牧场基础信息
# 原始坐标: [[35.654535,119.9431528],[35.65454528, 119.9733094],[35.66444639, 119.9733061],[35.66443611, 119.9431456]]
# 注意：原始数据是 [纬度, 经度] 格式，需要转换为 [经度, 纬度] 的GeoJSON标准格式
XINZHI_DATA = {
    "aquafarmName": "青岛市斋堂岛海域鑫智国家级海洋牧场示范区",
    "province": "山东省",
    "city": "青岛市",
    "type": "休闲、贝类养殖、垂钓",
    "geojson": json.dumps({
        "type": "Polygon",
        "coordinates": [[
            [119.9431528, 35.654535],
            [119.9733094, 35.65454528],
            [119.9733061, 35.66444639],
            [119.9431456, 35.66443611],
            [119.9431528, 35.654535]  # 闭合多边形
        ]]
    }, ensure_ascii=False)
}


def test_api_connection(url, timeout=10):
    """测试API连接是否可达"""
    print(f"\n{'='*60}")
    print(f"测试API连接: {url}")
    print(f"{'='*60}")

    try:
        # 先测试GET请求看服务器是否响应
        response = requests.get(url, timeout=timeout)
        print(f"GET请求状态码: {response.status_code}")
        return True
    except requests.exceptions.ConnectTimeout:
        print(f"连接超时 (>{timeout}秒)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        return False
    except Exception as e:
        print(f"其他错误: {type(e).__name__}: {e}")
        return False


def submit_ranch_info(url, data, timeout=30):
    """提交牧场基础信息"""
    print(f"\n{'='*60}")
    print(f"提交牧场信息到: {url}")
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
            verify=False  # 生产环境可能使用自签名证书
        )

        print(f"\n响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")

        # 尝试解析JSON响应
        try:
            result = response.json()
            print(f"\n响应数据 (JSON):")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # 检查返回码
            code = result.get("code")
            msg = result.get("msg", "")

            if code == 0:
                print(f"\n[SUCCESS] 接入成功! 牧场ID: {result.get('ranchId')}")
                return True, result
            elif code == 400 and "已存在" in msg:
                # 牧场已存在说明之前接入成功
                print(f"\n[ALREADY EXISTS] 牧场已存在于系统中（之前已成功接入）")
                return True, result  # 视为成功
            else:
                print(f"\n[FAILED] 接入失败: {msg}")
                return False, result

        except json.JSONDecodeError:
            print(f"\n响应内容 (非JSON):")
            print(response.text[:500] if len(response.text) > 500 else response.text)
            return False, {"error": "响应不是有效的JSON格式"}

    except requests.exceptions.ConnectTimeout:
        print(f"连接超时 (>{timeout}秒)")
        return False, {"error": "连接超时"}
    except requests.exceptions.ConnectionError as e:
        print(f"连接错误: {e}")
        return False, {"error": str(e)}
    except Exception as e:
        print(f"请求异常: {type(e).__name__}: {e}")
        return False, {"error": str(e)}


def main():
    """主测试函数"""
    print("=" * 60)
    print("牧场基础信息接入API测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试牧场: {XINZHI_DATA['aquafarmName']}")
    print("=" * 60)

    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    results = {}

    # 测试所有端点
    for env_name, url in API_ENDPOINTS.items():
        print(f"\n\n{'#'*60}")
        print(f"# 测试环境: {env_name}")
        print(f"{'#'*60}")

        # 1. 测试连接
        connected = test_api_connection(url)

        # 2. 如果连接成功，尝试提交数据
        if connected:
            success, response = submit_ranch_info(url, XINZHI_DATA)
            results[env_name] = {
                "url": url,
                "connected": True,
                "submit_success": success,
                "response": response
            }
        else:
            results[env_name] = {
                "url": url,
                "connected": False,
                "submit_success": False,
                "response": None
            }

    # 打印测试摘要
    print("\n\n")
    print("=" * 60)
    print("测试结果摘要")
    print("=" * 60)

    for env_name, result in results.items():
        status = "[OK]" if result["submit_success"] else "[FAIL]"
        conn_status = "OK" if result["connected"] else "FAIL"
        print(f"{env_name:8} | conn:{conn_status:4} | submit:{status:6} | {result['url']}")
        if result.get("response"):
            resp = result["response"]
            if isinstance(resp, dict):
                print(f"         | code={resp.get('code')} msg={resp.get('msg', resp.get('error', ''))}")

    return results


if __name__ == "__main__":
    main()
