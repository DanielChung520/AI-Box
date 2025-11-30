# 代碼功能說明: Ollama 連線診斷腳本
# 創建日期: 2025-11-26 01:15 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:15 (UTC+8)

"""診斷腳本，檢查 Ollama 服務連線狀態。"""

import argparse
import sys
import time

import httpx
import socket
from urllib.parse import urlparse


def check_dns(hostname: str) -> tuple[bool, str]:
    """檢查 DNS 解析。"""
    try:
        ip = socket.gethostbyname(hostname)
        return True, f"✓ DNS 解析成功: {hostname} -> {ip}"
    except socket.gaierror as e:
        return False, f"✗ DNS 解析失敗: {e}"


def check_port(hostname: str, port: int, timeout: int = 5) -> tuple[bool, str]:
    """檢查端口是否開放。"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((hostname, port))
        sock.close()
        if result == 0:
            return True, f"✓ 端口 {port} 可連線"
        else:
            return False, f"✗ 端口 {port} 無法連線 (錯誤碼: {result})"
    except socket.timeout:
        return False, f"✗ 端口 {port} 連線超時"
    except Exception as e:
        return False, f"✗ 端口 {port} 檢查失敗: {e}"


async def check_ollama_api(base_url: str, timeout: float = 10.0) -> tuple[bool, str]:
    """檢查 Ollama API 健康狀態。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 嘗試連接 /api/version
            response = await client.get(f"{base_url}/api/version")
            if response.status_code == 200:
                data = response.json()
                version = data.get("version") or data.get("version_string", "unknown")
                return True, f"✓ Ollama API 正常 (版本: {version})"
            else:
                return False, f"✗ Ollama API 回應異常 (狀態碼: {response.status_code})"
    except httpx.TimeoutException:
        return False, f"✗ Ollama API 連線超時 ({timeout}秒)"
    except httpx.ConnectError as e:
        return False, f"✗ Ollama API 連線失敗: {e}"
    except Exception as e:
        return False, f"✗ Ollama API 檢查失敗: {e}"


async def list_models(
    base_url: str, timeout: float = 10.0
) -> tuple[bool, list[str], str]:
    """列出可用模型。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                return True, models, f"✓ 找到 {len(models)} 個模型"
            else:
                return False, [], f"✗ 無法取得模型清單 (狀態碼: {response.status_code})"
    except Exception as e:
        return False, [], f"✗ 列出模型失敗: {e}"


async def test_chat(
    base_url: str, model: str, timeout: float = 120.0
) -> tuple[bool, str]:
    """測試對話功能。"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            payload = {
                "model": model,
                "messages": [
                    {"role": "user", "content": "你好，請用一句話回答。"},
                ],
                "stream": False,
            }
            start_time = time.time()
            response = await client.post(f"{base_url}/api/chat", json=payload)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return (
                    True,
                    f"✓ 對話測試成功 (耗時: {elapsed:.2f}秒)\n  回應: {content[:100]}",
                )
            else:
                return False, f"✗ 對話測試失敗 (狀態碼: {response.status_code})"
    except httpx.TimeoutException:
        return False, f"✗ 對話測試超時 ({timeout}秒)"
    except Exception as e:
        return False, f"✗ 對話測試失敗: {e}"


async def main():
    parser = argparse.ArgumentParser(description="診斷 Ollama 服務連線")
    parser.add_argument(
        "--url",
        default="http://olm.k84.org",
        help="Ollama 完整 URL（注意：olm.k84.org 已透過 tunnel 指向 11434，不需要指定端口）",
    )
    parser.add_argument("--test-chat", action="store_true", help="執行對話測試")
    parser.add_argument("--model", default="gpt-oss:20b", help="用於對話測試的模型")
    parser.add_argument("--timeout", type=float, default=10.0, help="API 請求超時時間")

    args = parser.parse_args()

    base_url = args.url
    parsed = urlparse(base_url)
    host = parsed.hostname or "olm.k84.org"
    port = parsed.port or 80 if parsed.scheme == "http" else 443

    print("=" * 60)
    print("Ollama 連線診斷")
    print("=" * 60)
    print(f"目標: {base_url}")
    print()

    # 1. DNS 檢查
    print("1. DNS 解析檢查...")
    dns_ok, dns_msg = check_dns(host)
    print(f"   {dns_msg}")
    print()

    if not dns_ok:
        print("⚠ DNS 解析失敗，無法繼續診斷。")
        sys.exit(1)

    # 2. 端口檢查（僅在未使用 tunnel 時檢查）
    if port != 443:  # HTTPS 端口通常無法直接檢查
        print("2. 端口連線檢查...")
        port_ok, port_msg = check_port(host, port, timeout=5)
        print(f"   {port_msg}")
        print()

        if not port_ok:
            print(f"⚠ 端口 {port} 無法連線（可能已透過 tunnel，繼續嘗試 API 連線）")
            print()

    # 3. API 健康檢查
    print("3. Ollama API 健康檢查...")
    api_ok, api_msg = await check_ollama_api(base_url, timeout=args.timeout)
    print(f"   {api_msg}")
    print()

    if not api_ok:
        print("⚠ Ollama API 無法訪問。")
        sys.exit(1)

    # 4. 列出模型
    print("4. 列出可用模型...")
    models_ok, models, models_msg = await list_models(base_url, timeout=args.timeout)
    print(f"   {models_msg}")
    if models:
        print(
            f"   模型列表: {', '.join(models[:5])}"
            + (f" ... (共 {len(models)} 個)" if len(models) > 5 else "")
        )
    print()

    # 5. 對話測試（可選）
    if args.test_chat:
        print("5. 對話功能測試...")
        chat_ok, chat_msg = await test_chat(
            base_url, args.model, timeout=args.timeout * 12
        )
        print(f"   {chat_msg}")
        print()

        if not chat_ok:
            print("⚠ 對話測試失敗。")
            sys.exit(1)

    print("=" * 60)
    print("✓ 所有檢查通過！")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
