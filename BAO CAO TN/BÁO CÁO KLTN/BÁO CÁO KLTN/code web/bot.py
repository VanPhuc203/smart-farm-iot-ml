import os
import logging
import json
import re
import time
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import discord # để làm bot
from discord.ext import commands, tasks
from dotenv import load_dotenv
import psycopg2 # để kết nối PostgreSQL
import paho.mqtt.client as mqtt # để publish/subscribe MQTT
import ssl
import requests # để gọi OpenRouter API & Open-Meteo
import numpy as np
import pandas as pd
import joblib # để load model ML
from sklearn.exceptions import InconsistentVersionWarning # để load model ML
import warnings
warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG # in log chi tiết, phục vụ debug
)
# Tải biến môi trường 
load_dotenv() # đọc các biến môi trường .env
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
OPENROUTER_API_URL = os.getenv("OPENROUTER_API_URL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
openrouter_headers = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "HTTP-Referer": "https://a-iot.onrender.com",
    "X-Title": "A-IOT"
}
# Khởi tạo bot Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
# Các biến toàn cục
user_contexts: Dict[int, List[dict]] = {}
MAX_CONTEXT_LENGTH = 10
device_states = {
    'light': False,
    'roof': False,
    'pump': False,
    'fan': False
}
device_icons = {
    'light': '💡',
    'roof': '🏠',
    'pump': '💧',
    'fan': '☢️'
}
device_names = {
    'light': 'Đèn',
    'roof': 'Mái che',
    'pump': 'Máy bơm',
    'fan': 'Quạt'
}
command_map = {
    'đèn': 'light',
    'mái che': 'roof',
    'máy bơm': 'pump',
    'quạt': 'fan'
}
DEVICE_COMMANDS = r'(?i)(bật|mở|tắt|đóng)\s*(đèn|mái\s+che|máy\s+bơm|quạt)'
TIME_PATTERN = r'^(\d+)\s*(phút|giờ|p|h|m|g)$'
SELECTING_DEVICE = 0
SELECTING_ACTION = 1
SELECTING_TIME = 2
ENTERING_CUSTOM_TIME = 3
SELECTING_NOTIFICATION_INTERVAL = 4
ENTERING_CUSTOM_INTERVAL = 5
scheduled_tasks: Dict[str, asyncio.Task] = {}
timer_messages: Dict[str, int] = {}
# map tên tiếng Anh ↔ tiếng Việt.
CROP_TRANSLATIONS = {
    'rice': 'Lúa', 'maize': 'Ngô', 'chickpea': 'Đậu gà', 'kidneybeans': 'Đậu thận',
    'pigeonpeas': 'Đậu săng', 'mothbeans': 'Đậu bướm', 'mungbean': 'Đậu xanh',
    'blackgram': 'Đậu đen', 'lentil': 'Đậu lăng', 'pomegranate': 'Lựu', 'banana': 'Chuối',
    'mango': 'Xoài', 'grapes': 'Nho', 'watermelon': 'Dưa hấu', 'muskmelon': 'Dưa lưới',
    'apple': 'Táo', 'orange': 'Cam', 'papaya': 'Đu đủ', 'coconut': 'Dừa', 'cotton': 'Bông',
    'jute': 'Đay', 'coffee': 'Cà phê'
}
# Phần ML & tham số cây trồng
MODEL_FILES = {
    'model': 'models/lgbm_crop_model.pkl',
    'scaler': 'models/scaler.pkl',
    'label_encoder': 'models/label_encoder.pkl'
}
try:
    model = joblib.load(MODEL_FILES['model'])
    scaler = joblib.load(MODEL_FILES['scaler'])
    label_encoder = joblib.load(MODEL_FILES['label_encoder'])
    print("✅ Đã tải models thành công")
except Exception as e:
    print(f"❌ Lỗi khi tải models: {e}")
    model = None
    scaler = None
    label_encoder = None
# chứa ngưỡng lý tưởng cho từng loại cây
CROP_PARAMETERS = {
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

VN_TZ = timezone(timedelta(hours=7))
# Kết nối PostgreSQL & config cảnh báo
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
        if row and row[0]:
            return {"temperature_alert": row[0]}
        return {
            "temperature_alert": {
                "threshold": 35.0,
                "last_alert_time": None,
                "alert_cooldown": 300
            }
        }
    except Exception as e:
        logging.error(f"❌ Lỗi khi đọc config từ DB: {e}")
        return {
            "temperature_alert": {
                "threshold": 35.0,
                "last_alert_time": None,
                "alert_cooldown": 300
            }
        }

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
        logging.info("✅ Đã lưu cấu hình vào database")
    except Exception as e:
        logging.error(f"❌ Lỗi khi lưu config vào DB: {e}")

config = load_config()
temperature_alert_settings = config['temperature_alert']
# Kết nối MQTT & điều khiển thiết bị
def setup_mqtt_client():
    client = mqtt.Client(protocol=mqtt.MQTTv311, transport="websockets")
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(tls_version=ssl.PROTOCOL_TLSv1_2)
    client.tls_insecure_set(False)

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("✅ Kết nối MQTT thành công")
            client.subscribe("iot/device/status/#", qos=1)
        else:
            print(f"❌ Kết nối MQTT thất bại với mã lỗi {rc}")

    def on_message(client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            device = topic.split('/')[-1]
            if device in device_states:
                device_states[device] = payload.get('status', False)
        except Exception as e:
            print(f"❌ Lỗi xử lý tin nhắn MQTT: {e}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"❌ Lỗi kết nối MQTT: {e}")

    return client

mqtt_client = setup_mqtt_client()

def control_device(device: str, status: bool) -> bool:
    try:
        topic = f"iot/device/control/{device}"
        payload = {
            "status": status,
            "timestamp": datetime.now(VN_TZ).isoformat()
        }
        print(f"Publishing to {topic}: {payload}")
        result = mqtt_client.publish(topic, json.dumps(payload), qos=1)
        print(f"Publish result: {result.rc}")
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            device_states[device] = status
            return True
        return False
    except Exception as e:
        print(f"❌ Lỗi điều khiển thiết bị: {e}")
        return False

def get_device_control_embed():
    embed = discord.Embed(title="🎮 Điều khiển thiết bị", color=discord.Color.blue())
    embed.add_field(name="💡 Đèn", value="Bật" if device_states['light'] else "Tắt", inline=True)
    embed.add_field(name="🏠 Mái che", value="Mở" if device_states['roof'] else "Đóng", inline=True)
    embed.add_field(name="💧 Máy bơm", value="Bật" if device_states['pump'] else "Tắt", inline=True)
    embed.add_field(name="☢️ Quạt", value="Bật" if device_states['fan'] else "Tắt", inline=True)
    return embed

def get_latest_sensor_data():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cursor = conn.cursor()
        cursor.execute('''
            SELECT temperature, humidity, nitrogen, phosphorus, potassium, ph
            FROM sensor_history
            ORDER BY timestamp DESC
            LIMIT 1
        ''')
        data = cursor.fetchone()
        conn.close()

        if data:
            return {
                'temperature': data[0],
                'humidity': data[1],
                'nitrogen': data[2],
                'phosphorus': data[3],
                'potassium': data[4],
                'ph': data[5]
            }
        return None
    except Exception as e:
        logging.error(f"Lỗi khi lấy dữ liệu cảm biến: {e}")
        return None

def get_ideal_parameters(crop_name_vi: str) -> str:
    crop_name_en = None
    for en, vi in CROP_TRANSLATIONS.items():
        if vi.lower() == crop_name_vi.lower():
            crop_name_en = en
            break
    if not crop_name_en or crop_name_en not in CROP_PARAMETERS:
        return ""
    params = CROP_PARAMETERS[crop_name_en]
    param_text = "\nThông số lý tưởng cho {}:\n".format(crop_name_vi)
    param_text += "- Nhiệt độ: {}-{}°C\n".format(params['temperature']['min'], params['temperature']['max'])
    param_text += "- Độ ẩm: {}-{}%\n".format(params['humidity']['min'], params['humidity']['max'])
    param_text += "- Nitơ: {}-{} mg/kg\n".format(params['nitrogen']['min'], params['nitrogen']['max'])
    param_text += "- Phốt pho: {}-{} mg/kg\n".format(params['phosphorus']['min'], params['phosphorus']['max'])
    param_text += "- Kali: {}-{} mg/kg\n".format(params['potassium']['min'], params['potassium']['max'])
    param_text += "- pH: {}-{}\n".format(params['ph']['min'], params['ph']['max'])
    return param_text
# Hệ thống nhắc nhở cho AI & ngữ cảnh
def get_system_prompt(sensor_data: dict = None, user_message: str = "") -> str:
    base_prompt = (
        "Bạn là trợ lý AI chuyên về nông nghiệp. Trả lời bằng tiếng Việt, ngắn gọn (dưới 100 từ), thân thiện, sử dụng emoji. "
        "Hệ thống chỉ hỗ trợ tư vấn về các cây trồng: Lúa, Ngô, Đậu gà, Đậu thận, Đậu săng, Đậu bướm, Đậu xanh, Đậu đen, Đậu lăng, Lựu, Chuối, Xoài, Nho, Dưa hấu, Dưa lưới, Táo, Cam, Đu đủ, Dừa, Bông, Đay, Cà phê. "
        "Nếu cây không trong danh sách, trả lời: '🤦‍♂️ Hệ thống chỉ hỗ trợ các cây trong danh sách sau: Lúa, Ngô, Đậu gà, Đậu thận, Đậu săng, Đậu bướm, Đậu xanh, Đậu đen, Đậu lăng, Lựu, Chuối, Xoài, Nho, Dưa hấu, Dưa lưới, Táo, Cam, Đu đủ, Dừa, Bông, Đay, Cà phê.' "
        "Chỉ trả lời câu hỏi mới nhất, không tham chiếu câu hỏi cũ. "
        "Ưu tiên giá trị trong câu hỏi của người dùng (ví dụ: độ ẩm 50%, pH 6.5) để so sánh với thông số lý tưởng, thay vì dữ liệu cảm biến. "
        "Luôn viết 'pH' đúng định dạng (chữ 'p' thường, 'H' hoa) khi nói về chỉ số hóa học. Không thay đổi các từ tiếng Việt thông thường như 'phục', 'phù', v.v."
        "Liệt kê tất cả cây trồng phù hợp với giá trị được hỏi, không chỉ chọn một cây. "
        "Trả lời một câu cho mỗi yếu tố được hỏi, không tự tạo câu hỏi. "
        "Nếu câu hỏi không liên quan đến thông số kỹ thuật, trả lời hài hước nhưng hữu ích."
    )
    ideal_param_text = ""
    for vi_name in CROP_TRANSLATIONS.values():
        if vi_name.lower() in user_message.lower():
            ideal_param_text = get_ideal_parameters(vi_name)
            break
    if sensor_data:
        sensor_prompt = "\nDữ liệu cảm biến hiện tại:\n"
        for key, value in sensor_data.items():
            sensor_prompt += f"- {key}: {value}\n"
        return base_prompt + sensor_prompt + ideal_param_text
    return base_prompt + ideal_param_text

def manage_context(user_id: int, role: str, content: str):
    if user_id not in user_contexts:
        user_contexts[user_id] = []
    user_contexts[user_id].append({"role": role, "content": content})
    if len(user_contexts[user_id]) > MAX_CONTEXT_LENGTH:
        user_contexts[user_id] = user_contexts[user_id][-MAX_CONTEXT_LENGTH:]

user_request_counts = {}
MAX_REQUESTS_PER_DAY = 50
# Gọi OpenRouter
async def get_ai_response(user_id: int, user_message: str, max_retries: int = 3) -> str:
    try:
        current_time = datetime.now(timezone.utc)
        if user_id not in user_request_counts:
            user_request_counts[user_id] = {"count": 0, "last_reset": current_time}
        else:
            last_reset = user_request_counts[user_id]["last_reset"]
            if (current_time - last_reset).days >= 1:
                user_request_counts[user_id] = {"count": 0, "last_reset": current_time}
            if user_request_counts[user_id]["count"] >= MAX_REQUESTS_PER_DAY:
                return "⏳ Bạn đã vượt quá giới hạn 50 yêu cầu/ngày. Vui lòng thử lại vào ngày mai."

        user_request_counts[user_id]["count"] += 1

        sensor_data = get_latest_sensor_data()
        system_prompt = get_system_prompt(sensor_data, user_message)
        context_messages = user_contexts.get(user_id, [])

        messages = [{"role": "system", "content": system_prompt}]
        for msg in context_messages[-5:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=openrouter_headers,
                    json={
                        "model": os.getenv("OPENROUTER_MODEL"),
                        "messages": messages,
                        "max_tokens": 200,
                        "temperature": 0.7
                    },
                    timeout=15
                )

                if response.status_code == 200:
                    result = response.json()
                    answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if not answer:
                        return "❌ Không nhận được câu trả lời hợp lệ từ AI."
                    answer = answer[0].upper() + answer[1:]
                    manage_context(user_id, "assistant", answer)
                    return answer
                elif response.status_code == 429:
                    return "⏳ Đã vượt quá giới hạn yêu cầu API. Vui lòng thử lại sau vài phút."
                elif response.status_code == 503:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return "⏳ Hệ thống AI đang bận. Vui lòng thử lại sau."
                else:
                    logging.error(f"API Error: {response.status_code} - {response.text}")
                    return "❌ Lỗi khi gọi API AI. Vui lòng thử lại sau."
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return "⏳ Hệ thống AI phản hồi chậm. Vui lòng thử lại sau."
            except requests.exceptions.RequestException as e:
                logging.error(f"Request error: {e}")
                return "❌ Không thể kết nối đến API AI. Vui lòng thử lại sau."
    except Exception as e:
        logging.error(f"Error in get_ai_response: {e}")
        return "❌ Có lỗi xảy ra khi xử lý câu hỏi của bạn. Vui lòng thử lại sau."
# Hẹn giờ thiết bị
async def schedule_device_action(device: str, action: bool, delay_minutes: int, channel_id: int):
    timer_id = f"{device}_{channel_id}_{int(time.time())}"
    message = None  
    try:
        device_vn = device_names.get(device, device)
        if timer_id not in timer_messages:
            message = await bot.get_channel(channel_id).send(
                f"⏳ Đang hẹn giờ: {delay_minutes} phút nữa sẽ {'bật' if action else 'tắt'} {device_vn}"
            )
            timer_messages[timer_id] = message.id
        else:
            channel = bot.get_channel(channel_id)
            message = await channel.fetch_message(timer_messages[timer_id])

        while delay_minutes > 0:
            await asyncio.sleep(60)
            delay_minutes -= 1
            if timer_id in timer_messages:
                await message.edit(
                    content=f"⏳ Đang hẹn giờ: {delay_minutes} phút nữa sẽ {'bật' if action else 'tắt'} {device_vn}"
                )
            else:
                break

        if timer_id in scheduled_tasks and not scheduled_tasks[timer_id].done():
            if control_device(device, action):
                await message.edit(
                    content=f"✅ Đã {'bật' if action else 'tắt'} {device_vn} theo lịch hẹn"
                )
            else:
                await message.edit(
                    content=f"❌ Không thể {'bật' if action else 'tắt'} {device_vn}. Vui lòng thử lại."
                )
    except asyncio.CancelledError:
        if timer_id in timer_messages:
            try:
                channel = bot.get_channel(channel_id)
                message = await channel.fetch_message(timer_messages[timer_id])
                await message.edit(content=f"⏰ Hẹn giờ cho {device_vn} đã bị hủy.")
            except discord.NotFound:
                pass 
            except discord.Forbidden:
                logging.error("Bot không có quyền chỉnh sửa tin nhắn.")
    except Exception as e:
        logging.error(f"Lỗi hẹn giờ: {e}")
    finally:
        if timer_id in timer_messages:
            del timer_messages[timer_id]
        if timer_id in scheduled_tasks:
            del scheduled_tasks[timer_id]

SENSOR_TRANSLATIONS = {
    "temperature": "Nhiệt độ",
    "humidity": "Độ ẩm",
    "nitrogen": "Nitơ",
    "phosphorus": "Phốt pho",
    "potassium": "Kali",
    "ph": "pH",
}

def get_last_month_rainfall():
    latitude = 10.8411
    longitude = 106.8090
    today = datetime.now(VN_TZ)
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
            logging.info(f"🌧️ Tổng lượng mưa tháng trước: {total_rainfall:.2f}mm")
            return round(total_rainfall, 2)
        else:
            logging.error(f"❌ Lỗi API lấy lượng mưa tháng trước: {response.status_code}")
            return 0
    except Exception as e:
        logging.error(f"❌ Lỗi khi lấy lượng mưa tháng trước: {e}")
        return 0
# Gửi dữ liệu cảm biến định kỳ qua Discord
discord_subscribed_users = {}
discord_subscription_jobs = {}

def save_discord_subscribers():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discord_subscribers (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                channel_id BIGINT,
                subscribed_at TIMESTAMP,
                interval INTEGER
            )
        ''')
        for user_id, info in discord_subscribed_users.items():
            cursor.execute(
                '''
                INSERT INTO discord_subscribers (user_id, username, channel_id, subscribed_at, interval)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET username = EXCLUDED.username,
                    channel_id = EXCLUDED.channel_id,
                    subscribed_at = EXCLUDED.subscribed_at,
                    interval = EXCLUDED.interval
                ''',
                (user_id, info['username'], info['channel_id'], info['subscribed_at'], info['interval'])
            )
        conn.commit()
        conn.close()
        logging.info("✅ Đã lưu discord_subscribed_users vào database")
    except Exception as e:
        logging.error(f"❌ Lỗi khi lưu discord_subscribed_users: {e}")

def load_discord_subscribers():
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("POSTGRES_DB", "sensor_data"),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", "postgres"),
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432")
        )
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS discord_subscribers (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                channel_id BIGINT,
                subscribed_at TIMESTAMP,
                interval INTEGER
            )
        ''')
        cursor.execute('SELECT user_id, username, channel_id, subscribed_at, interval FROM discord_subscribers')
        rows = cursor.fetchall()
        for row in rows:
            discord_subscribed_users[row[0]] = {
                'username': row[1],
                'channel_id': row[2],
                'subscribed_at': row[3],
                'interval': row[4]
            }
        conn.commit()
        conn.close()
        logging.info("✅ Đã tải discord_subscribed_users từ database")
    except Exception as e:
        logging.error(f"❌ Lỗi khi tải discord_subscribed_users: {e}")

async def send_sensor_data_to_user(user_id: int, channel_id: int):
    if user_id not in discord_subscribed_users:
        logging.warning(f"User {user_id} không còn trong danh sách đăng ký Discord")
        return

    data = get_latest_sensor_data()
    if not data:
        logging.error(f"Không lấy được dữ liệu cảm biến cho user {user_id}")
        return

    message = "📊 Dữ liệu cảm biến mới nhất:\n"
    message += f"•🌡️ Nhiệt độ: {data['temperature']}°C\n"
    message += f"•💧 Độ ẩm: {data['humidity']}%\n"
    message += f"•🌿 Nitơ: {data['nitrogen']} mg/kg\n"
    message += f"•🧪 Phốt pho: {data['phosphorus']} mg/kg\n"
    message += f"•⚡ Kali: {data['potassium']} mg/kg\n"
    message += f"•🔬 pH: {data['ph']}\n"
    message += "⏰ Cập nhật: " + datetime.now(VN_TZ).strftime("%d/%m/%Y %H:%M:%S\n")
    message += "------------------------------------------------"

    for attempt in range(3):
        try:
            channel = bot.get_channel(channel_id)
            if channel is None:
                logging.error(f"Không tìm thấy kênh với channel_id {channel_id} cho user {user_id}")
                if user_id in discord_subscribed_users:
                    del discord_subscribed_users[user_id]
                    save_discord_subscribers()
                return
            await channel.send(message)
            logging.info(f"Đã gửi thông báo cảm biến đến user {user_id}")
            break
        except Exception as e:
            logging.error(f"Lỗi khi gửi dữ liệu cảm biến đến user {user_id} (lần {attempt+1}): {e}")
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
            else:
                logging.warning(f"Bỏ qua thông báo cho user {user_id} sau 3 lần thử")

async def start_subscription_job(user_id: int, channel_id: int):
    if user_id not in discord_subscribed_users:
        logging.warning(f"Không tìm thấy user_id {user_id} trong discord_subscribed_users")
        return

    interval = discord_subscribed_users[user_id]['interval']
    if interval is None:
        logging.warning(f"Interval chưa được thiết lập cho user {user_id}")
        return

    logging.info(f"Đang tạo job định kỳ cho user {user_id} với interval {interval} giây")

    last_sent = time.time()  

    @tasks.loop(seconds=interval)
    async def user_job():
        nonlocal last_sent
        current_time = time.time()
        if current_time - last_sent >= interval:
            await send_sensor_data_to_user(user_id, channel_id)
            last_sent = current_time
            logging.info(f"Sent sensor data to user {user_id} from periodic job")
    # Hủy job cũ nếu tồn tại
    if user_id in discord_subscription_jobs:
        old_job = discord_subscription_jobs[user_id]
        if old_job.is_running():
            old_job.stop()
            logging.info(f"Đã dừng job cũ cho user {user_id}")
        try:
            await asyncio.sleep(0.1)  
            old_job.close()
        except Exception as e:
            logging.warning(f"Không thể đóng job cũ cho user {user_id}: {e}")
        logging.info(f"Đã xử lý job cũ cho user {user_id}")
    # Khởi tạo job mới
    try:
        user_job.start()
        discord_subscription_jobs[user_id] = user_job
        logging.info(f"Đã tạo job mới cho user {user_id} với interval {interval} giây")
    except Exception as e:
        logging.error(f"Không thể khởi động job mới cho user {user_id}: {e}")
        return
    await asyncio.sleep(interval)
# Xử lý sự kiện và lệnh
@bot.event
async def on_ready():
    print(f"🤖 Bot {bot.user.name} đã sẵn sàng!")
    load_discord_subscribers()
    for user_id, info in list(discord_subscribed_users.items()):
        if info.get('interval'):
            await start_subscription_job(user_id, info['channel_id'])
    check_temperature_alert.start()

@bot.command()
async def start(ctx):
    welcome_message = """
🌟 Chào mừng bạn đến với AgriTech Bot trên Discord! 🌟

Tôi là trợ lý ảo thông minh giúp bạn theo dõi và quản lý hệ thống giám sát chất lượng đất và cây trồng.

Các lệnh có sẵn:
!start - Khởi động bot
!helps - Xem hướng dẫn sử dụng
!sensor - Xem dữ liệu cảm biến mới nhất
!subscribe - Đăng ký nhận thông báo tự động
!check - Kiểm tra khoảng thời gian nhận thông báo
!change - Thay đổi khoảng thời gian nhận thông báo
!unsubscribe - Hủy đăng ký nhận thông báo
!device - Điều khiển thiết bị
!timer - Hẹn giờ thiết bị
!predict - Khuyến nghị cây trồng phù hợp
!ask <câu hỏi> - Đặt câu hỏi với trợ lý AI
!about - Thông tin về hệ thống
!clear - Xóa lịch sử trò chuyện

Hãy thử các lệnh trên để bắt đầu! 🌱
------------------------------------------------
    """
    await ctx.send(welcome_message)

@bot.command()
async def helps(ctx):
    help_text = """
📚 Hướng dẫn sử dụng AgriTech Bot:

1️⃣ Xem dữ liệu cảm biến:
   !sensor - Hiển thị các chỉ số mới nhất
   !subscribe - Đăng ký nhận thông báo tự động
   !check - Kiểm tra khoảng thời gian nhận thông báo
   !change - Thay đổi khoảng thời gian nhận thông báo
   !unsubscribe - Hủy đăng ký nhận thông báo

2️⃣ Điều khiển thiết bị:
   !device - Mở bảng điều khiển
   • Điều khiển đèn 💡
   • Điều khiển mái che 🏠
   • Điều khiển máy bơm 💧
   • Điều khiển quạt ☢️

3️⃣ Hẹn giờ thiết bị:
   !timer - Hẹn giờ bật/tắt thiết bị
   • Chọn thiết bị cần hẹn giờ
   • Chọn hành động bật/tắt
   • Đặt thời gian hẹn giờ
   !cancel - Hủy hẹn giờ

4️⃣ Khuyến nghị cây trồng:
   !predict - Nhận khuyến nghị cây trồng phù hợp
   • Dựa trên dữ liệu cảm biến hiện tại
   • So sánh thông số hiện tại và lý tưởng
   • Nhận đề xuất chăm sóc cây trồng

5️⃣ Hỏi AI:
   !ask <câu hỏi> - Đặt câu hỏi về nông nghiệp 
   VD: !ask Độ pH 6.5 có phù hợp với lúa không?

6️⃣ Thông tin hệ thống:
   !about - Thông tin về dự án
   !clear - Xóa lịch sử trò chuyện

❓ Cần giúp đỡ? Liên hệ:
   📧 Email: vuphucqtqt@gmail.com
   📞 SĐT: 0344 982 128
------------------------------------------------
    """
    await ctx.send(help_text)

@bot.command()
async def sensor(ctx):
    data = get_latest_sensor_data()
    if data:
        message = "📊 Dữ liệu cảm biến mới nhất:\n"
        message += f"•🌡️ Nhiệt độ: {data['temperature']}°C\n"
        message += f"•💧 Độ ẩm: {data['humidity']}%\n"
        message += f"•🌿 Nitơ: {data['nitrogen']} mg/kg\n"
        message += f"•🧪 Phốt pho: {data['phosphorus']} mg/kg\n"
        message += f"•⚡ Kali: {data['potassium']} mg/kg\n"
        message += f"•🔬 pH: {data['ph']}\n"
        now_vn = datetime.now(VN_TZ)
        message += "⏰ Cập nhật: " + now_vn.strftime("%d/%m/%Y %H:%M:%S\n")
        message += "------------------------------------------------"
    else:
        message = "❌ Không thể lấy dữ liệu cảm biến. Vui lòng thử lại sau."
        message += "------------------------------------------------"
    await ctx.send(message)

@bot.command()
async def about(ctx):
    about_text = """
🏢 Hệ thống Giám sát Chất lượng đất

📍 Địa chỉ: 
97 Man Thiện, Hiệp Phú, Thủ Đức, Thành phố Hồ Chí Minh

🔧 Tính năng:
• Giám sát thời gian thực
• Phân tích dữ liệu thông minh
• Khuyến nghị cây trồng
• Điều khiển thiết bị
• Trợ lý AI thông minh

📱 Liên hệ:
• SĐT: 0344 982 128
• Email: vuphucqtqt@gmail.com

🌐 Mạng xã hội:
• Facebook: [Link]
• YouTube: [Link]
• TikTok: [Link]
------------------------------------------------
    """
    await ctx.send(about_text)

@bot.command()
async def clear(ctx):
    if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
        await ctx.send("❌ Bot cần quyền 'Manage Messages' để xóa tin nhắn!\n------------------------------------------------")
        return

    try:
        deleted = await ctx.channel.purge(
            limit=100,
            check=lambda m: m.author == bot.user or m.content.startswith('!'),
            before=ctx.message
        )
        await ctx.send(f"🧹 Đã xóa {len(deleted)} tin nhắn!\n------------------------------------------------", delete_after=5)
    except discord.errors.Forbidden:
        await ctx.send("❌ Bot không có quyền xóa tin nhắn!\n------------------------------------------------")
    except Exception as e:
        logging.error(f"Error in clear command: {e}")
        await ctx.send("❌ Có lỗi xảy ra khi xóa tin nhắn.\n------------------------------------------------")

@bot.command()
async def device(ctx):
    embed = get_device_control_embed()
    view = DeviceControlView()
    await ctx.send(embed=embed, view=view)

class DeviceControlView(discord.ui.View):
    @discord.ui.button(label="💡 Đèn", style=discord.ButtonStyle.primary)
    async def toggle_light(self, interaction: discord.Interaction, button: discord.ui.Button):
        status = not device_states['light']
        if control_device('light', status):
            status_text = "bật" if status else "tắt"
            await interaction.response.send_message(f"{device_icons['light']} Đã {status_text} {device_names['light']}")
        else:
            await interaction.response.send_message("❌ Không thể điều khiển thiết bị. Vui lòng thử lại sau.\n------------------------------------------------")
        embed = get_device_control_embed()
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="🏠 Mái che", style=discord.ButtonStyle.primary)
    async def toggle_roof(self, interaction: discord.Interaction, button: discord.ui.Button):
        status = not device_states['roof']
        if control_device('roof', status):
            status_text = "mở" if status else "đóng"
            await interaction.response.send_message(f"{device_icons['roof']} Đã {status_text} {device_names['roof']}")
        else:
            await interaction.response.send_message("❌ Không thể điều khiển thiết bị. Vui lòng thử lại sau.\n------------------------------------------------")
        embed = get_device_control_embed()
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="💧 Máy bơm", style=discord.ButtonStyle.primary)
    async def toggle_pump(self, interaction: discord.Interaction, button: discord.ui.Button):
        status = not device_states['pump']
        if control_device('pump', status):
            status_text = "bật" if status else "tắt"
            await interaction.response.send_message(f"{device_icons['pump']} Đã {status_text} {device_names['pump']}")
        else:
            await interaction.response.send_message("❌ Không thể điều khiển thiết bị. Vui lòng thử lại sau.\n------------------------------------------------")
        embed = get_device_control_embed()
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label="☢️ Quạt", style=discord.ButtonStyle.primary)
    async def toggle_fan(self, interaction: discord.Interaction, button: discord.ui.Button):
        status = not device_states['fan']
        if control_device('fan', status):
            status_text = "bật" if status else "tắt"
            await interaction.response.send_message(f"{device_icons['fan']} Đã {status_text} {device_names['fan']}")
        else:
            await interaction.response.send_message("❌ Không thể điều khiển thiết bị. Vui lòng thử lại sau.\n------------------------------------------------")
        embed = get_device_control_embed()
        await interaction.message.edit(embed=embed, view=self)

@bot.command()
async def timer(ctx):
    embed = discord.Embed(title="🕒 Chọn thiết bị bạn muốn hẹn giờ", color=discord.Color.blue())
    view = TimerDeviceSelectView()
    await ctx.send(embed=embed, view=view)

class TimerDeviceSelectView(discord.ui.View):
    @discord.ui.button(label="💡 Đèn", style=discord.ButtonStyle.primary)
    async def select_light(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"⚡ Chọn hành động cho {device_names['light']}", color=discord.Color.blue())
        view = TimerActionSelectView(device='light')
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🏠 Mái che", style=discord.ButtonStyle.primary)
    async def select_roof(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"⚡ Chọn hành động cho {device_names['roof']}", color=discord.Color.blue())
        view = TimerActionSelectView(device='roof')
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="💧 Máy bơm", style=discord.ButtonStyle.primary)
    async def select_pump(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"⚡ Chọn hành động cho {device_names['pump']}", color=discord.Color.blue())
        view = TimerActionSelectView(device='pump')
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="☢️ Quạt", style=discord.ButtonStyle.primary)
    async def select_fan(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title=f"⚡ Chọn hành động cho {device_names['fan']}", color=discord.Color.blue())
        view = TimerActionSelectView(device='fan')
        await interaction.response.edit_message(embed=embed, view=view)

class TimerActionSelectView(discord.ui.View):
    def __init__(self, device: str):
        super().__init__(timeout=60) 
        self.device = device

    @discord.ui.button(label="🟢 Bật", style=discord.ButtonStyle.green)
    async def action_on(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"⏰ Chọn thời gian hẹn giờ để bật {device_names[self.device]}",
            color=discord.Color.blue()
        )
        view = TimerTimeSelectView(device=self.device, action=True)
        logging.info(f"Sending TimerTimeSelectView for device {self.device} with action ON")
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔴 Tắt", style=discord.ButtonStyle.red)
    async def action_off(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"⏰ Chọn thời gian hẹn giờ để tắt {device_names[self.device]}",
            color=discord.Color.blue()
        )
        view = TimerTimeSelectView(device=self.device, action=False)
        logging.info(f"Sending TimerTimeSelectView for device {self.device} with action OFF")
        await interaction.response.edit_message(embed=embed, view=view)

class TimerSelectView(discord.ui.View):
    def __init__(self, user_id: int, device: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.device = device

    @discord.ui.button(label="5 phút", style=discord.ButtonStyle.secondary)
    async def timer_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_timer(interaction, 5 * 60)

    @discord.ui.button(label="10 phút", style=discord.ButtonStyle.secondary)
    async def timer_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_timer(interaction, 10 * 60)

    @discord.ui.button(label="15 phút", style=discord.ButtonStyle.secondary)
    async def timer_15(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.set_timer(interaction, 15 * 60)

    @discord.ui.button(label="Tùy chỉnh", style=discord.ButtonStyle.secondary)
    async def timer_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="⌨️ Vui lòng nhập thời gian hẹn giờ (VD: 5 phút, 1 giờ, 30 p, 1.5 h):",
            embed=None, view=None
        )
        try:
            msg = await bot.wait_for(
                'message',
                check=lambda m: m.author.id == self.user_id and m.channel.id == interaction.channel_id,
                timeout=60
            )
            text = msg.content.lower().strip()
            match = re.match(TIME_PATTERN, text)
            if not match:
                await msg.channel.send(
                    "❌ Định dạng không hợp lệ!\nVui lòng nhập theo định dạng: <số> <đơn vị> (VD: 5 phút, 1 giờ).\n------------------------------------------------"
                )
                return
            value = float(match.group(1))
            unit = match.group(2)
            if unit in ['giờ', 'g', 'h']:
                seconds = int(value * 3600)
            else:
                seconds = int(value * 60)
            if seconds < 60 or seconds > 86400:
                await msg.channel.send("❌ Thời gian phải từ 1 phút đến 24 giờ!")
                return

            await self.set_timer(msg, seconds)
        except asyncio.TimeoutError:
            await interaction.channel.send("⏳ Đã hết thời gian nhập. Dùng !timer để thử lại.")

    async def set_timer(self, interaction: discord.Interaction, seconds: int):
        global timer_jobs
        if self.user_id in timer_jobs and timer_jobs[self.user_id].is_running():
            timer_jobs[self.user_id].cancel()
            logging.info(f"Hủy timer cũ cho user {self.user_id}")

        async def timer_task():
            await asyncio.sleep(seconds)
            device_states[self.device] = not device_states[self.device] 
            await interaction.channel.send(
                f"⏰ Hẹn giờ kết thúc! Thiết bị {self.device} đã {'bật' if device_states[self.device] else 'tắt'}."
            )
            if self.user_id in timer_jobs:
                del timer_jobs[self.user_id]

        timer_jobs[self.user_id] = bot.loop.create_task(timer_task())
        time_text = f"{seconds//60} phút" if seconds < 3600 else f"{seconds//3600} giờ"
        await interaction.channel.send(
            f"✅ Đã đặt hẹn giờ {time_text} cho thiết bị {self.device}. Sẽ {'bật' if not device_states[self.device] else 'tắt'} sau {time_text}."
        )

class TimerTimeSelectView(discord.ui.View):
    def __init__(self, device: str, action: bool):
        super().__init__(timeout=120) 
        self.device = device
        self.action = action
        logging.info(f"Initialized TimerTimeSelectView for device {self.device}, action {self.action}")

    @discord.ui.button(label="5 phút", style=discord.ButtonStyle.secondary)
    async def time_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        timer_id = f"{self.device}_{interaction.channel_id}_{int(time.time())}"
        task = asyncio.create_task(schedule_device_action(self.device, self.action, 5, interaction.channel_id))
        scheduled_tasks[timer_id] = task
        action_text = "bật" if self.action else "tắt"
        logging.info(f"Scheduled timer {timer_id} for {action_text} {self.device} in 5 minutes")
        await interaction.response.edit_message(
            content=f"✅ Đã hẹn giờ {action_text} {device_names[self.device]} sau 5 phút",
            embed=None,
            view=None
        )

    @discord.ui.button(label="10 phút", style=discord.ButtonStyle.secondary)
    async def time_10(self, interaction: discord.Interaction, button: discord.ui.Button):
        timer_id = f"{self.device}_{interaction.channel_id}_{int(time.time())}"
        task = asyncio.create_task(schedule_device_action(self.device, self.action, 10, interaction.channel_id))
        scheduled_tasks[timer_id] = task
        action_text = "bật" if self.action else "tắt"
        logging.info(f"Scheduled timer {timer_id} for {action_text} {self.device} in 10 minutes")
        await interaction.response.edit_message(
            content=f"✅ Đã hẹn giờ {action_text} {device_names[self.device]} sau 10 phút",
            embed=None,
            view=None
        )

    @discord.ui.button(label="15 phút", style=discord.ButtonStyle.secondary)
    async def time_15(self, interaction: discord.Interaction, button: discord.ui.Button):
        timer_id = f"{self.device}_{interaction.channel_id}_{int(time.time())}"
        task = asyncio.create_task(schedule_device_action(self.device, self.action, 15, interaction.channel_id))
        scheduled_tasks[timer_id] = task
        action_text = "bật" if self.action else "tắt"
        logging.info(f"Scheduled timer {timer_id} for {action_text} {self.device} in 15 minutes")
        await interaction.response.edit_message(
            content=f"✅ Đã hẹn giờ {action_text} {device_names[self.device]} sau 15 phút",
            embed=None,
            view=None
        )

    @discord.ui.button(label="Tùy chỉnh", style=discord.ButtonStyle.secondary)
    async def time_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        user_states[user_id] = {"state": "entering_timer", "device": self.device, "action": self.action}
        logging.info(f"User {user_id} entered custom timer mode for {self.device}")
        try:
            await interaction.response.send_message(
                content="⌨️ Vui lòng nhập thời gian hẹn giờ (VD: 5 phút, 1 giờ, 30 p, 1.5 h):",
                ephemeral=True 
            )
        except discord.errors.HTTPException as e:
            logging.error(f"Failed to send custom timer prompt for user {user_id}: {e}")
            await interaction.channel.send("❌ Không thể gửi yêu cầu nhập thời gian. Vui lòng thử lại.")
            return

        try:
            msg = await bot.wait_for(
                'message',
                check=lambda m: m.author.id == user_id and m.channel.id == interaction.channel_id,
                timeout=120
            )
            text = msg.content.lower().strip()
            logging.info(f"Received custom timer input from user {user_id}: {text}")
            match = re.match(TIME_PATTERN, text)
            if not match:
                logging.warning(f"Invalid timer format from user {user_id}: {text}")
                await msg.channel.send(
                    "❌ Định dạng không hợp lệ!\nVui lòng nhập theo định dạng: <số> <đơn vị> (VD: 5 phút, 1 giờ).\n------------------------------------------------"
                )
                return
            value = float(match.group(1))
            unit = match.group(2)
            if unit in ['giờ', 'g', 'h']:
                seconds = int(value * 3600)
            else:
                seconds = int(value * 60)
            if seconds < 60 or seconds > 86400:
                logging.warning(f"Timer out of range from user {user_id}: {seconds} seconds")
                await msg.channel.send("❌ Thời gian phải từ 1 phút đến 24 giờ!")
                return
            timer_id = f"{self.device}_{interaction.channel_id}_{int(time.time())}"
            task = asyncio.create_task(schedule_device_action(self.device, self.action, seconds // 60, interaction.channel_id))
            scheduled_tasks[timer_id] = task
            action_text = "bật" if self.action else "tắt"
            time_text = f"{seconds//60} phút" if seconds < 3600 else f"{seconds//3600} giờ"
            logging.info(f"Scheduled timer {timer_id} for {action_text} {self.device} in {time_text}")
            message = await msg.channel.send(
                f"✅ Đã hẹn giờ {action_text} {device_names[self.device]} sau {time_text}"
            )
            timer_messages[timer_id] = message.id
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for timer input from user {user_id}")
            await interaction.channel.send("⏳ Đã hết thời gian nhập. Dùng !timer để thử lại.")
        except discord.errors.HTTPException as e:
            logging.error(f"Failed to process custom timer input for user {user_id}: {e}")
            await interaction.channel.send("❌ Lỗi khi xử lý thời gian. Vui lòng thử lại.")
        finally:
            if user_id in user_states:
                logging.info(f"Clearing user state for {user_id}")
                del user_states[user_id]

    async def on_timeout(self):
        logging.info(f"Timeout for TimerTimeSelectView for device {self.device}")
        try:
            await self.message.edit(content="⏳ Bảng chọn thời gian đã hết hạn. Dùng !timer để thử lại.", view=None)
        except:
            pass

@bot.command()
async def cancel(ctx):
    user_id = ctx.author.id
    channel_id = str(ctx.channel.id)
    cancelled = False
    user_timers = [tid for tid in scheduled_tasks if f"_{channel_id}_" in tid]

    logging.info(f"scheduled_tasks before cancel: {scheduled_tasks}")
    logging.info(f"Found timers for channel {channel_id}: {user_timers}")

    if not user_timers:
        await ctx.send("❌ Không có hẹn giờ nào để hủy.\n------------------------------------------------")
        return

    try:
        for timer_id in user_timers[:]: 
            if timer_id in scheduled_tasks:
                task = scheduled_tasks[timer_id]
                task.cancel()
                try:
                    await task 
                    cancelled = True
                    logging.info(f"Cancelled timer {timer_id} for user {user_id}")
                    if timer_id in timer_messages:
                        try:
                            message = await ctx.channel.fetch_message(timer_messages[timer_id])
                            await message.edit(content=f"⏰ Hẹn giờ cho {device_names[timer_id.split('_')[0]]} đã bị hủy.")
                        except (discord.errors.NotFound, discord.errors.Forbidden) as e:
                            logging.warning(f"Error handling message for timer {timer_id}: {e}")
                        finally:
                            del timer_messages[timer_id]
                except asyncio.CancelledError:
                    pass
                finally:
                    if timer_id in scheduled_tasks:
                        del scheduled_tasks[timer_id]

        if cancelled:
            await ctx.send("✅ Đã hủy tất cả hẹn giờ của bạn trong kênh này.\n------------------------------------------------")
        else:
            await ctx.send("❌ Không tìm thấy hẹn giờ nào để hủy.\n------------------------------------------------")
    except Exception as e:
        logging.error(f"Error in cancel command for user {user_id}: {e}", exc_info=True)
        if cancelled:
            await ctx.send("✅ Đã hủy tất cả hẹn giờ của bạn trong kênh này.\n------------------------------------------------")
        else:
            await ctx.send("❌ Có lỗi xảy ra khi hủy hẹn giờ. Vui lòng thử lại.\n------------------------------------------------")

@bot.command()
async def predict(ctx):
    try:
        if not all([model, scaler, label_encoder]):
            await ctx.send("❌ Chức năng dự đoán không khả dụng do lỗi tải models")
            return

        sensor_data = get_latest_sensor_data()
        if not sensor_data:
            await ctx.send("❌ Không thể lấy dữ liệu cảm biến. Vui lòng thử lại sau.")
            return

        monthly_rainfall = get_last_month_rainfall()
        logging.info(f"Lượng mưa tháng trước: {monthly_rainfall}mm")

        input_data = pd.DataFrame([{
            'N': round(float(sensor_data['nitrogen']), 2),
            'P': round(float(sensor_data['phosphorus']), 2),
            'K': round(float(sensor_data['potassium']), 2),
            'temperature': round(float(sensor_data['temperature']), 2),
            'humidity': round(float(sensor_data['humidity']), 2),
            'ph': round(float(sensor_data['ph']), 2),
            'rainfall': monthly_rainfall
        }])

        scaled_data = scaler.transform(input_data)
        prediction = model.predict(scaled_data)
        crop_name = label_encoder.inverse_transform(prediction)[0].lower()
        crop_name_vi = CROP_TRANSLATIONS.get(crop_name, crop_name)
        crop_params = CROP_PARAMETERS.get(crop_name)

        if not crop_params:
            await ctx.send("❌ Không tìm thấy thông số cho cây trồng này.")
            return
            
        message = f"🌱 Cây trồng được khuyến nghị: {crop_name_vi}\n"

        warnings = []
        suggestions = []
        param_map = {
            'N': 'nitrogen',
            'P': 'phosphorus',
            'K': 'potassium',
            'temperature': 'temperature',
            'humidity': 'humidity',
            'ph': 'ph'
        }

        for param, value in input_data.iloc[0].items():
            mapped_param = param_map.get(param)
            if mapped_param in crop_params:
                ideal_range = crop_params[mapped_param]
                if value < ideal_range['min']:
                    warnings.append(f"⚠️ {SENSOR_TRANSLATIONS[mapped_param]} ({value}) thấp hơn mức tối thiểu ({ideal_range['min']})")
                    suggestions.append(f"🔼 Cần tăng {SENSOR_TRANSLATIONS[mapped_param]}")
                elif value > ideal_range['max']:
                    warnings.append(f"⚠️ {SENSOR_TRANSLATIONS[mapped_param]} ({value}) cao hơn mức tối đa ({ideal_range['max']})")
                    suggestions.append(f"🔻 Cần giảm {SENSOR_TRANSLATIONS[mapped_param]}")

        ideal_values = [
            f"{crop_params['temperature']['min']}-{crop_params['temperature']['max']}",
            f"{crop_params['humidity']['min']}-{crop_params['humidity']['max']}",
            f"{crop_params['nitrogen']['min']}-{crop_params['nitrogen']['max']}",
            f"{crop_params['phosphorus']['min']}-{crop_params['phosphorus']['max']}",
            f"{crop_params['potassium']['min']}-{crop_params['potassium']['max']}",
            f"{crop_params['ph']['min']}-{crop_params['ph']['max']}"
        ]
        max_width = max(len(v) for v in ideal_values)

        def pad_value(value, width):
            value_str = str(value)
            return value_str + ' ' * (width - len(value_str))

        table = (
            "THÔNG SỐ   LÝ TƯỞNG" + " " * (max_width - len("Lý tưởng")) + "   HIỆN TẠI\n"
            f"Nhiệt độ | {pad_value(ideal_values[0], max_width)}  | {input_data['temperature'].iloc[0]}°C\n"
            f"Độ ẩm    | {pad_value(ideal_values[1], max_width)}  | {input_data['humidity'].iloc[0]}%\n"
            f"Nitơ     | {pad_value(ideal_values[2], max_width)}  | {input_data['N'].iloc[0]}mg/kg\n"
            f"Phốt pho | {pad_value(ideal_values[3], max_width)}  | {input_data['P'].iloc[0]}mg/kg\n"
            f"Kali     | {pad_value(ideal_values[4], max_width)}  | {input_data['K'].iloc[0]}mg/kg\n"
            f"pH       | {pad_value(ideal_values[5], max_width)}  | {input_data['ph'].iloc[0]}\n"
        )
        message += f"```\n{table}\n```"

        if warnings:
            message += "⚠️ Cảnh báo:\n"
            for warning in warnings:
                message += f"• {warning}\n"
            message += "\n"

        if suggestions:
            message += "💡 Đề xuất:\n"
            for suggestion in suggestions:
                message += f"• {suggestion}\n"
            message += "------------------------------------------------"
        try:
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            image_path = None
            for ext in image_extensions:
                try_path = os.path.join("static", "img", "plants", f"{crop_name}{ext}")
                if os.path.exists(try_path):
                    image_path = try_path
                    break

            if image_path:
                file = discord.File(image_path)
                await ctx.send(file=file)
                await ctx.send(message)
            else:
                await ctx.send(message)
        except Exception as e:
            await ctx.send(message)
            logging.error(f"Lỗi khi gửi ảnh: {e}")

    except Exception as e:
        logging.error(f"Lỗi trong predict_crop: {e}")
        await ctx.send("❌ Có lỗi xảy ra. Vui lòng thử lại sau.")

@bot.command()
async def ask(ctx, *, question=None):
    if not question:
        await ctx.send("Vui lòng nhập câu hỏi sau lệnh !ask. Ví dụ: !ask Độ pH 6.5 có phù hợp với lúa không?")
        return

    user_id = ctx.author.id
    user_message = question
    manage_context(user_id, "user", user_message)

    message = await ctx.send("Đang xử lý câu hỏi của bạn... 🌱")
    response = await get_ai_response(user_id, user_message)
    await message.edit(content=response)

@bot.command()
async def subscribe(ctx):
    user_id = ctx.author.id
    username = ctx.author.name
    logging.info(f"Xử lý !subscribe cho user {user_id}")

    if user_id in discord_subscribed_users:
        await ctx.send("❌ Bạn đã đăng ký nhận thông báo.\nDùng !unsubscribe để hủy hoặc !change để thay đổi.\n------------------------------------------------")
        return

    try:
        discord_subscribed_users[user_id] = {
            'username': username,
            'channel_id': ctx.channel.id,
            'subscribed_at': datetime.now(VN_TZ),
            'interval': None
        }
        save_discord_subscribers()
        logging.info(f"Đã lưu user {user_id} vào discord_subscribed_users")

        embed = discord.Embed(title="🕒 Chọn khoảng thời gian nhận thông báo cảm biến", color=discord.Color.blue())
        view = IntervalSelectView(user_id=user_id)
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        logging.error(f"Lỗi trong subscribe cho user {user_id}: {e}", exc_info=True)
        await ctx.send("❌ Có lỗi xảy ra. Vui lòng thử lại sau.\n------------------------------------------------")

class IntervalSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)  
        self.user_id = user_id
        self.add_buttons()

    def add_buttons(self):
        # Nút 1 phút
        button_1m = discord.ui.Button(label="1 phút", style=discord.ButtonStyle.primary)
        button_1m.callback = self.interval_1m
        self.add_item(button_1m)
        # Nút 5 phút
        button_5m = discord.ui.Button(label="5 phút", style=discord.ButtonStyle.primary)
        button_5m.callback = self.interval_5m
        self.add_item(button_5m)
        # Nút 10 phút
        button_10m = discord.ui.Button(label="10 phút", style=discord.ButtonStyle.primary)
        button_10m.callback = self.interval_10m
        self.add_item(button_10m)
        # Nút tùy chỉnh
        button_custom = discord.ui.Button(label="Tùy chỉnh", style=discord.ButtonStyle.secondary)
        button_custom.callback = self.interval_custom
        self.add_item(button_custom)

    async def interval_1m(self, interaction: discord.Interaction):
        await self.set_interval(interaction, 60) 

    async def interval_5m(self, interaction: discord.Interaction):
        await self.set_interval(interaction, 300) 

    async def interval_10m(self, interaction: discord.Interaction):
        await self.set_interval(interaction, 600) 

    async def set_interval(self, interaction: discord.Interaction, seconds: int):
        try:
            discord_subscribed_users[self.user_id]['interval'] = seconds
            save_discord_subscribers()
            logging.info(f"Saved interval {seconds} seconds for user {self.user_id}")
            time_text = f"{seconds//60} phút"
            await interaction.response.send_message(
                f"✅ Bạn đã đăng ký nhận thông báo mỗi {time_text}.\nDùng !unsubscribe để hủy hoặc !change để thay đổi.\n------------------------------------------------"
            )
            await send_sensor_data_to_user(self.user_id, interaction.channel_id)
            await start_subscription_job(self.user_id, interaction.channel_id)
        except Exception as e:
            logging.error(f"Error setting interval for user {self.user_id}: {e}", exc_info=True)
            await interaction.response.send_message("❌ Có lỗi xảy ra. Vui lòng thử lại sau.\n------------------------------------------------")
        finally:
            if self.user_id in user_states:
                logging.info(f"Clearing user state for {self.user_id}")
                del user_states[self.user_id]

    async def interval_custom(self, interaction: discord.Interaction):
        user_states[self.user_id] = {"state": "entering_interval"}
        try:
            await interaction.response.send_message(
                "⌨️ Vui lòng nhập khoảng thời gian nhận thông báo (VD: 5 phút, 1 giờ, 30 p, 1.5 h):",
                ephemeral=True 
            )
            msg = await bot.wait_for(
                'message',
                check=lambda m: m.author.id == self.user_id and m.channel.id == interaction.channel_id,
                timeout=120  
            )
            text = msg.content.lower().strip()
            logging.info(f"Received custom interval input from user {self.user_id}: {text}")
            match = re.match(TIME_PATTERN, text)
            if not match:
                logging.warning(f"Invalid interval format from user {self.user_id}: {text}")
                await msg.channel.send(
                    "❌ Định dạng không hợp lệ!\nVui lòng nhập theo định dạng: <số> <đơn vị> (VD: 5 phút, 1 giờ).\n------------------------------------------------"
                )
                return
            value = float(match.group(1))
            unit = match.group(2)
            if unit in ['giờ', 'g', 'h']:
                seconds = int(value * 3600)
            else:
                seconds = int(value * 60)
            if seconds < 60 or seconds > 86400:
                logging.warning(f"Interval out of range from user {self.user_id}: {seconds} seconds")
                await msg.channel.send("❌ Khoảng thời gian phải từ 1 phút đến 24 giờ!")
                return

            discord_subscribed_users[self.user_id]['interval'] = seconds
            save_discord_subscribers()
            logging.info(f"Saved interval {seconds} seconds for user {self.user_id}")
            time_text = f"{seconds//60} phút" if seconds < 3600 else f"{seconds//3600} giờ"
            await msg.channel.send(
                f"✅ Bạn đã đăng ký nhận thông báo mỗi {time_text}.\nDùng !unsubscribe để hủy hoặc !change để thay đổi.\n------------------------------------------------"
            )
            await send_sensor_data_to_user(self.user_id, interaction.channel_id)
            await start_subscription_job(self.user_id, interaction.channel_id)
        except asyncio.TimeoutError:
            logging.warning(f"Timeout waiting for interval input from user {self.user_id}")
            await interaction.channel.send("⏳ Đã hết thời gian nhập. Dùng !change để thử lại.")
        except Exception as e:
            logging.error(f"Error in interval_custom for user {self.user_id}: {e}", exc_info=True)
            await interaction.channel.send("❌ Có lỗi xảy ra. Vui lòng thử lại sau.")
        finally:
            if self.user_id in user_states:
                logging.info(f"Clearing user state for {self.user_id}")
                del user_states[self.user_id]

    async def on_timeout(self):
        if self.user_id in user_states:
            logging.info(f"Timeout: Clearing user state for {self.user_id}")
            del user_states[self.user_id]

@bot.command()
async def change(ctx):
    user_id = ctx.author.id
    if user_id not in discord_subscribed_users:
        await ctx.send("❌ Bạn chưa đăng ký nhận thông báo.\nDùng !subscribe để đăng ký.\n------------------------------------------------")
        return
    if user_id in user_states:
        logging.info(f"Clearing existing user state for {user_id} before starting !change")
        del user_states[user_id]
    user_states[user_id] = {"state": "entering_interval"}
    logging.info(f"User {user_id} started !change command")
    embed = discord.Embed(
        title="🕒 Chọn khoảng thời gian mới để nhận thông báo cảm biến",
        description="Chọn một khoảng thời gian từ các nút bên dưới hoặc chọn 'Tùy chỉnh' để nhập thời gian khác.",
        color=discord.Color.blue()
    )
    view = IntervalSelectView(user_id=user_id)
    await ctx.send(embed=embed, view=view)

@bot.command()
async def unsubscribe(ctx):
    user_id = ctx.author.id
    if user_id not in discord_subscribed_users:
        await ctx.send("❌ Bạn chưa đăng ký nhận thông báo.\n------------------------------------------------")
        return
    if user_id in discord_subscription_jobs:
        discord_subscription_jobs[user_id].cancel()
        del discord_subscription_jobs[user_id]
    del discord_subscribed_users[user_id]
    save_discord_subscribers()
    await ctx.send("✅ Bạn đã hủy đăng ký nhận thông báo.\n------------------------------------------------")

@bot.command()
async def check(ctx):
    user_id = ctx.author.id
    if user_id in discord_subscribed_users:
        interval = discord_subscribed_users[user_id]['interval']
        time_text = f"{interval//60} phút" if interval < 3600 else f"{interval//3600} giờ"
        await ctx.send(
            f"✅ Bạn đang đăng ký nhận thông báo mỗi {time_text}.\nDùng !unsubscribe để hủy hoặc !change để thay đổi.\n------------------------------------------------"
        )
    else:
        await ctx.send("❌ Bạn chưa đăng ký nhận thông báo.\nDùng !subscribe để đăng ký.\n------------------------------------------------")
# Task cảnh báo nhiệt độ
@tasks.loop(seconds=30)
async def check_temperature_alert():
    try:
        global config, temperature_alert_settings
        config = load_config()
        temperature_alert_settings = config['temperature_alert']
        data = get_latest_sensor_data()
        if not data or 'temperature' not in data:
            logging.warning("❌ Không thể lấy dữ liệu nhiệt độ để kiểm tra cảnh báo")
            return
        current_temp = data['temperature']
        threshold = temperature_alert_settings['threshold']
        current_time = time.time()
        logging.info(f"🌡️ Kiểm tra cảnh báo - Nhiệt độ hiện tại: {current_temp}°C, Ngưỡng: {threshold}°C")
        if current_temp > threshold:
            logging.info("⚠️ Phát hiện nhiệt độ vượt ngưỡng!")
            if (temperature_alert_settings['last_alert_time'] is None or
                current_time - temperature_alert_settings['last_alert_time'] > temperature_alert_settings['alert_cooldown']):
                temperature_alert_settings['last_alert_time'] = current_time
                config['temperature_alert'] = temperature_alert_settings
                save_config(config)
                alert_message = (
                    f"⚠️ CẢNH BÁO NHIỆT ĐỘ ⚠️\n"
                    f"Nhiệt độ hiện tại ({current_temp:.1f}°C) đã vượt quá ngưỡng cảnh báo ({threshold:.1f}°C).\n"
                    f"⏰ Thời gian: {datetime.now(VN_TZ).strftime('%d/%m/%Y %H:%M:%S')}\n"
                    f"❗ Vui lòng kiểm tra hệ thống!\n"
                    f"------------------------------------------------"
                )
                if not discord_subscribed_users:
                    logging.warning("⚠️ Không có người dùng nào đăng ký nhận thông báo trên Discord")
                    return
                for user_id in list(discord_subscribed_users.keys()):
                    try:
                        channel = bot.get_channel(discord_subscribed_users[user_id]['channel_id'])
                        if channel is None:
                            logging.error(f"Không tìm thấy kênh với channel_id {discord_subscribed_users[user_id]['channel_id']} cho user {user_id}")
                            del discord_subscribed_users[user_id]
                            save_discord_subscribers()
                            continue
                        await channel.send(alert_message)
                        logging.info(f"✅ Đã gửi cảnh báo nhiệt độ đến người dùng {user_id}")
                    except Exception as e:
                        logging.error(f"❌ Lỗi khi gửi cảnh báo nhiệt độ đến người dùng {user_id}: {e}")
                        if user_id in discord_subscribed_users:
                            del discord_subscribed_users[user_id]
                            save_discord_subscribers()
            else:
                logging.info(f"⏳ Đang trong thời gian cooldown ({temperature_alert_settings['alert_cooldown']} giây)")
        else:
            logging.info("✅ Nhiệt độ trong ngưỡng cho phép")
    except Exception as e:
        logging.error(f"❌ Lỗi trong check_temperature_alert: {e}")

user_states = {}
# Xử lý mọi tin nhắn
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    user_id = message.author.id
    text = message.content.lower()

    try:
        if user_id in user_states and user_states[user_id]["state"] in ["entering_timer", "entering_interval"]:
            logging.info(f"Ignoring message from user {user_id} in state {user_states[user_id]['state']}: {text}")
            return

        if text.startswith('!'):
            logging.info(f"Processing command from user {user_id}: {text}")
            await bot.process_commands(message)
        else:
            logging.info(f"Processing non-command message from user {user_id}: {text}")
            if re.match(DEVICE_COMMANDS, text):
                logging.info(f"Processing device command from user {user_id}: {text}")
                if "bật" in text or "mở" in text:
                    action = True
                elif "tắt" in text or "đóng" in text:
                    action = False
                else:
                    await message.channel.send("❓ Vui lòng nhập lệnh bật/tắt thiết bị hợp lệ.")
                    return

                found = False
                for vn_name, device in command_map.items():
                    if vn_name in text:
                        found = True
                        if device_states[device] == action:
                            status_text = "bật" if action else "tắt"
                            await message.channel.send(f"{device_icons[device]} {device_names[device]} đang {status_text} rồi mà {status_text} gì nữa!")
                            return
                        result = control_device(device, action)
                        if result:
                            status_text = "bật" if action else "tắt"
                            await message.channel.send(f"{device_icons[device]} Đã {status_text} {device_names[device]}")
                        else:
                            await message.channel.send("❌ Không thể điều khiển thiết bị. Vui lòng thử lại sau.")
                        break
                if not found:
                    await message.channel.send("❓ Không nhận diện được thiết bị. Vui lòng thử lại.")
            else:
                logging.info(f"Processing AI query from user {user_id}: {text}")
                user_message = message.content.strip()
                manage_context(user_id, "user", user_message)
                
                thinking_msg = await message.channel.send("Đang xử lý câu hỏi của bạn... 🌱")
                response = await get_ai_response(user_id, user_message)
                response_with_line = response + "\n------------------------------------------------"
                await thinking_msg.edit(content=response_with_line)

    except Exception as e:
        logging.error(f"Error in on_message for user {user_id}: {e}", exc_info=True)
        await message.channel.send("❌ Có lỗi xảy ra. Vui lòng thử lại sau.")
# Chạy bot
bot.run(os.getenv("DISCORD_TOKEN")) # Đọc token từ .env