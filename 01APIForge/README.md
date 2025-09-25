# 01APIForge - API缁熶竴绠＄悊宸ュ巶

## 姒傝堪

APIForge鏄疦euroTrade Nexus (NTN)绯荤粺鐨勬牳蹇冩ā鍧楋紝璐熻矗缁熶竴绠＄悊鍜屽崗璋冩墍鏈堿PI鎺ュ彛锛屾彁渚涘畨鍏ㄣ€侀珮鏁堢殑API缃戝叧鏈嶅姟銆?

## 鏍稿績鍔熻兘

### 1. API缃戝叧鏈嶅姟
- 缁熶竴API鍏ュ彛鐐?
- 璇锋眰璺敱鍜岃礋杞藉潎琛?
- API鐗堟湰绠＄悊
- 璇锋眰/鍝嶅簲杞崲

### 2. 璁よ瘉涓庢巿鏉?
- JWT浠ょ墝绠＄悊
- 鐢ㄦ埛韬唤楠岃瘉
- 鏉冮檺鎺у埗
- API瀵嗛挜绠＄悊

### 3. 闄愭祦涓庣啍鏂?
- 璇锋眰棰戠巼闄愬埗
- 鐔旀柇鍣ㄦā寮?
- 闄嶇骇绛栫暐
- 娴侀噺鎺у埗

### 4. 鐩戞帶涓庢棩蹇?
- API璋冪敤缁熻
- 鎬ц兘鐩戞帶
- 閿欒杩借釜
- 瀹¤鏃ュ織

## 鎶€鏈灦鏋?

### 鎶€鏈爤
- **妗嗘灦**: FastAPI 0.104.1
- **寮傛杩愯鏃?*: Uvicorn
- **鏁版嵁搴?*: SQLite (SQLAlchemy ORM)
- **缂撳瓨**: Redis
- **娑堟伅闃熷垪**: ZeroMQ
- **璁よ瘉**: JWT + Passlib

### 鐩綍缁撴瀯
```
api_factory/
鈹溾攢鈹€ __init__.py
鈹溾攢鈹€ main.py              # 搴旂敤鍏ュ彛
鈹溾攢鈹€ config/              # 閰嶇疆绠＄悊
鈹溾攢鈹€ core/                # 鏍稿績涓氬姟閫昏緫
鈹溾攢鈹€ routers/             # API璺敱
鈹斺攢鈹€ security/            # 瀹夊叏妯″潡
```

## 蹇€熷紑濮?

### 鐜瑕佹眰
- Python 3.11+
- Redis 7.0+
- Docker (鍙€?

### 鏈湴寮€鍙?

1. **瀹夎渚濊禆**
```bash
pip install -r requirements.txt
```

2. **閰嶇疆鐜鍙橀噺**
```bash
cp .env.example .env
# 缂栬緫 .env 鏂囦欢璁剧疆蹇呰鐨勯厤缃?
```

3. **鍚姩鏈嶅姟**
```bash
python -m api_factory.main
```

### Docker閮ㄧ讲

1. **鏋勫缓闀滃儚**
```bash
docker build -t ntn-api-forge .
```

2. **杩愯瀹瑰櫒**
```bash
docker run -p 8000:8000 -p 5555:5555 -p 5556:5556 ntn-api-forge
```

## API鏂囨。

鍚姩鏈嶅姟鍚庯紝璁块棶浠ヤ笅鍦板潃鏌ョ湅API鏂囨。锛?
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 鏍稿績绔偣

### 鍋ュ悍妫€鏌?
```
GET /health
```

### 璁よ瘉
```
POST /auth/login
POST /auth/refresh
POST /auth/logout
```

### API绠＄悊
```
GET /api/routes
POST /api/register
DELETE /api/unregister
```

## 閰嶇疆璇存槑

### 鐜鍙橀噺

| 鍙橀噺鍚?| 鎻忚堪 | 榛樿鍊?|
|--------|------|--------|
| `APP_ENV` | 杩愯鐜 | `development` |
| `REDIS_HOST` | Redis涓绘満 | `localhost` |
| `REDIS_PASSWORD` | Redis瀵嗙爜 | - |
| `ZMQ_PUBLISHER_PORT` | ZMQ鍙戝竷绔彛 | `5555` |
| `ZMQ_SUBSCRIBER_PORT` | ZMQ璁㈤槄绔彛 | `5556` |
| `JWT_SECRET_KEY` | JWT瀵嗛挜 | 鑷姩鐢熸垚 |
| `JWT_ALGORITHM` | JWT绠楁硶 | `HS256` |
| `JWT_EXPIRE_MINUTES` | JWT杩囨湡鏃堕棿 | `30` |

## 寮€鍙戞寚鍗?

### 浠ｇ爜瑙勮寖
- 閬靛惊PEP 8浠ｇ爜椋庢牸
- 浣跨敤Black杩涜浠ｇ爜鏍煎紡鍖?
- 浣跨敤isort杩涜瀵煎叆鎺掑簭
- 浣跨敤MyPy杩涜绫诲瀷妫€鏌?

### 娴嬭瘯
```bash
# 杩愯鎵€鏈夋祴璇?
pytest

# 杩愯娴嬭瘯骞剁敓鎴愯鐩栫巼鎶ュ憡
pytest --cov=api_factory

# 杩愯鐗瑰畾娴嬭瘯
pytest tests/test_auth_center.py
```

### 浠ｇ爜璐ㄩ噺妫€鏌?
```bash
# 浠ｇ爜鏍煎紡鍖?
black api_factory/

# 瀵煎叆鎺掑簭
isort api_factory/

# 浠ｇ爜妫€鏌?
flake8 api_factory/

# 绫诲瀷妫€鏌?
mypy api_factory/
```

## 鐩戞帶涓庤繍缁?

### 鍋ュ悍妫€鏌?
鏈嶅姟鎻愪緵澶氬眰娆＄殑鍋ュ悍妫€鏌ワ細
- HTTP鍋ュ悍妫€鏌ョ鐐?
- Redis杩炴帴妫€鏌?
- 鏁版嵁搴撹繛鎺ユ鏌?
- ZMQ杩炴帴妫€鏌?

### 鏃ュ織绠＄悊
- 浣跨敤Loguru杩涜缁撴瀯鍖栨棩蹇?
- 鏀寔澶氱鏃ュ織绾у埆
- 鑷姩鏃ュ織杞浆
- 闆嗕腑鍖栨棩蹇楁敹闆?

### 鎬ц兘鐩戞帶
- Prometheus鎸囨爣瀵煎嚭
- API鍝嶅簲鏃堕棿鐩戞帶
- 閿欒鐜囩粺璁?
- 璧勬簮浣跨敤鐩戞帶

## 鏁呴殰鎺掗櫎

### 甯歌闂

1. **Redis杩炴帴澶辫触**
   - 妫€鏌edis鏈嶅姟鐘舵€?
   - 楠岃瘉杩炴帴閰嶇疆
   - 妫€鏌ョ綉缁滆繛閫氭€?

2. **ZMQ绔彛鍐茬獊**
   - 妫€鏌ョ鍙ｅ崰鐢ㄦ儏鍐?
   - 淇敼閰嶇疆鏂囦欢涓殑绔彛璁剧疆
   - 閲嶅惎鐩稿叧鏈嶅姟

3. **鏁版嵁搴撻攣瀹?*
   - 妫€鏌QLite鏂囦欢鏉冮檺
   - 纭繚娌℃湁鍏朵粬杩涚▼鍗犵敤鏁版嵁搴?
   - 閲嶅惎鏈嶅姟

### 鏃ュ織鍒嗘瀽
```bash
# 鏌ョ湅鏈€鏂版棩蹇?
tail -f logs/api_factory.log

# 鎼滅储閿欒鏃ュ織
grep "ERROR" logs/api_factory.log

# 鍒嗘瀽API璋冪敤缁熻
grep "API_CALL" logs/api_factory.log | awk '{print $5}' | sort | uniq -c
```

## 璐＄尞鎸囧崡

1. Fork椤圭洰
2. 鍒涘缓鍔熻兘鍒嗘敮
3. 鎻愪氦鏇存敼
4. 鎺ㄩ€佸埌鍒嗘敮
5. 鍒涘缓Pull Request

## 璁稿彲璇?

鏈」鐩噰鐢∕IT璁稿彲璇?- 璇﹁ [LICENSE](../LICENSE) 鏂囦欢銆?

## 鑱旂郴鏂瑰紡

- 椤圭洰缁存姢鑰? NTN寮€鍙戝洟闃?
- 閭: dev@neurotrade-nexus.com
- 鏂囨。: https://docs.neurotrade-nexus.com