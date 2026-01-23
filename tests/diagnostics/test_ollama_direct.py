import asyncio

import httpx


async def test_ollama_direct():
    url = "http://localhost:11434/api/generate"
    prompt = """你是一個專業的命名實體識別（NER）助手。請仔細閱讀以下文本，識別並提取所有命名實體。

重要規則：
1. **必須識別盡可能多的實體**：不要遺漏任何重要的實體。即使文本簡短，也要盡力識別所有可能的概念、材料、設備、過程、產物、參數、組織、產品、地點、時間等。
2. **至少識別 2-3 個實體**：即使文本很短，也要嘗試識別多個不同的實體，包括主體、客體、屬性、關係、過程、產物等。
3. **僅返回一個 JSON 數組**：不要包含任何解釋、註釋或額外文字。
4. **嚴格遵守 JSON 格式**：確保輸出是有效的 JSON 數組，格式為 [{"text": "...", "label": "...", "start": 0, "end": 0, "confidence": 0.0}]。

待分析的文本內容：
中央廚房採用真空包裝技術生產預製菜產品，保質期可達 30 天。生產線使用自動化設備，每日產能約 5000 份。

請返回 JSON 數組格式的實體列表："""

    payload = {
        "model": "mistral-nemo:12b",
        "prompt": prompt,
        "format": "json",
        "stream": False,
        "options": {"temperature": 0.0},
    }

    async with httpx.AsyncClient(timeout=200.0) as client:
        response = await client.post(url, json=payload)
        result = response.json()
        print(f"Raw Response: {result.get('response')}")


if __name__ == "__main__":
    asyncio.run(test_ollama_direct())
