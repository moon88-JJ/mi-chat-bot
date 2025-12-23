from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from google import genai
import httpx
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# ✅ 修复中间件 (新版写法)
@app.middleware("http")
async def fix_header_bytes(request: Request, call_next):
    response = await call_next(request)
    if hasattr(response, "headers"):
        headers = {}
        for k, v in response.headers.items():
            if isinstance(k, bytes):
                k = k.decode("utf-8")
            headers[str(k)] = v
        response.raw_headers = [(k.encode("utf-8"), v.encode("utf-8")) for k, v in headers.items()]
    return response


# ✅ 初始化 Gemini 客户端
client = OpenAI(
    api_key=os.getenv("API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

@app.get("/")
async def root():
    return JSONResponse({"message": "🤖 Telegram + Gemini Bot is running!"})

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    try:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"].get("text", "")

        # ✅ Gemini 生成回复
        completion = client.chat.completions.create(
            model="mimo-v2-flash",
            messages=[
                {"role": "system", "content": "你是一个友好、有逻辑的AI助手。"},
                {"role": "user", "content": user_text}
            ],
            temperature=0.6,
        )
        reply = completion.choices[0].message.content.strip()

        # ✅ 回复 Telegram
        async with httpx.AsyncClient() as http_client:
            await http_client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": reply}
            )

        return JSONResponse({"ok": True})
    except Exception as e:
        print("❌ Error:", e)
        return JSONResponse({"error": str(e)}, status_code=500)
