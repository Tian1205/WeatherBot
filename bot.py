import os
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

TOKEN = os.getenv("DISCORD_TOKEN")
WEATHER_API = os.getenv("OPENWEATHER_API_KEY")

CHANNEL_ID = 1510252662455668818
PORT = int(os.getenv("PORT", 10000))

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"WeatherBot Running")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_web_server():
    server = HTTPServer(("0.0.0.0", PORT), HealthCheckHandler)
    server.serve_forever()

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

weather_message = None

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

def aqi_text(aqi):
    levels = {
        1: "🟢 優",
        2: "🟡 良",
        3: "🟠 普通",
        4: "🔴 差",
        5: "🟣 極差"
    }
    return levels.get(aqi, "未知")

def get_weather(city):
    current_url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}"
        f"&appid={WEATHER_API}"
        f"&units=metric"
        f"&lang=zh_tw"
    )

    current_data = requests.get(current_url, timeout=10).json()

    if current_data.get("cod") != 200:
        raise Exception(current_data)

    lat = current_data["coord"]["lat"]
    lon = current_data["coord"]["lon"]

    temp = round(current_data["main"]["temp"])
    feels_like = round(current_data["main"]["feels_like"])
    weather = current_data["weather"][0]["description"]

    forecast_url = (
        f"https://api.openweathermap.org/data/2.5/forecast"
        f"?q={city}"
        f"&appid={WEATHER_API}"
        f"&units=metric"
        f"&lang=zh_tw"
    )

    forecast_data = requests.get(forecast_url, timeout=10).json()

    rain_chance = 0

    if forecast_data.get("cod") == "200":
        rain_chance = int(forecast_data["list"][0].get("pop", 0) * 100)

    aqi_url = (
        f"https://api.openweathermap.org/data/2.5/air_pollution"
        f"?lat={lat}"
        f"&lon={lon}"
        f"&appid={WEATHER_API}"
    )

    aqi_data = requests.get(aqi_url, timeout=10).json()
    aqi = aqi_data["list"][0]["main"]["aqi"]

    return temp, feels_like, weather, rain_chance, aqi

def make_weather_text():
    now = datetime.now(ZoneInfo("Asia/Taipei"))

    text = "🌦️ **世界天氣預報**\n\n"

    for display_name, city in cities:
        try:
            temp, feels_like, weather, rain_chance, aqi = get_weather(city)

            text += (
                f"{display_name}\n"
                f"🌡️ 溫度：`{temp}°C`\n"
                f"🤗 體感：`{feels_like}°C`\n"
                f"☁️ 天氣：`{weather}`\n"
                f"☔ 降雨率：`{rain_chance}%`\n"
                f"🌫️ AQI：`{aqi_text(aqi)}`\n\n"
            )

        except Exception as e:
            print(f"{display_name} 天氣取得失敗：{e}", flush=True)

            text += (
                f"{display_name}\n"
                f"❌ 資料取得失敗\n\n"
            )

    text += (
        f"🕒 更新時間：`{now.strftime('%Y/%m/%d %H:%M:%S')}`\n"
        "🔄 每分鐘自動更新"
    )

    return text

@bot.event
async def on_ready():
    print(f"已登入：{bot.user}", flush=True)

    print("Bot 目前看得到的伺服器與頻道：", flush=True)
    for guild in bot.guilds:
        print(f"伺服器：{guild.name}", flush=True)
        for ch in guild.text_channels:
            print(f"頻道：{ch.name} | ID：{ch.id}", flush=True)

    if not update_weather.is_running():
        update_weather.start()

@tasks.loop(minutes=1)
async def update_weather():
    global weather_message

    channel = bot.get_channel(CHANNEL_ID)

    if channel is None:
        print(f"找不到頻道：{CHANNEL_ID}", flush=True)
        return

    try:
        if weather_message is None:
            weather_message = await channel.send(make_weather_text())
            print("天氣訊息建立", flush=True)
        else:
            await weather_message.edit(content=make_weather_text())
            print("天氣已更新", flush=True)

    except Exception as e:
        print(f"更新天氣錯誤：{e}", flush=True)

if TOKEN is None:
    raise ValueError("找不到 DISCORD_TOKEN")

if WEATHER_API is None:
    raise ValueError("找不到 OPENWEATHER_API_KEY")

threading.Thread(target=run_web_server, daemon=True).start()

print("WeatherBot 啟動中...", flush=True)

bot.run(TOKEN)
