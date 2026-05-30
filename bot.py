import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler

import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_API = os.getenv("OPENWEATHER_API_KEY")

CHANNEL_ID = 1510252662455668818

PORT = int(os.getenv("PORT", 10000))

# =========================
# Render 防睡著
# =========================

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"WeatherBot Running")

def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

# =========================
# Discord
# =========================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

weather_message = None

# =========================
# 城市列表
# =========================

cities = [
    ("🇹🇼 台北", "Taipei"),
    ("🇹🇼 高雄", "Kaohsiung"),
    ("🇨🇳 南京", "Nanjing"),
    ("🇯🇵 東京", "Tokyo"),
    ("🇯🇵 北海道", "Sapporo"),
    ("🇨🇦 溫哥華", "Vancouver"),
    ("🇩🇪 慕尼黑", "Munich"),
    ("🇩🇰 哥本哈根", "Copenhagen"),
    ("🇸🇪 Malmö", "Malmo")
]

# =========================
# AQI 等級
# =========================

def aqi_text(aqi):

    levels = {
        1: "優",
        2: "良",
        3: "普通",
        4: "差",
        5: "極差"
    }

    return levels.get(aqi, "未知")

# =========================
# 取得天氣
# =========================

def get_weather(city):

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        f"&appid={WEATHER_API}"
        f"&units=metric"
        f"&lang=zh_tw"
    )

    data = requests.get(url).json()

    lat = data["coord"]["lat"]
    lon = data["coord"]["lon"]

    temp = round(data["main"]["temp"])

    weather = data["weather"][0]["description"]

    rain = 0

    if "rain" in data:
        rain = int(data["rain"].get("1h", 0))

    aqi_url = (
        f"https://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}"
        f"&lon={lon}"
        f"&appid={WEATHER_API}"
    )

    aqi_data = requests.get(aqi_url).json()

    aqi = aqi_data["list"][0]["main"]["aqi"]

    return temp, weather, rain, aqi

# =========================
# 建立訊息
# =========================

def make_weather_text():

    text = "🌦️ **世界天氣預報**\n\n"

    for display_name, city in cities:

        try:

            temp, weather, rain, aqi = get_weather(city)

            text += (
                f"{display_name}\n"
                f"🌡️ {temp}°C\n"
                f"☁️ {weather}\n"
                f"☔ {rain}%\n"
                f"🌫️ AQI：{aqi_text(aqi)}\n\n"
            )

        except Exception:

            text += (
                f"{display_name}\n"
                f"❌ 資料取得失敗\n\n"
            )

    text += "🔄 每分鐘自動更新"

    return text

# =========================
# Bot 上線
# =========================

@bot.event
async def on_ready():

    print(f"已登入：{bot.user}")

    if not update_weather.is_running():
        update_weather.start()

# =========================
# 更新天氣
# =========================

@tasks.loop(minutes=1)
async def update_weather():

    global weather_message

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print("找不到頻道")
        return

    try:

        if weather_message is None:

            weather_message = await channel.send(
                make_weather_text()
            )

            print("天氣訊息建立")

        else:

            await weather_message.edit(
                content=make_weather_text()
            )

            print("天氣已更新")

    except Exception as e:

        print(e)

# =========================
# 啟動
# =========================

if TOKEN is None:
    raise ValueError("找不到 DISCORD_TOKEN")

if WEATHER_API is None:
    raise ValueError("找不到 OPENWEATHER_API_KEY")

threading.Thread(
    target=run_web_server,
    daemon=True
).start()

bot.run(TOKEN)
