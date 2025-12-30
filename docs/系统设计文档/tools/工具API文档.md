# 工具 API 文档

**創建日期**: 2025-12-30
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-30

**關聯文檔**: [工具組開發規格](./工具組開發規格.md)、[工具使用指南](./工具使用指南.md)、[工具註冊清單說明](./工具註冊清單說明.md)

---

## 📋 概述

本文檔提供 AI-Box 工具組所有工具的完整 API 說明，包括輸入參數、輸出結果、使用示例和錯誤處理。

---

## 🕐 時間與日期工具

### DateTimeTool

獲取當前日期時間，支持時區轉換和多種格式輸出。

#### 工具信息

- **名稱**: `datetime`
- **版本**: `1.0.0`
- **描述**: 獲取當前日期時間，支持時區轉換和多種格式輸出

#### 輸入參數 (DateTimeInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `timezone` | `Optional[str]` | 否 | `None` | 時區（如 "Asia/Taipei"），None 表示使用配置中的默認時區 |
| `format` | `Optional[str]` | 否 | `None` | 輸出格式（如 "%Y-%m-%d %H:%M:%S"），None 表示使用配置中的默認格式 |
| `tenant_id` | `Optional[str]` | 否 | `None` | 租戶 ID（用於讀取租戶級配置） |
| `user_id` | `Optional[str]` | 否 | `None` | 用戶 ID（用於讀取用戶級配置） |

#### 輸出結果 (DateTimeOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `datetime` | `str` | 格式化後的日期時間字符串 |
| `timestamp` | `float` | Unix 時間戳 |
| `timezone` | `str` | 時區名稱 |
| `iso_format` | `str` | ISO 8601 格式 |
| `local_format` | `str` | 本地格式 |

#### 使用示例

```python
from tools.time import DateTimeTool, DateTimeInput

tool = DateTimeTool()

# 使用默認配置
result = await tool.execute(DateTimeInput())

# 使用自定義時區
result = await tool.execute(DateTimeInput(timezone="Asia/Taipei"))

# 使用自定義格式
result = await tool.execute(DateTimeInput(format="%Y-%m-%d %H:%M:%S"))

# 使用租戶和用戶配置
result = await tool.execute(DateTimeInput(
    tenant_id="tenant_123",
    user_id="user_456"
))
```

#### 錯誤處理

- `ToolExecutionError`: 工具執行失敗
- `ToolConfigurationError`: 配置讀取失敗

---

### DateFormatter

日期格式化和解析工具。

#### 工具信息

- **名稱**: `date_formatter`
- **版本**: `1.0.0`
- **描述**: 日期格式化和解析工具

#### 輸入參數 (FormatInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `date` | `str` | 是 | 日期字符串或 ISO 8601 格式 |
| `format` | `str` | 是 | 目標格式（如 "%Y年%m月%d日"） |
| `source_format` | `Optional[str]` | 否 | 源格式（如果 date 不是 ISO 8601） |

#### 輸出結果 (FormatOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `formatted` | `str` | 格式化後的日期字符串 |
| `iso_format` | `str` | ISO 8601 格式 |
| `timestamp` | `float` | Unix 時間戳 |

#### 使用示例

```python
from tools.time import DateFormatter, FormatInput

tool = DateFormatter()

# 格式化日期
result = await tool.execute(FormatInput(
    date="2025-12-30",
    format="%Y年%m月%d日"
))
```

---

### DateCalculator

日期計算工具，支持日期差值計算、加減運算和工作日計算。

#### 工具信息

- **名稱**: `date_calculator`
- **版本**: `1.0.0`
- **描述**: 日期計算工具，支持日期差值計算、加減運算和工作日計算

#### 輸入參數 (CalculateInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `operation` | `str` | 是 | 操作類型：`add`, `subtract`, `diff` |
| `date1` | `str` | 是 | 第一個日期（ISO 8601） |
| `date2` | `Optional[str]` | 否 | 第二個日期（用於 diff 操作） |
| `days` | `Optional[int]` | 否 | 天數（用於 add/subtract） |
| `months` | `Optional[int]` | 否 | 月數（用於 add/subtract） |
| `years` | `Optional[int]` | 否 | 年數（用於 add/subtract） |

#### 輸出結果 (CalculateOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `result` | `str` | 計算結果（ISO 8601 格式） |
| `days_diff` | `Optional[int]` | 天數差值（diff 操作） |
| `hours_diff` | `Optional[float]` | 小時差值（diff 操作） |

#### 使用示例

```python
from tools.time import DateCalculator, CalculateInput

tool = DateCalculator()

# 計算日期差值
result = await tool.execute(CalculateInput(
    operation="diff",
    date1="2025-01-01",
    date2="2025-12-30"
))

# 日期加減
result = await tool.execute(CalculateInput(
    operation="add",
    date1="2025-01-01",
    days=30
))
```

---

## 🌤️ 天氣工具

### WeatherTool

根據城市名稱或經緯度獲取當前天氣信息。

#### 工具信息

- **名稱**: `weather`
- **版本**: `1.0.0`
- **描述**: 根據城市名稱或經緯度獲取當前天氣信息

#### 輸入參數 (WeatherInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `city` | `Optional[str]` | 否 | `None` | 城市名稱（如 "Taipei"） |
| `lat` | `Optional[float]` | 否 | `None` | 緯度 |
| `lon` | `Optional[float]` | 否 | `None` | 經度 |
| `units` | `str` | 否 | `"metric"` | 單位：`metric` (攝氏度), `imperial` (華氏度) |
| `provider` | `Optional[str]` | 否 | `None` | 天氣 API 提供商（如 "openweathermap"） |

**注意**: `city` 和 `lat`/`lon` 至少需要提供一個。

#### 輸出結果 (WeatherOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `city` | `str` | 城市名稱 |
| `country` | `str` | 國家代碼 |
| `temperature` | `float` | 溫度 |
| `feels_like` | `float` | 體感溫度 |
| `humidity` | `int` | 濕度（百分比） |
| `pressure` | `int` | 氣壓（hPa） |
| `description` | `str` | 天氣描述 |
| `icon` | `str` | 天氣圖標代碼 |
| `wind_speed` | `float` | 風速 |
| `wind_direction` | `int` | 風向（度數） |
| `visibility` | `Optional[int]` | 能見度（米） |
| `uv_index` | `Optional[float]` | UV 指數 |
| `timestamp` | `float` | 數據時間戳 |

#### 使用示例

```python
from tools.weather import WeatherTool, WeatherInput

tool = WeatherTool()

# 根據城市名稱查詢
result = await tool.execute(WeatherInput(city="Taipei"))

# 根據經緯度查詢
result = await tool.execute(WeatherInput(lat=25.0330, lon=121.5654))

# 使用華氏度
result = await tool.execute(WeatherInput(city="Taipei", units="imperial"))
```

#### 錯誤處理

- `ToolValidationError`: 輸入參數驗證失敗（如未提供 city 或 lat/lon）
- `ToolExecutionError`: API 調用失敗或網絡錯誤

#### 配置要求

需要設置環境變數 `OPENWEATHERMAP_API_KEY`。

---

### ForecastTool

獲取未來幾天的天氣預報。

#### 工具信息

- **名稱**: `forecast`
- **版本**: `1.0.0`
- **描述**: 獲取未來幾天的天氣預報

#### 輸入參數 (ForecastInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `city` | `Optional[str]` | 否 | `None` | 城市名稱 |
| `lat` | `Optional[float]` | 否 | `None` | 緯度 |
| `lon` | `Optional[float]` | 否 | `None` | 經度 |
| `days` | `int` | 否 | `3` | 預報天數（1-7） |
| `hourly` | `bool` | 否 | `False` | 是否獲取小時級別預報 |
| `units` | `str` | 否 | `"metric"` | 單位 |
| `provider` | `Optional[str]` | 否 | `None` | 天氣 API 提供商 |

#### 輸出結果 (ForecastOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `city` | `str` | 城市名稱 |
| `country` | `str` | 國家代碼 |
| `forecasts` | `List[ForecastItem]` | 預報列表 |

#### 使用示例

```python
from tools.weather import ForecastTool, ForecastInput

tool = ForecastTool()

# 獲取 5 天預報
result = await tool.execute(ForecastInput(city="Taipei", days=5))

# 獲取小時級別預報
result = await tool.execute(ForecastInput(
    city="Taipei",
    days=3,
    hourly=True
))
```

---

## 📍 地理位置工具

### IPLocationTool

根據 IP 地址獲取地理位置信息。

#### 工具信息

- **名稱**: `ip_location`
- **版本**: `1.0.0`
- **描述**: 根據 IP 地址獲取地理位置信息

#### 輸入參數 (IPLocationInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `ip` | `str` | 是 | IP 地址（IPv4 或 IPv6） |
| `provider` | `Optional[str]` | 否 | IP 定位服務提供商 |

#### 輸出結果 (IPLocationOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `ip` | `str` | IP 地址 |
| `country` | `str` | 國家名稱 |
| `country_code` | `str` | 國家代碼（ISO 3166-1 alpha-2） |
| `region` | `Optional[str]` | 地區/州 |
| `city` | `Optional[str]` | 城市 |
| `latitude` | `Optional[float]` | 緯度 |
| `longitude` | `Optional[float]` | 經度 |
| `timezone` | `Optional[str]` | 時區 |
| `isp` | `Optional[str]` | ISP 提供商 |
| `org` | `Optional[str]` | 組織 |

#### 使用示例

```python
from tools.location import IPLocationTool, IPLocationInput

tool = IPLocationTool()

result = await tool.execute(IPLocationInput(ip="8.8.8.8"))
```

---

### GeocodingTool

地理編碼工具，支持正向（地址 → 坐標）和反向（坐標 → 地址）編碼。

#### 工具信息

- **名稱**: `geocoding`
- **版本**: `1.0.0`
- **描述**: 地理編碼工具，支持正向和反向編碼

#### 輸入參數 (GeocodingInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `address` | `Optional[str]` | 否 | `None` | 地址（正向編碼） |
| `lat` | `Optional[float]` | 否 | `None` | 緯度（反向編碼） |
| `lon` | `Optional[float]` | 否 | `None` | 經度（反向編碼） |
| `language` | `str` | 否 | `"zh-TW"` | 結果語言 |
| `provider` | `Optional[str]` | 否 | `None` | 地理編碼服務提供商 |

**注意**: 正向編碼需要提供 `address`，反向編碼需要提供 `lat` 和 `lon`。

#### 輸出結果 (GeocodingOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `address` | `str` | 完整地址 |
| `formatted_address` | `str` | 格式化地址 |
| `latitude` | `float` | 緯度 |
| `longitude` | `float` | 經度 |
| `country` | `str` | 國家 |
| `country_code` | `str` | 國家代碼 |
| `region` | `Optional[str]` | 地區 |
| `city` | `Optional[str]` | 城市 |
| `district` | `Optional[str]` | 區/縣 |
| `street` | `Optional[str]` | 街道 |
| `postal_code` | `Optional[str]` | 郵政編碼 |
| `place_id` | `Optional[str]` | 地點 ID |

#### 使用示例

```python
from tools.location import GeocodingTool, GeocodingInput

tool = GeocodingTool()

# 正向編碼（地址 → 坐標）
result = await tool.execute(GeocodingInput(address="Taipei, Taiwan"))

# 反向編碼（坐標 → 地址）
result = await tool.execute(GeocodingInput(lat=25.0330, lon=121.5654))
```

---

### DistanceTool

計算兩個地理位置之間的距離。

#### 工具信息

- **名稱**: `distance`
- **版本**: `1.0.0`
- **描述**: 計算兩個地理位置之間的距離

#### 輸入參數 (DistanceInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `lat1` | `float` | 是 | - | 起點緯度 |
| `lon1` | `float` | 是 | - | 起點經度 |
| `lat2` | `float` | 是 | - | 終點緯度 |
| `lon2` | `float` | 是 | - | 終點經度 |
| `method` | `str` | 否 | `"haversine"` | 計算方法：`haversine`, `driving`, `walking` |
| `unit` | `str` | 否 | `"km"` | 單位：`km`, `mile`, `meter` |
| `provider` | `Optional[str]` | 否 | `None` | 地圖服務提供商（用於 driving/walking） |

#### 輸出結果 (DistanceOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `distance` | `float` | 距離（指定單位） |
| `distance_km` | `float` | 距離（公里） |
| `distance_mile` | `float` | 距離（英里） |
| `method` | `str` | 使用的計算方法 |
| `duration` | `Optional[float]` | 預計時間（秒，僅 driving/walking） |
| `route` | `Optional[Dict[str, Any]]` | 路線信息（僅 driving/walking） |

#### 使用示例

```python
from tools.location import DistanceTool, DistanceInput

tool = DistanceTool()

# 計算直線距離
result = await tool.execute(DistanceInput(
    lat1=25.0330, lon1=121.5654,  # 台北
    lat2=24.1477, lon2=120.6736,  # 台中
    method="haversine",
    unit="km"
))
```

---

### TimezoneTool

根據地理位置獲取時區信息。

#### 工具信息

- **名稱**: `timezone`
- **版本**: `1.0.0`
- **描述**: 根據地理位置獲取時區信息

#### 輸入參數 (TimezoneInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `lat` | `float` | 是 | 緯度 |
| `lon` | `float` | 是 | 經度 |
| `timestamp` | `Optional[float]` | 否 | 時間戳（用於歷史時區查詢） |

#### 輸出結果 (TimezoneOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `timezone` | `str` | 時區名稱（如 "Asia/Taipei"） |
| `offset` | `int` | UTC 偏移量（秒） |
| `offset_hours` | `float` | UTC 偏移量（小時） |
| `dst` | `bool` | 是否使用夏令時 |
| `abbreviation` | `str` | 時區縮寫（如 "CST"） |

#### 使用示例

```python
from tools.location import TimezoneTool, TimezoneInput

tool = TimezoneTool()

result = await tool.execute(TimezoneInput(lat=25.0330, lon=121.5654))
```

---

## 🔄 單位轉換工具

### LengthConverter

長度單位轉換工具。

#### 工具信息

- **名稱**: `length_converter`
- **版本**: `1.0.0`
- **描述**: 長度單位轉換工具

#### 輸入參數 (LengthInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `value` | `float` | 是 | 數值 |
| `from_unit` | `str` | 是 | 源單位（如 "meter", "foot", "mile"） |
| `to_unit` | `str` | 是 | 目標單位 |

#### 輸出結果 (LengthOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `value` | `float` | 轉換後的數值 |
| `from_unit` | `str` | 源單位 |
| `to_unit` | `str` | 目標單位 |
| `original_value` | `float` | 原始數值 |

#### 支持的單位

- 公制：`meter`, `kilometer`, `centimeter`, `millimeter`
- 英制：`foot`, `inch`, `mile`, `yard`

#### 使用示例

```python
from tools.conversion import LengthConverter, LengthInput

tool = LengthConverter()

result = await tool.execute(LengthInput(
    value=1000.0,
    from_unit="meter",
    to_unit="kilometer"
))
```

---

### WeightConverter

重量單位轉換工具。

#### 工具信息

- **名稱**: `weight_converter`
- **版本**: `1.0.0`
- **描述**: 重量單位轉換工具

#### 支持的單位

- 公制：`kilogram`, `gram`, `milligram`, `metric_ton`
- 英制：`pound`, `ounce`, `stone`, `ton`
- 其他：`carat`

#### 使用示例

```python
from tools.conversion import WeightConverter, WeightInput

tool = WeightConverter()

result = await tool.execute(WeightInput(
    value=1.0,
    from_unit="kilogram",
    to_unit="pound"
))
```

---

### TemperatureConverter

溫度單位轉換工具。

#### 工具信息

- **名稱**: `temperature_converter`
- **版本**: `1.0.0`
- **描述**: 溫度單位轉換工具

#### 支持的單位

- `celsius` (攝氏度)
- `fahrenheit` (華氏度)
- `kelvin` (開爾文)

#### 使用示例

```python
from tools.conversion import TemperatureConverter, TemperatureInput

tool = TemperatureConverter()

result = await tool.execute(TemperatureInput(
    value=25.0,
    from_unit="celsius",
    to_unit="fahrenheit"
))
```

---

### CurrencyConverter

貨幣轉換工具，使用實時匯率 API。

#### 工具信息

- **名稱**: `currency_converter`
- **版本**: `1.0.0`
- **描述**: 貨幣轉換工具，使用實時匯率 API

#### 輸入參數 (CurrencyInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `amount` | `float` | 是 | 金額 |
| `from_currency` | `str` | 是 | 源貨幣代碼（如 "USD", "TWD"） |
| `to_currency` | `str` | 是 | 目標貨幣代碼 |

#### 輸出結果 (CurrencyOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `amount` | `float` | 轉換後的金額 |
| `from_currency` | `str` | 源貨幣代碼 |
| `to_currency` | `str` | 目標貨幣代碼 |
| `original_amount` | `float` | 原始金額 |
| `exchange_rate` | `float` | 匯率 |
| `timestamp` | `Optional[float]` | 匯率時間戳 |

#### 支持的貨幣

USD, EUR, GBP, JPY, CNY, TWD, HKD, KRW, SGD, AUD, CAD, CHF, INR, BRL, MXN, RUB, ZAR, NZD, SEK, NOK, DKK, PLN, THB, MYR, IDR, PHP, VND 等。

#### 使用示例

```python
from tools.conversion import CurrencyConverter, CurrencyInput

tool = CurrencyConverter()

result = await tool.execute(CurrencyInput(
    amount=100.0,
    from_currency="USD",
    to_currency="TWD"
))
```

---

### VolumeConverter

體積單位轉換工具。

#### 工具信息

- **名稱**: `volume_converter`
- **版本**: `1.0.0`
- **描述**: 體積單位轉換工具

#### 支持的單位

- 公制：`liter`, `milliliter`, `cubic_meter`, `cubic_centimeter`
- 英制：`gallon`, `quart`, `pint`, `cup`, `fluid_ounce`, `tablespoon`, `teaspoon`

#### 使用示例

```python
from tools.conversion import VolumeConverter, VolumeInput

tool = VolumeConverter()

result = await tool.execute(VolumeInput(
    value=1.0,
    from_unit="liter",
    to_unit="milliliter"
))
```

---

### AreaConverter

面積單位轉換工具。

#### 工具信息

- **名稱**: `area_converter`
- **版本**: `1.0.0`
- **描述**: 面積單位轉換工具

#### 支持的單位

- 公制：`square_meter`, `square_kilometer`, `hectare`, `are`
- 英制：`square_foot`, `square_inch`, `square_yard`, `square_mile`, `acre`
- 其他：`ping` (坪，台灣常用)

#### 使用示例

```python
from tools.conversion import AreaConverter, AreaInput

tool = AreaConverter()

result = await tool.execute(AreaInput(
    value=1.0,
    from_unit="ping",
    to_unit="square_meter"
))
```

---

## 🧮 計算工具

### MathCalculator

數學計算工具。

#### 工具信息

- **名稱**: `math_calculator`
- **版本**: `1.0.0`
- **描述**: 數學計算工具

#### 輸入參數 (MathInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `expression` | `str` | 是 | 數學表達式（如 "2 + 3 * 4"） |

#### 輸出結果 (MathOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `result` | `float` | 計算結果 |
| `expression` | `str` | 原始表達式 |

#### 使用示例

```python
from tools.calculator import MathCalculator, MathInput

tool = MathCalculator()

result = await tool.execute(MathInput(expression="2 + 3 * 4"))
```

---

### StatisticsCalculator

統計計算工具。

#### 工具信息

- **名稱**: `statistics_calculator`
- **版本**: `1.0.0`
- **描述**: 統計計算工具

#### 輸入參數 (StatisticsInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `operation` | `str` | 是 | 操作類型：`mean`, `median`, `mode`, `std`, `variance` |
| `values` | `List[float]` | 是 | 數值列表 |

#### 輸出結果 (StatisticsOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `result` | `float` | 計算結果 |
| `operation` | `str` | 操作類型 |
| `count` | `int` | 數值數量 |

#### 使用示例

```python
from tools.calculator import StatisticsCalculator, StatisticsInput

tool = StatisticsCalculator()

result = await tool.execute(StatisticsInput(
    operation="mean",
    values=[1.0, 2.0, 3.0, 4.0, 5.0]
))
```

---

## 📝 文本處理工具

### TextFormatter

文本格式化工具。

#### 工具信息

- **名稱**: `text_formatter`
- **版本**: `1.0.0`
- **描述**: 文本格式化工具

#### 輸入參數 (TextFormatterInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `text` | `str` | 是 | 輸入文本 |
| `operation` | `str` | 是 | 操作類型：`upper`, `lower`, `title`, `capitalize` |

#### 輸出結果 (TextFormatterOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `formatted_text` | `str` | 格式化後的文本 |
| `original_text` | `str` | 原始文本 |
| `operation` | `str` | 操作類型 |

#### 使用示例

```python
from tools.text import TextFormatter, TextFormatterInput

tool = TextFormatter()

result = await tool.execute(TextFormatterInput(
    text="hello world",
    operation="title"
))
```

---

### TextCleaner

文本清理工具。

#### 工具信息

- **名稱**: `text_cleaner`
- **版本**: `1.0.0`
- **描述**: 文本清理工具

#### 輸入參數 (TextCleanerInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `text` | `str` | 是 | 輸入文本 |
| `operation` | `str` | 是 | 操作類型：`strip`, `remove_whitespace`, `remove_special_chars` |

#### 使用示例

```python
from tools.text import TextCleaner, TextCleanerInput

tool = TextCleaner()

result = await tool.execute(TextCleanerInput(
    text="  hello world  ",
    operation="strip"
))
```

---

### TextConverter

文本格式轉換工具，支持 Markdown、HTML、純文本之間的轉換。

#### 工具信息

- **名稱**: `text_converter`
- **版本**: `1.0.0`
- **描述**: 文本格式轉換工具

#### 輸入參數 (TextConverterInput)

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `text` | `str` | 是 | 輸入文本 |
| `from_format` | `str` | 是 | 源格式：`markdown`, `html`, `plain`, `text` |
| `to_format` | `str` | 是 | 目標格式 |

#### 輸出結果 (TextConverterOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `converted_text` | `str` | 轉換後的文本 |
| `original_text` | `str` | 原始文本 |
| `from_format` | `str` | 源格式 |
| `to_format` | `str` | 目標格式 |

#### 使用示例

```python
from tools.text import TextConverter, TextConverterInput

tool = TextConverter()

# Markdown 轉 HTML
result = await tool.execute(TextConverterInput(
    text="# Title\n\nContent",
    from_format="markdown",
    to_format="html"
))

# HTML 轉純文本
result = await tool.execute(TextConverterInput(
    text="<h1>Title</h1><p>Content</p>",
    from_format="html",
    to_format="plain"
))
```

---

### TextSummarizer

文本摘要工具，支持提取關鍵詞、生成摘要和統計信息。

#### 工具信息

- **名稱**: `text_summarizer`
- **版本**: `1.0.0`
- **描述**: 文本摘要工具

#### 輸入參數 (TextSummarizerInput)

| 參數 | 類型 | 必填 | 默認值 | 說明 |
|------|------|------|--------|------|
| `text` | `str` | 是 | - | 輸入文本 |
| `operation` | `str` | 是 | - | 操作類型：`keywords`, `summary`, `stats` |
| `max_keywords` | `Optional[int]` | 否 | `10` | 最大關鍵詞數量（用於 keywords 操作） |
| `summary_length` | `Optional[int]` | 否 | `3` | 摘要句子數量（用於 summary 操作） |

#### 輸出結果 (TextSummarizerOutput)

| 字段 | 類型 | 說明 |
|------|------|------|
| `result` | `str` | 結果文本 |
| `operation` | `str` | 操作類型 |
| `keywords` | `Optional[List[str]]` | 關鍵詞列表（用於 keywords 操作） |
| `stats` | `Optional[dict]` | 統計信息（用於 stats 操作） |

#### 使用示例

```python
from tools.text import TextSummarizer, TextSummarizerInput

tool = TextSummarizer()

# 提取關鍵詞
result = await tool.execute(TextSummarizerInput(
    text="Python is a programming language...",
    operation="keywords",
    max_keywords=5
))

# 生成摘要
result = await tool.execute(TextSummarizerInput(
    text="Long text content...",
    operation="summary",
    summary_length=3
))

# 計算統計信息
result = await tool.execute(TextSummarizerInput(
    text="Sample text",
    operation="stats"
))
```

---

## 🔧 工具註冊表 API

### ToolRegistry

工具註冊表用於管理所有工具的註冊、查詢和註銷。

#### 方法

##### register(tool: BaseTool) -> None

註冊工具到註冊表。

**參數**:

- `tool`: 工具實例

**異常**:

- `ValueError`: 如果工具名稱已存在

##### get_tool(name: str) -> Optional[BaseTool]

獲取工具實例。

**參數**:

- `name`: 工具名稱

**返回**: 工具實例，如果不存在返回 `None`

##### get_tool_or_raise(name: str) -> BaseTool

獲取工具實例（如果不存在則拋出異常）。

**參數**:

- `name`: 工具名稱

**返回**: 工具實例

**異常**:

- `ToolNotFoundError`: 如果工具不存在

##### list_tools() -> List[str]

列出所有工具名稱。

**返回**: 工具名稱列表

##### list_tools_with_info() -> List[Dict[str, str]]

列出所有工具的詳細信息。

**返回**: 工具信息列表，每個元素包含 `name`, `description`, `version`

##### unregister(name: str) -> bool

取消註冊工具。

**參數**:

- `name`: 工具名稱

**返回**: 是否成功取消註冊

##### clear() -> None

清空所有工具註冊。

#### 使用示例

```python
from tools import register_all_tools, get_tool_registry
from tools.time import DateTimeTool

# 獲取註冊表
registry = get_tool_registry()

# 註冊所有工具
register_all_tools(registry)

# 獲取工具
tool = registry.get_tool("datetime")

# 列出所有工具
tools = registry.list_tools()
```

---

## ⚙️ 配置管理

### 日期時間工具配置

日期時間工具的配置存儲在 ArangoDB 中，支持三層配置架構：

1. **系統級配置** (`system_configs`): 默認配置，所有用戶共享
2. **租戶級配置** (`tenant_configs`): 租戶特定配置，可覆蓋系統級
3. **用戶級配置** (`user_configs`): 用戶個性化配置，優先級最高

#### 配置 Scope

`tools.datetime`

#### 配置數據結構

```json
{
  "default_format": "%Y-%m-%d %H:%M:%S",
  "default_timezone": "UTC",
  "default_locale": "en_US",
  "iso_format": "%Y-%m-%dT%H:%M:%S%z",
  "date_only_format": "%Y-%m-%d",
  "time_only_format": "%H:%M:%S",
  "localized_formats": {
    "zh_TW": "%Y年%m月%d日 %H:%M:%S",
    "en_US": "%B %d, %Y %I:%M:%S %p"
  }
}
```

#### 配置優先級

User > Tenant > System

---

## 🚨 錯誤處理

### 錯誤類型

#### ToolError

工具錯誤基類。

#### ToolExecutionError

工具執行錯誤。

**屬性**:

- `message`: 錯誤消息
- `tool_name`: 工具名稱（可選）

#### ToolValidationError

工具驗證錯誤（輸入參數驗證失敗）。

**屬性**:

- `message`: 錯誤消息
- `field`: 驗證失敗的字段（可選）

#### ToolNotFoundError

工具未找到錯誤。

**屬性**:

- `tool_name`: 工具名稱

#### ToolConfigurationError

工具配置錯誤。

**屬性**:

- `message`: 錯誤消息
- `tool_name`: 工具名稱（可選）

---

## 📚 相關文檔

- [工具組開發規格](./工具組開發規格.md) - 技術規格和實現細節
- [工具使用指南](./工具使用指南.md) - 使用指南和最佳實踐
- [工具組需求分析](./工具組需求分析.md) - 功能需求說明
- [工具註冊清單說明](./工具註冊清單說明.md) - 工具註冊清單的存儲和管理

---

---

## 🔧 工具註冊清單 API

工具註冊清單提供了完整的 API 接口，用於管理工具的註冊信息。詳細說明請參閱 [工具註冊清單說明](./工具註冊清單說明.md)。

### API 端點

| 方法 | 端點 | 說明 |
|------|------|------|
| `POST` | `/api/v1/tools/registry` | 註冊新工具 |
| `GET` | `/api/v1/tools/registry/{tool_name}` | 獲取指定工具信息 |
| `PUT` | `/api/v1/tools/registry/{tool_name}` | 更新工具信息 |
| `DELETE` | `/api/v1/tools/registry/{tool_name}` | 刪除工具（軟刪除） |
| `GET` | `/api/v1/tools/registry` | 列出所有工具（支持分類、分頁） |
| `GET` | `/api/v1/tools/registry/search` | 搜索工具（關鍵字搜索） |
| `GET` | `/api/v1/tools/registry/categories/list` | 獲取所有類別 |

### 使用示例

```bash
# 查詢所有工具
curl http://localhost:8000/api/v1/tools/registry

# 獲取指定工具信息
curl http://localhost:8000/api/v1/tools/registry/datetime

# 註冊新工具
curl -X POST http://localhost:8000/api/v1/tools/registry \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new_tool",
    "version": "1.0.0",
    "category": "測試",
    "description": "新工具描述",
    "purpose": "工具用途說明",
    "use_cases": ["場景1"],
    "input_parameters": {},
    "output_fields": {},
    "example_scenarios": []
  }'
```

---

**最後更新日期**: 2025-12-30
**維護人**: Daniel Chung
