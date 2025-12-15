import asyncio
import json
import os
import ssl
import time
import warnings
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import aiohttp
import joblib
import numpy as np
import pandas as pd
import paho.mqtt.client as mqtt
import requests
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sklearn.exceptions import InconsistentVersionWarning
from dotenv import load_dotenv
import uvicorn
import psycopg2
from psycopg2.extras import RealDictCursor
import pytz
from device_timer import DeviceTimer
from contextlib import asynccontextmanager
import random

warnings.filterwarnings("ignore", category=InconsistentVersionWarning)

@asynccontextmanager

# async def lifespan(app: FastAPI):# Hàm lifespan – chạy khi server khởi động & tắt
#     disable_mqtt = os.getenv("DISABLE_MQTT", "false").lower() == "true"

#     try:
#         if not disable_mqtt:
#             print("⏳ Đang kết nối MQTT...")
#             await mqtt_client.connect()
#             mqtt_client._reconnect_task = asyncio.create_task(mqtt_client.keep_alive()) # Chạy nền liên tục:
#             print("✅ MQTT đã được bật và kết nối thành công.")
#         else:
#             print("🚫 MQTT bị tắt (DISABLE_MQTT=true) — bỏ qua kết nối MQTT.")

#         print("✅ Khởi động ứng dụng thành công.")
#         yield  # <- cực kỳ quan trọng, phải có yield

#     finally:
#         if not disable_mqtt:
#             await mqtt_client.disconnect()
#             print("✅ Đã ngắt kết nối MQTT.")
#         print("✅ Ứng dụng đã dừng.")

async def lifespan(app: FastAPI):
    try:
        global mqtt_client
        mqtt_client = MQTTClient()
        await mqtt_client.connect()
        mqtt_client._reconnect_task = asyncio.create_task(mqtt_client.keep_alive())
        print("✅ Khởi động thành công")
        yield
    finally:
        try:
            if mqtt_client:
                await mqtt_client.disconnect()
            print("✅ Đã dừng ứng dụng")
        except Exception as e:
            print(f"❌ Lỗi khi dừng ứng dụng: {str(e)}")


# Cấu hình FastAPI + CORS
app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://localhost:5000",
    "http://127.0.0.1:5501",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "https://a-iot.onrender.com",
    "http://a-iot.onrender.com",
    "wss://a-iot.onrender.com",
    "ws://a-iot.onrender.com"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Load mô hình AI dự đoán cây trồng
MODEL_FILES = {
    'model': 'models/lgbm_crop_model.pkl',
    'scaler': 'models/scaler.pkl',
    'label_encoder': 'models/label_encoder.pkl'
}

def load_ml_models():
    """Load machine learning models and return them"""
    try:
        models = {}
        for name, file in MODEL_FILES.items():
            if not os.path.exists(file):
                print(f"⚠️ File model {file} không tồn tại")
                return None
            models[name] = joblib.load(file)
            print(f"✅ Đã tải {file} thành công")
        return models
    except Exception as e:
        print(f"❌ Lỗi khi tải model: {str(e)}")
        return None

ml_models = load_ml_models()
if ml_models:
    model = ml_models['model']
    scaler = ml_models['scaler']
    label_encoder = ml_models['label_encoder']
else:
    model = None
    scaler = None
    label_encoder = None
    print("⚠️ Không thể tải models, một số chức năng có thể không hoạt động")
# Config MQTT
load_dotenv()

MQTT_BROKER = os.getenv("MQTT_BROKER") #Lấy thông tin MQTT từ .env
MQTT_PORT = int(os.getenv("MQTT_PORT", 8884))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
CONTROL_TOPIC = "iot/device/control/#" #Các topic điều khiển & nhận trạng thái từ thiết bị ESP32
STATUS_TOPIC = "iot/device/status/#"
TEST_TOPIC = "iot/test"

API_KEY = os.getenv("API_KEY")
CITY = os.getenv("CITY")
URL = f'https://api.openweathermap.org/data/2.5/forecast?q={CITY}&appid={API_KEY}&units=metric&lang=en'

CONFIG_FILE = 'config.json'

CROP_TRANSLATIONS = {
    'rice': 'Lúa', 'maize': 'Ngô', 'chickpea': 'Đậu gà', 'kidneybeans': 'Đậu thận',
    'pigeonpeas': 'Đậu săng', 'mothbeans': 'Đậu bướm', 'mungbean': 'Đậu xanh', 'blackgram': 'Đậu đen',
    'lentil': 'Đậu lăng', 'pomegranate': 'Lựu', 'banana': 'Chuối', 'mango': 'Xoài', 'grapes': 'Nho',
    'watermelon': 'Dưa hấu', 'muskmelon': 'Dưa lưới', 'apple': 'Táo', 'orange': 'Cam', 'papaya': 'Đu đủ',
    'coconut': 'Dừa', 'cotton': 'Bông', 'jute': 'Đay', 'coffee': 'Cà phê'
}
#Class MQTTClient – toàn bộ xử lý MQTT
class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client(
            client_id=f"iot_client_{int(time.time())}_{random.randint(1000, 9999)}",
            transport="websockets" #Kết nối MQTT qua WebSocket
        )
        self.client.tls_set(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        self.client.tls_insecure_set(True)
        self.client.on_connect = self.on_connect 
        self.client.on_disconnect = self.on_disconnect # kích hoạt tự động reconnect
        self.client.on_message = self.on_message
        self.is_connected = False
        self.connection_lock = asyncio.Lock()
        self.max_reconnect_attempts = 10 # tối đa 10 lần thử
        self.reconnect_delay = 1 
        self.reconnect_backoff = 2 
        self.device_states = {'light': False, 'roof': False, 'pump': False, 'fan': False}
        self.active_websockets = set()
        self.latest_data = None
        self.last_db_update = None
        self._loop = None
        self._reconnect_task = None
        self._keep_alive_task = None
        self._last_connection_attempt = None
        self._connection_timeout = 30 # Chờ tối đa 30s, Nếu thất bại → raise lỗi
        self._connection_attempts = 0
        self._last_connection_time = None

    def on_connect(self, client, userdata, flags, rc): # Khi kết nối thành công: Gửi thông báo test lên MQTT
        if rc == 0:
            print("✅ Kết nối MQTT thành công")
            if client._ssl:
                print("✅ SSL/TLS đã được kích hoạt")
            else:
                print("⚠️ SSL/TLS chưa được kích hoạt")
            self.is_connected = True
            self._last_connection_attempt = None
            
            topics = [
                ("iot/device/control/#", 1),
                ("iot/device/status/#", 1),
                ("iot/device/status_request/#", 1),
                ("iot/sensor/data", 1),
                ("iot/test", 1)
            ]
            self.client.subscribe(topics)
            
            self.client.publish("iot/test", json.dumps({
                "type": "python_client_connected",
                "timestamp": int(time.time())
            }), qos=1)
           
            self._broadcast_connection_status(True)
        else:
            print(f"❌ Lỗi kết nối MQTT: {rc}")
            self.is_connected = False
            self._broadcast_connection_status(False)
            if self._loop and not self._loop.is_closed():
                self._loop.create_task(self.handle_reconnect())

# Khi mất kết nối MQTT → kích hoạt tự động reconnect
    def on_disconnect(self, client, userdata, rc): 
        print(f"❌ Mất kết nối MQTT: {rc}")
        self.is_connected = False
        self._broadcast_connection_status(False)
        if rc != 0 and self._loop and not self._loop.is_closed():
            self._loop.create_task(self.handle_reconnect())

    def _broadcast_connection_status(self, connected):
        closed_ws = set()
        for ws in self.active_websockets:
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.create_task(ws.send_json({
                        "type": "mqtt_status",
                        "connected": connected,
                        "timestamp": int(time.time())
                    }))
            except Exception:
                closed_ws.add(ws)
        self.active_websockets -= closed_ws

#connect()
#Thực hiện:
#Set username/password
#Kết nối MQTT
#Chờ tối đa 30s
# Nếu thất bại → raise lỗi
    async def connect(self):
        try:
            if self._loop is None:
                self._loop = asyncio.get_event_loop()

            if self._reconnect_task:
                self._reconnect_task.cancel()
                self._reconnect_task = None

            self.client.loop_stop()

            self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()

            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < self._connection_timeout:
                await asyncio.sleep(1)

            if not self.is_connected:
                raise Exception("Không thể kết nối đến MQTT broker trong thời gian quy định")

            self._last_connection_time = time.time()
            self._connection_attempts = 0
            print("✅ Kết nối MQTT thành công")

        except Exception as e:
            print(f"❌ Lỗi kết nối MQTT: {str(e)}")
            self._connection_attempts += 1
            raise

    async def handle_reconnect(self):
        async with self.connection_lock:
            if self.is_connected:
                return

            now = time.time()
            if self._last_connection_attempt and (now - self._last_connection_attempt) < self.reconnect_delay:
                return

            self._last_connection_attempt = now

            for attempt in range(self.max_reconnect_attempts):
                try:
                    await self.connect()
                    if self.is_connected:
                        print("✅ Kết nối lại MQTT thành công")
                        return
                except Exception as e:
                    print(f"❌ Lỗi kết nối lại MQTT (lần {attempt + 1}): {str(e)}")

                delay = self.reconnect_delay * (self.reconnect_backoff ** attempt)
                print(f"⏳ Thử kết nối lại sau {delay} giây...")
                await asyncio.sleep(delay)

            print("❌ Đã thử kết nối lại nhiều lần nhưng không thành công")

    async def keep_alive(self):
        """Keep the MQTT connection alive and handle reconnections"""
        while True:
            try:
                if not self.is_connected:
                    await self.handle_reconnect()
                elif self._last_connection_time and (time.time() - self._last_connection_time) > 300:  # 5 minutes

                    print("⚠️ Không có hoạt động MQTT trong 5 phút, đang kết nối lại...")
                    await self.disconnect()
                    await self.handle_reconnect()
                await asyncio.sleep(30) 
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Lỗi trong keep_alive: {str(e)}")
                await asyncio.sleep(5) 

    def control_device(self, device, status):
        if not self.is_connected:
            print("❌ Không thể điều khiển thiết bị: MQTT chưa kết nối")
            return False

        try:
            topic = f"iot/device/control/{device}"
            payload = json.dumps({
                "status": status,
                "timestamp": int(time.time())
            })
            result = self.client.publish(topic, payload, qos=1)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ Đã gửi lệnh điều khiển {device}: {'ON' if status else 'OFF'}")
                self._last_connection_time = time.time()  
                return True
            else:
                print(f"❌ Lỗi gửi lệnh điều khiển {device}: {result.rc}")
                return False
        except Exception as e:
            print(f"❌ Lỗi điều khiển thiết bị {device}: {str(e)}")
            return False

    def on_message(self, client, userdata, msg): # Nhận dữ liệu từ MQTT và xử lý:
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            print(f"MQTT nhận từ {topic}: {payload}")
            # Nhận lệnh điều khiển
            if topic.startswith("iot/device/control/"):
                device = topic.split("/")[-1]
                if device in self.device_states:
                    status = payload.get("status")
                    if status is not None:
                        print(f"📥 Nhận từ {topic}: {payload}")
                        self.device_states[device] = status
                       
                        closed_ws = set()
                        for ws in self.active_websockets:
                            try:
                                if ws.application_state.name == "CONNECTED" and self._loop and not self._loop.is_closed():
                                    self._loop.create_task(ws.send_json({
                                        "type": "device_status",
                                        "device": device,
                                        "status": status,
                                        "timestamp": int(time.time())
                                    }))
                                else:
                                    closed_ws.add(ws)
                            except Exception:
                                closed_ws.add(ws)
                        self.active_websockets -= closed_ws
                        print(f"🔄 Đã cập nhật và broadcast {device}: {status}")

            elif topic.startswith("iot/device/status/"):
                device = topic.split("/")[-1]
                if device in self.device_states:
                    status = payload.get("status")
                    if status is not None:
                        print(f"📥 Nhận từ {topic}: {payload}")
                        self.device_states[device] = status
            # Nhận dữ liệu sensor
            elif topic == "iot/sensor/data":
                self.latest_data = payload # Lưu vào latest_data
                                            # Gửi realtime cho WebSocket
                                            # Mỗi 5 phút → ghi vào PostgreSQL
                closed_ws = set()
                for ws in self.active_websockets:
                    try:
                        if ws.application_state == ws.State.CONNECTED and self._loop and not self._loop.is_closed():
                            self._loop.create_task(ws.send_json({"latest": self.latest_data}))
                        else:
                            closed_ws.add(ws)
                    except Exception:
                        closed_ws.add(ws)
                self.active_websockets -= closed_ws
                
                now = datetime.now()
                if not self.last_db_update or (now - self.last_db_update).total_seconds() >= 300:
                    save_to_db(payload)
                    self.last_db_update = now

        except Exception as e:
            print(f"❌ Lỗi xử lý message: {str(e)}")

    def publish_all_states(self):
        for device, status in self.device_states.items():
            self.control_device(device, status)

    async def disconnect(self):
        try:
            if self._reconnect_task:
                self._reconnect_task.cancel()
                self._reconnect_task = None

            if self._keep_alive_task:
                self._keep_alive_task.cancel()
                self._keep_alive_task = None

            self.client.loop_stop()
            self.client.disconnect()
            self.is_connected = False
            self._broadcast_connection_status(False)
            print("✅ Đã ngắt kết nối MQTT")
        except Exception as e:
            print(f"❌ Lỗi khi ngắt kết nối MQTT: {str(e)}")

vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
# Các object chính
mqtt_client = MQTTClient() # MQTT client dùng giao tiếp realtime
device_timer = DeviceTimer(mqtt_client) # device_timer dùng để tự động tắt thiết bị sau X phút
# PostgreSQL Database
def init_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        # Tạo bảng sensor_history
        # Tạo bảng config
        # Thêm bản ghi mẫu nếu DB trống
        cur.execute('''CREATE TABLE IF NOT EXISTS sensor_history (
                        id SERIAL PRIMARY KEY,
                        timestamp TIMESTAMP,
                        temperature REAL,
                        humidity REAL,
                        nitrogen REAL,
                        phosphorus REAL,
                        potassium REAL,
                        ph REAL,
                        rainfall REAL DEFAULT 0,
                        monthly_rainfall REAL DEFAULT 0
                    )''')

        cur.execute('SELECT COUNT(*) FROM sensor_history')
        if cur.fetchone()[0] == 0:
            current_time = datetime.now(vn_tz)
            monthly_rainfall = get_last_month_rainfall()
            cur.execute('''INSERT INTO sensor_history
                        (timestamp, temperature, humidity, nitrogen, phosphorus, potassium, ph, rainfall, monthly_rainfall)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                     (current_time, 29.3, 26.2, 17, 87, 80, 6.0, 0, monthly_rainfall))

        cur.execute('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value JSONB
            )
        ''')

        conn.commit()
        conn.close()
        print("✅ Đã khởi tạo PostgreSQL database và thêm dữ liệu mẫu")
    except Exception as e:
        print(f"❌ Lỗi khi khởi tạo PostgreSQL: {e}")
# Ghi sensor + lương mưa vào database
def save_to_db(data):
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        current_time = datetime.now(vn_tz)
        current_rainfall = asyncio.run(get_rainfall_data())
        monthly_rainfall = get_last_month_rainfall()
        cur.execute('''INSERT INTO sensor_history
                    (timestamp, temperature, humidity, nitrogen, phosphorus, potassium, ph, rainfall, monthly_rainfall)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                 (current_time,
                  data.get('temperature', 0),
                  data.get('humidity', 0),
                  data.get('nitrogen', 0),
                  data.get('phosphorus', 0),
                  data.get('potassium', 0),
                  data.get('ph', 0),
                  current_rainfall,
                  monthly_rainfall))
        conn.commit()
        conn.close()
        print(f"✅ Đã lưu dữ liệu vào PostgreSQL: {data}")
        print(f"🌧️ Lượng mưa hiện tại: {current_rainfall}mm")
        print(f"🌧️ Tổng lượng mưa tháng trước: {monthly_rainfall}mm")
    except Exception as e:
        print(f"❌ Lỗi khi lưu vào PostgreSQL: {e}")
# Lấy lịch sử cảm biến → trả JSON
def get_history_from_db():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute('''SELECT timestamp, temperature, humidity, rainfall, nitrogen, phosphorus, potassium, ph, monthly_rainfall
                    FROM sensor_history
                    ORDER BY timestamp DESC''')
        rows = cur.fetchall()
        conn.close()

        def ensure_vn_tz(dt):
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=vn_tz)
            return dt.astimezone(vn_tz)
        # return [{
        #     'timestamp': ensure_vn_tz(row['timestamp']).isoformat() if row['timestamp'] else None,
        #     'temperature': row['temperature'],
        #     'humidity': row['humidity'],
        #     'rainfall': row['rainfall'],
        #     'nitrogen': row['nitrogen'],
        #     'phosphorus': row['phosphorus'],
        #     'potassium': row['potassium'],
        #     'ph': row['ph'],
        #     'monthly_rainfall': row['monthly_rainfall']
        # } for row in rows]
        return [{
            'timestamp': row['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if row['timestamp'] else None,
            'temperature': row['temperature'],
            'humidity': row['humidity'],
            'rainfall': row['rainfall'],
            'nitrogen': row['nitrogen'],
            'phosphorus': row['phosphorus'],
            'potassium': row['potassium'],
            'ph': row['ph'],
            'monthly_rainfall': row['monthly_rainfall']
        } for row in rows]
    except Exception as e:
        print(f"Error getting history from DB: {e}")
        return []
# Hàm lấy dữ liệu lượng mưa
async def get_rainfall_data():
    try:
        latitude = 10.8471
        longitude = 106.7872
        start_date = end_date = datetime.now().strftime('%Y-%m-%d')
        # API: open-meteo.com
        # Lấy lượng mưa hằng ngày tại vị trí cố định
        # Chạy bất đồng bộ
        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}" 
            f"&start_date={start_date}&end_date={end_date}"
            f"&daily=precipitation_sum&timezone=Asia/Ho_Chi_Minh"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    print("Lỗi khi lấy dữ liệu thời tiết:", await response.text())
                    return 0.0
                data = await response.json()
                rainfall_list = data.get("daily", {}).get("precipitation_sum", [])
                total_rain_today = rainfall_list[0] if rainfall_list else 0.0

                return total_rain_today
    except Exception as e:
        print("Lỗi khi lấy dữ liệu lượng mưa:", e)
        return 0.0
# Thống kê lượng mưa tháng trước
def get_last_month_rainfall():
    latitude = 10.8411
    longitude = 106.8090
    today = datetime.now()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_day_last_month = today.replace(day=1) - timedelta(days=1)
    start_date = first_day_last_month.strftime("%Y-%m-%d")
    end_date = last_day_last_month.strftime("%Y-%m-%d")
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&start_date={start_date}&end_date={end_date}&daily=precipitation_sum&timezone=Asia/Ho_Chi_Minh"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            rainfall_data = data["daily"]["precipitation_sum"]
            total_rainfall = sum(x for x in rainfall_data if x is not None)
            return round(total_rainfall, 2)
        else:
            print(f"❌ Lỗi API lấy lượng mưa tháng trước: {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ Lỗi khi lấy lượng mưa tháng trước: {e}")
        return 0

async def get_forecast_rainfall():
    # Gọi OpenWeather dự báo 5 ngày
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(URL) as response:
                if response.status != 200:
                    print(f"OpenWeather API error: {response.status}")
                    return {'today': {'rainfall': 0, 'temperature': 0, 'humidity': 0}, 'forecast_5days': []}
                data = await response.json()
                forecast_by_day = defaultdict(list)
                # Gom dữ liệu theo ngày
                # nhiệt độ trung bình
                # độ ẩm trung bình
                # tổng lượng mưa
                # icon thời tiết
                for entry in data['list']:
                    dt = datetime.fromtimestamp(entry['dt'])
                    date_str = dt.strftime('%Y-%m-%d')
                    temp = entry['main']['temp']
                    humidity = entry['main']['humidity']
                    rain = entry.get('rain', {}).get('3h', 0)
                    weather_info = entry.get('weather', [{}])[0]
                    icon_code = weather_info.get('icon', '')
                    description = weather_info.get('description', '')
                    forecast_by_day[date_str].append({
                        'time': dt.strftime('%H:%M'),
                        'temp': temp,
                        'humidity': humidity,
                        'rain': rain,
                        'icon_code': icon_code,
                        'description': description
                    })
                today_str = datetime.now().strftime('%Y-%m-%d')
                forecast_5days = []
                today_data = {'rainfall': 0, 'temperature': 0, 'humidity': 0}
                for idx, (date, entries) in enumerate(sorted(forecast_by_day.items())):
                    avg_temp = sum(e['temp'] for e in entries) / len(entries)
                    avg_humidity = sum(e['humidity'] for e in entries) / len(entries)
                    total_rain = sum(e['rain'] for e in entries)
                    mid_day_entry = entries[len(entries)//2] if entries else entries[0]
                    icon_code = mid_day_entry.get('icon_code', '')
                    description = mid_day_entry.get('description', '')
                    icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png" if icon_code else ''
                    forecast_5days.append({
                        'date': date,
                        'temperature': round(avg_temp, 2),
                        'humidity': round(avg_humidity, 2),
                        'rainfall': round(total_rain, 2),
                        'description': description,
                        'icon': icon_url
                    })
                    if date == today_str:
                        today_data = {
                            'rainfall': round(total_rain, 2),
                            'temperature': round(avg_temp, 2),
                            'humidity': round(avg_humidity, 2)
                        }
                    if len(forecast_5days) >= 5:
                        break
                
                return {'today': today_data, 'forecast_5days': forecast_5days}
    except Exception as e:
        print(f"Error fetching forecast data: {e}")
        return {'today': {'rainfall': 0, 'temperature': 0, 'humidity': 0}, 'forecast_5days': []}
# lấy cấu hình cảnh báo nhiệt độ từ database
# Chức năng chính
 # Kết nối PostgreSQL
 # Lấy giá trị trong bảng config với key = "temperature_alert"
 # Nếu có → trả về cấu hình từ database
def load_config():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'temperature_alert'")
        row = cur.fetchone()
        conn.close()
        if row and row[0]: # Nếu bản ghi tồn tại, trả về cấu hình JSON đúng như lưu trong DB.
            return {"temperature_alert": row[0]}
        # Nếu không có cấu hình, trả về cấu hình mặc định:
        return {
            "temperature_alert": {
                "threshold": 35.0,
                "last_alert_time": None, #Không có thời điểm cảnh báo trước đó
                "alert_cooldown": 300 # Thời gian chờ 5 phút giữa 2 cảnh báo
            }
        }
    except Exception as e:
        print(f"❌ Lỗi khi đọc config từ DB: {e}")
        return {
            "temperature_alert": {
                "threshold": 35.0,
                "last_alert_time": None,
                "alert_cooldown": 300
            }
        }
# lưu cấu hình cảnh báo vào database
def save_config(config):
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO config (key, value)
            VALUES ('temperature_alert', %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, [json.dumps(config['temperature_alert'])]
        )
        conn.commit()
        conn.close()
        print("✅ Đã lưu cấu hình vào database")
    except Exception as e:
        print(f"❌ Lỗi khi lưu config vào DB: {e}")
# gửi dữ liệu realtime qua WebSocket
async def send_data(websocket: WebSocket, mqtt_client: MQTTClient):
    try:
        while True:
            if websocket.application_state.name != "CONNECTED":
                print("WebSocket is no longer connected, exiting send_data")
                break

            sensor_data = mqtt_client.latest_data.copy() if mqtt_client.latest_data else {}
            if sensor_data:
                current_rainfall = await get_rainfall_data() # Lượng mưa hôm nay
                sensor_data['rainfall'] = current_rainfall
                monthly_rainfall = get_last_month_rainfall() # Lượng mưa tháng
                sensor_data['monthly_rainfall'] = monthly_rainfall
                mqtt_client.latest_data.update({
                    'rainfall': current_rainfall,
                    'monthly_rainfall': monthly_rainfall
                })
            history_data = get_history_from_db() # Lịch sử cảm biến
            forecast_data = await get_forecast_rainfall() # Dự báo mưa 5 ngày
            message = {
                'latest': sensor_data,
                'history': history_data,
                'today': forecast_data['today'],
                'forecast_5days': forecast_data['forecast_5days']
            }
            await websocket.send_json(message) # Gửi toàn bộ gói dữ liệu về client qua WebSocket.
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("WebSocket disconnected in send_data")
    except Exception as e:
        print(f"Error in send_data: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        mqtt_client.active_websockets.discard(websocket)
# Redirect trang chủ → login
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/static/login.html")
# API - trả về bản ghi sensor mới nhất
@app.get("/latest-data")
async def get_latest_data():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        cur.execute('''SELECT temperature, humidity, nitrogen, phosphorus, potassium, ph, rainfall, monthly_rainfall 
                    FROM sensor_history
                    ORDER BY timestamp DESC
                    LIMIT 1''') # Trả về giá trị mới nhất.
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                'temperature': round(float(row[0]), 2),
                'humidity': float(row[1]),
                'nitrogen': float(row[2]),
                'phosphorus': float(row[3]),
                'potassium': float(row[4]),
                'ph': float(row[5]),
                'rainfall': float(row[6]),
                'monthly_rainfall': float(row[7])
            }
        return JSONResponse({'error': 'No data found'}, status_code=404)
    except Exception as e:
        print(f"Error in /latest-data: {str(e)}")
        return JSONResponse({'error': str(e)}, status_code=500)
# API /quick-fill – điền nhanh vào form dự báo cây
# Dùng để tự động điền form "Khuyến nghị cây trồng".
@app.get("/quick-fill")
async def get_quick_fill_data():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cur = conn.cursor()
        cur.execute('''SELECT temperature, humidity, nitrogen, phosphorus, potassium, ph, monthly_rainfall
                    FROM sensor_history
                    ORDER BY timestamp DESC
                    LIMIT 1''')
        row = cur.fetchone()
        conn.close()
        if row:
            return {
                'temperature': round(float(row[0]), 2),
                'humidity': round(float(row[1]), 2),
                'nitrogen': round(float(row[2]), 2),
                'phosphorus': round(float(row[3]), 2),
                'potassium': round(float(row[4]), 2),
                'ph': round(float(row[5]), 2),
                'monthly_rainfall': round(float(row[6]), 2)
            }
        monthly_rainfall = get_last_month_rainfall()
        return {
            'temperature': 0.00,
            'humidity': 0.00,
            'nitrogen': 0.00,
            'phosphorus': 0.00,
            'potassium': 0.00,
            'ph': 0.00,
            'monthly_rainfall': round(monthly_rainfall, 2)
        }
    except Exception as e:
        print(f"Error in /quick-fill: {str(e)}")
        return JSONResponse({'error': str(e)}, status_code=500)
# API /predict – khuyến nghị cây trồng bằng ML model
# chức năng 
# Nhận dữ liệu từ client
# Lấy lượng mưa tháng
# Chuẩn hóa dữ liệu bằng scaler
# Dự đoán bằng model
# Giải mã kết quả bằng label_encoder
# Lấy ra tên cây tiếng Việt
@app.post("/predict")
async def predict(request: Request):
    if not all([model, scaler, label_encoder]):
        return JSONResponse({'error': 'Chức năng khuyến nghị cây trồng không khả dụng do lỗi tải models'}, status_code=503)
    try:
        data = await request.json()
        if not data:
            return JSONResponse({'error': 'Không có dữ liệu được gửi'}, status_code=400)
        monthly_rainfall = get_last_month_rainfall()
        input_data = {
            'N': float(data['N']),
            'P': float(data['P']),
            'K': float(data['K']),
            'temperature': float(data['temperature']),
            'humidity': float(data['humidity']),
            'ph': float(data['ph']),
            'rainfall': monthly_rainfall
        }
        df = pd.DataFrame([input_data])
        scaled_data = scaler.transform(df)
        prediction = model.predict(scaled_data)
        crop_en = label_encoder.inverse_transform(prediction)[0]
        crop_vi = CROP_TRANSLATIONS.get(crop_en.lower(), crop_en)
        crop_params = {
            'rice': {
                'temperature': {'min': 20, 'max': 27},
                'humidity': {'min': 80, 'max': 85},
                'nitrogen': {'min': 60, 'max': 99},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 35, 'max': 45},
                'ph': {'min': 5.0, 'max': 7.8}
            },
            'maize': {
                'temperature': {'min': 18, 'max': 26},
                'humidity': {'min': 55, 'max': 74},
                'nitrogen': {'min': 60, 'max': 100},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 5.5, 'max': 7.0}
            },
            'chickpea': {
                'temperature': {'min': 17, 'max': 21},
                'humidity': {'min': 14, 'max': 20},
                'nitrogen': {'min': 20, 'max': 60},
                'phosphorus': {'min': 55, 'max': 80},
                'potassium': {'min': 75, 'max': 85},
                'ph': {'min': 6.0, 'max': 8.9}
            },
            'kidneybeans': {
                'temperature': {'min': 15, 'max': 24},
                'humidity': {'min': 18, 'max': 25},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 55, 'max': 80},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 5.5, 'max': 6.0}
            },
            'pigeonpeas': {
                'temperature': {'min': 18, 'max': 39},
                'humidity': {'min': 14, 'max': 35},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 55, 'max': 80},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 4.0, 'max': 8.8}
            },
            'mothbeans': {
                'temperature': {'min': 24, 'max': 32},
                'humidity': {'min': 25, 'max': 35},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 3.5, 'max': 9.0}
            },
            'mungbean': {
                'temperature': {'min': 27, 'max': 30},
                'humidity': {'min': 80, 'max': 90},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 6.2, 'max': 7.6}
            },
            'blackgram': {
                'temperature': {'min': 26, 'max': 32},
                'humidity': {'min': 60, 'max': 70},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 55, 'max': 80},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 4.9, 'max': 7.6}
            },
            'lentil': {
                'temperature': {'min': 18, 'max': 27},
                'humidity': {'min': 60, 'max': 70},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 55, 'max': 80},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 5.8, 'max': 7.8}
            },
            'pomegranate': {
                'temperature': {'min': 18, 'max': 24},
                'humidity': {'min': 85, 'max': 95},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 35, 'max': 45},
                'ph': {'min': 5.4, 'max': 7.8}
            },
            'banana': {
                'temperature': {'min': 25, 'max': 30},
                'humidity': {'min': 75, 'max': 85},
                'nitrogen': {'min': 80, 'max': 120},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 45, 'max': 55},
                'ph': {'min': 5.0, 'max': 7.0}
            },
            'mango': {
                'temperature': {'min': 27, 'max': 35},
                'humidity': {'min': 45, 'max': 55},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 15, 'max': 40},
                'potassium': {'min': 25, 'max': 35},
                'ph': {'min': 4.3, 'max': 7.6}
            },
            'grapes': {
                'temperature': {'min': 8, 'max': 32},
                'humidity': {'min': 80, 'max': 85},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 120, 'max': 145},
                'potassium': {'min': 195, 'max': 205},
                'ph': {'min': 5.5, 'max': 7.0}
            },
            'watermelon': {
                'temperature': {'min': 24, 'max': 27},
                'humidity': {'min': 80, 'max': 90},
                'nitrogen': {'min': 80, 'max': 120},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 5, 'max': 15},
                'ph': {'min': 6.0, 'max': 6.8}
            },
            'muskmelon': {
                'temperature': {'min': 27, 'max': 29},
                'humidity': {'min': 90, 'max': 95},
                'nitrogen': {'min': 80, 'max': 120},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 5, 'max': 15},
                'ph': {'min': 6.0, 'max': 6.8}
            },
            'apple': {
                'temperature': {'min': 21, 'max': 24},
                'humidity': {'min': 85, 'max': 95},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 120, 'max': 145},
                'potassium': {'min': 195, 'max': 205},
                'ph': {'min': 5.5, 'max': 7.0}
            },
            'orange': {
                'temperature': {'min': 10, 'max': 34},
                'humidity': {'min': 85, 'max': 95},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 5, 'max': 15},
                'ph': {'min': 4.0, 'max': 9.0}
            },
            'papaya': {
                'temperature': {'min': 23, 'max': 44},
                'humidity': {'min': 85, 'max': 95},
                'nitrogen': {'min': 40, 'max': 80},
                'phosphorus': {'min': 5, 'max': 60},
                'potassium': {'min': 45, 'max': 55},
                'ph': {'min': 4.3, 'max': 7.6}
            },
            'coconut': {
                'temperature': {'min': 25, 'max': 30},
                'humidity': {'min': 90, 'max': 100},
                'nitrogen': {'min': 0, 'max': 40},
                'phosphorus': {'min': 5, 'max': 30},
                'potassium': {'min': 25, 'max': 35},
                'ph': {'min': 5.5, 'max': 6.5}
            },
            'cotton': {
                'temperature': {'min': 22, 'max': 26},
                'humidity': {'min': 75, 'max': 85},
                'nitrogen': {'min': 100, 'max': 140},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 15, 'max': 25},
                'ph': {'min': 5.8, 'max': 8.0}
            },
            'jute': {
                'temperature': {'min': 23, 'max': 27},
                'humidity': {'min': 70, 'max': 90},
                'nitrogen': {'min': 60, 'max': 100},
                'phosphorus': {'min': 35, 'max': 60},
                'potassium': {'min': 35, 'max': 45},
                'ph': {'min': 6.0, 'max': 7.5}
            },
            'coffee': {
                'temperature': {'min': 23, 'max': 28},
                'humidity': {'min': 50, 'max': 70},
                'nitrogen': {'min': 80, 'max': 120},
                'phosphorus': {'min': 15, 'max': 40},
                'potassium': {'min': 25, 'max': 35},
                'ph': {'min': 6.0, 'max': 7.5}
            }
        }
        warnings_list = []
        suggestions = []
        ideal_params = crop_params.get(crop_en.lower(), {}) # Kiểm tra tham số lý tưởng của từng cây
        if ideal_params:
            if input_data['temperature'] < ideal_params['temperature']['min']:
                warnings_list.append(f"⚠️ Nhiệt độ ({input_data['temperature']}°C) thấp hơn mức tối thiểu ({ideal_params['temperature']['min']}°C)") # nếu thông số hiện tại thấp hơn min → cảnh báo và gợi ý
                suggestions.append("🔼 Cần tăng nhiệt độ")                                                                                              
            elif input_data['temperature'] > ideal_params['temperature']['max']:
                warnings_list.append(f"⚠️ Nhiệt độ ({input_data['temperature']}°C) cao hơn mức tối đa ({ideal_params['temperature']['max']}°C)") # cảnh báo và gợi ý
                suggestions.append("🔽 Cần giảm nhiệt độ")
            if input_data['humidity'] < ideal_params['humidity']['min']:
                warnings_list.append(f"⚠️ Độ ẩm ({input_data['humidity']}%) thấp hơn mức tối thiểu ({ideal_params['humidity']['min']}%)")
                suggestions.append("🔼 Cần tăng độ ẩm")
            elif input_data['humidity'] > ideal_params['humidity']['max']:
                warnings_list.append(f"⚠️ Độ ẩm ({input_data['humidity']}%) cao hơn mức tối đa ({ideal_params['humidity']['max']}%)")
                suggestions.append("🔽 Cần giảm độ ẩm")
            if input_data['N'] < ideal_params['nitrogen']['min']:
                warnings_list.append(f"⚠️ Nitrogen ({input_data['N']}mg/kg) thấp hơn mức tối thiểu ({ideal_params['nitrogen']['min']}mg/kg)")
                suggestions.append("🔼 Cần bổ sung phân đạm")
            elif input_data['N'] > ideal_params['nitrogen']['max']:
                warnings_list.append(f"⚠️ Nitrogen ({input_data['N']}mg/kg) cao hơn mức tối đa ({ideal_params['nitrogen']['max']}mg/kg)")
                suggestions.append("🔽 Cần giảm phân đạm")
            if input_data['P'] < ideal_params['phosphorus']['min']:
                warnings_list.append(f"⚠️ Phosphorus ({input_data['P']}mg/kg) thấp hơn mức tối thiểu ({ideal_params['phosphorus']['min']}mg/kg)")
                suggestions.append("🔼 Cần bổ sung phân lân")
            elif input_data['P'] > ideal_params['phosphorus']['max']:
                warnings_list.append(f"⚠️ Phosphorus ({input_data['P']}mg/kg) cao hơn mức tối đa ({ideal_params['phosphorus']['max']}mg/kg)")
                suggestions.append("🔽 Cần giảm phân lân")
            if input_data['K'] < ideal_params['potassium']['min']:
                warnings_list.append(f"⚠️ Potassium ({input_data['K']}mg/kg) thấp hơn mức tối thiểu ({ideal_params['potassium']['min']}mg/kg)")
                suggestions.append("🔼 Cần bổ sung phân kali")
            elif input_data['K'] > ideal_params['potassium']['max']:
                warnings_list.append(f"⚠️ Potassium ({input_data['K']}mg/kg) cao hơn mức tối đa ({ideal_params['potassium']['max']}mg/kg)")
                suggestions.append("🔽 Cần giảm phân kali")
            if input_data['ph'] < ideal_params['ph']['min']:
                warnings_list.append(f"⚠️ pH ({input_data['ph']}) thấp hơn mức tối thiểu ({ideal_params['ph']['min']})")
                suggestions.append("🔼 Cần tăng độ pH")
            elif input_data['ph'] > ideal_params['ph']['max']:
                warnings_list.append(f"⚠️ pH ({input_data['ph']}) cao hơn mức tối đa ({ideal_params['ph']['max']})")
                suggestions.append("🔽 Cần giảm độ pH")
        response = {
            'prediction_text': f'Cây trồng được khuyến nghị: {crop_vi}', # trả về 
            'warnings': warnings_list,
            'suggestions': suggestions,
            'ideal_params': ideal_params,
            'current_params': {**input_data, 'rainfall': monthly_rainfall}
        }
        return response
    except Exception as e:
        print(f"Error during prediction: {str(e)}")
        return JSONResponse({'error': f'Có lỗi xảy ra khi khuyến nghị cây trồng: {str(e)}'}, status_code=500)
# API: Thiết lập cảnh báo nhiệt độ
@app.post("/set-temperature-alert")
async def set_temperature_alert(request: Request):
    try:
        data = await request.json()
        if not data or 'threshold' not in data:
            return JSONResponse({'success': False, 'error': 'Thiếu thông tin ngưỡng nhiệt độ'}, status_code=400)
        threshold = float(data['threshold'])
        if threshold < 0 or threshold > 50:
            return JSONResponse({'success': False, 'error': 'Ngưỡng nhiệt độ phải nằm trong khoảng 0-50°C'}, status_code=400)
        config = load_config()
        config['temperature_alert']['threshold'] = threshold
        save_config(config)
        print(f"✅ Đã cập nhật ngưỡng cảnh báo nhiệt độ: {threshold}°C")
        return {'success': True, 'threshold': threshold}
    except Exception as e:
        print(f"❌ Lỗi khi thiết lập ngưỡng cảnh báo nhiệt độ: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)

@app.post("/test-temperature-alert")
async def test_temperature_alert(request: Request):
    try: # Thay đổi ngưỡng cảnh báo:
        data = await request.json()
        if not data or 'threshold' not in data:
            return JSONResponse({'success': False, 'error': 'Thiếu thông tin ngưỡng nhiệt độ'}, status_code=400)
        threshold = float(data['threshold'])
        if threshold < 0 or threshold > 50: # Kiểm tra hợp lệ (0–50), Lưu DB bằng save_config
            return JSONResponse({'success': False, 'error': 'Ngưỡng nhiệt độ phải nằm trong khoảng 0-50°C'}, status_code=400)
        sensor_data = await get_latest_data()
        if not sensor_data or 'temperature' not in sensor_data:
            return JSONResponse({'success': False, 'error': 'Không thể lấy dữ liệu cảm biến'}, status_code=500)
        current_temp = sensor_data['temperature']
        print(f"✅ Đã gửi thông báo thử nghiệm với ngưỡng {threshold}°C")
        return {
            'success': True,
            'message': 'Đã gửi thông báo thử nghiệm',
            'current_temperature': current_temp,
            'threshold': threshold
        } # Trả về kết quả
    except Exception as e:
        print(f"❌ Lỗi khi gửi thông báo thử nghiệm: {e}")
        return JSONResponse({'success': False, 'error': str(e)}, status_code=500)
# API Login                  
@app.post("/api/login")
async def api_login(request: Request):
    try:
        data = await request.json()
        username = data.get('username')
        password = data.get('password')

        env_username = os.getenv('LOGIN_USERNAME', 'admin')  ###
        env_password = os.getenv('LOGIN_PASSWORD', '2025')   ###

        if username == env_username and password == env_password:
            return {'success': True}
        else:
            return JSONResponse({'success': False, 'message': 'Tên đăng nhập hoặc mật khẩu không đúng'}, status_code=401)
    except Exception as e:
        print(f"Error in /api/login: {str(e)}")
        return JSONResponse({'error': str(e)}, status_code=500)
# API /history & /forecast
@app.get("/history") # trả toàn bộ dữ liệu cảm biến
async def get_history():
    try:
        current_time = datetime.now(vn_tz)
        return get_history_from_db()
    except Exception as e:
        print(f"Error in /history: {str(e)}")
        return JSONResponse({'error': str(e)}, status_code=500)

@app.get("/forecast") # dự báo mưa từ API khác
async def get_forecast():
    try:
        current_time = datetime.now(vn_tz)
        return await get_forecast_rainfall()
    except Exception as e:
        print(f"Error in /forecast: {str(e)}")
        return JSONResponse({'error': str(e)}, status_code=500)
# WebSocket chính
@app.websocket("/ws")
# Nhận kết nối WebSocket:
async def websocket_endpoint(websocket: WebSocket): 
    await websocket.accept() # Gửi dữ liệu realtime cho từng client.
    mqtt_client.active_websockets.add(websocket)
    try:
        await send_data(websocket, mqtt_client)
    except WebSocketDisconnect:
        print("WebSocket disconnected in websocket_endpoint")
    except Exception as e:
        print(f"Unexpected error in websocket_endpoint: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        mqtt_client.active_websockets.discard(websocket)
        print("WebSocket removed from active connections")
# Bộ API Timer – hẹn giờ bật tắt thiết bị
@app.post("/api/set-timer")
async def set_timer(request: Request):
    try:        # Set giờ bật/tắt:
        data = await request.json()
        device = data.get('device')
        on_date = data.get('onDate')
        on_time = data.get('onTime')
        off_date = data.get('offDate')
        off_time = data.get('offTime')
        daily = data.get('daily', False) # bật hàng ngày

        if not all([device, on_date, on_time, off_date, off_time]):
            return {"success": False, "message": "Missing required parameters"}

        vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        on_dt = vn_tz.localize(datetime.strptime(f"{on_date} {on_time}", "%Y-%m-%d %H:%M"))
        off_dt = vn_tz.localize(datetime.strptime(f"{off_date} {off_time}", "%Y-%m-%d %H:%M"))

        success = device_timer.set_timer(device, on_dt.isoformat(), off_dt.isoformat(), daily)
        return {"success": success}
    except Exception as e:
        return {"success": False, "message": str(e)}
# Xóa timer một thiết bị.
@app.post("/api/clear-timer")
async def clear_timer(request: Request):
    try:
        data = await request.json()
        device = data.get('device')

        if not device:
            return {"success": False, "message": "Missing device parameter"}

        device_timer.clear_timer(device)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}
# Lấy timer hiện tại.
@app.get("/api/get-timer/{device}")
async def get_timer(device: str):
    try:
        timer = device_timer.get_timer(device)
        return {"success": True, "timer": timer}
    except Exception as e:
        return {"success": False, "message": str(e)}
# Thêm timer rời rạc (loại khác).
@app.post("/api/timer/add")
async def add_timer(device: str, time: str, status: bool):
    try:
        success = await device_timer.add_timer(device, time, status)
        if success:
            return {"status": "success", "message": f"Đã thêm timer cho {device}"}
        return {"status": "error", "message": "Timer đã tồn tại"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# Xoá timer rời rạc.
@app.post("/api/timer/remove")
async def remove_timer(device: str, time: str, status: bool):
    try:
        success = await device_timer.remove_timer(device, time, status)
        if success:
            return {"status": "success", "message": f"Đã xóa timer của {device}"}
        return {"status": "error", "message": "Không tìm thấy timer"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# Cập nhật timer rời rạc.
@app.post("/api/timer/update")
async def update_timer(device: str, old_time: str, new_time: str, status: bool):
    try:
        success = await device_timer.update_timer(device, old_time, new_time, status)
        if success:
            return {"status": "success", "message": f"Đã cập nhật timer của {device}"}
        return {"status": "error", "message": "Không tìm thấy timer"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# Lấy toàn bộ timer.
@app.get("/api/timer/list")
async def list_timers():
    try:
        return {"status": "success", "timers": device_timer.timers}
    except Exception as e:
        return {"status": "error", "message": str(e)}
# API trả cấu hình MQTT 
@app.get("/api/mqtt-config")
async def get_mqtt_config():
    """Trả về cấu hình MQTT cho client"""
    try:
        return {
            "success": True,
            "host": os.getenv("MQTT_BROKER", "localhost"),
            "port": int(os.getenv("MQTT_PORT", "8884")),
            "username": os.getenv("MQTT_USERNAME", "admin"),
            "password": os.getenv("MQTT_PASSWORD", "admin")
        }
    except Exception as e:
        print(f"❌ Lỗi khi lấy cấu hình MQTT: {e}")
        return {
            "success": False,
            "error": str(e)
        }
# WebSocketManager – broadcast cho nhiều client
class WebSocketManager:
    def __init__(self):
        self.active_connections = set()

    async def handle_websocket(self, websocket: WebSocket): # Nhận kết nối tới WebSocket riêng (cho broadcast).
        await websocket.accept()
        self.active_connections.add(websocket)
        try:
            while True:
                await asyncio.sleep(1)  
        except WebSocketDisconnect:
            print("Client disconnected")
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            self.active_connections.discard(websocket)

    async def broadcast(self, message: dict): # Gửi 1 message cho tất cả WebSocket đang hoạt động.
        disconnected = []
        for ws in list(self.active_connections):
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.active_connections.discard(ws)
# Mỗi 5 giây
# Lấy sensor mới nhất
# Lấy rainfall
# Lấy lịch sử
# Lấy forecast
# Gửi cho tất cả WebSocket
# ---> Hoạt động song song với WebSocket
    async def broadcast_loop(self):
        while True:
            try:
                sensor_data = mqtt_client.latest_data.copy() if mqtt_client.latest_data else {}
                if sensor_data:
                    current_rainfall = await get_rainfall_data()
                    sensor_data['rainfall'] = current_rainfall
                    monthly_rainfall = get_last_month_rainfall()
                    sensor_data['monthly_rainfall'] = monthly_rainfall
                    mqtt_client.latest_data.update({
                        'rainfall': current_rainfall,
                        'monthly_rainfall': monthly_rainfall
                    })
                history_data = get_history_from_db()
                forecast_data = await get_forecast_rainfall()
                message = {
                    'latest': sensor_data,
                    'history': history_data,
                    'today': forecast_data['today'],
                    'forecast_5days': forecast_data['forecast_5days']
                }
                
                for ws in list(self.active_connections):
                    try:
                        if ws.application_state == ws.State.CONNECTED:
                            await ws.send_json(message)
                        else:
                            self.active_connections.discard(ws)
                    except (WebSocketDisconnect, RuntimeError):
                        self.active_connections.discard(ws)
                        print("Removed disconnected WebSocket from broadcast_loop")
                await asyncio.sleep(5) 
            except Exception as e:
                print(f"Error in broadcast_loop: {e}")
                await asyncio.sleep(5)