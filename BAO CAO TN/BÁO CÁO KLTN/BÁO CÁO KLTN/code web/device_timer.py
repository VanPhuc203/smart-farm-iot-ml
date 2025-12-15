import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import pytz
import traceback

from dotenv import load_dotenv
load_dotenv()
MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")

vn_tz = pytz.timezone('Asia/Ho_Chi_Minh')

class DeviceTimer:
    def __init__(self, mqtt_client):
        self.timers: Dict[str, Dict] = {}
        self.tasks: Dict[str, asyncio.Task] = {}
        self.mqtt_client = mqtt_client
        self.load_timers()

    def load_timers(self):
        """Load timers from file"""
        try:
            with open('device_timers.json', 'r') as f:
                self.timers = json.load(f)
        except FileNotFoundError:
            self.timers = {}

    def save_timers(self):
        """Save timers to file"""
        with open('device_timers.json', 'w') as f:
            json.dump(self.timers, f)

    def set_timer(self, device: str, on_datetime: str, off_datetime: str, daily: bool = False) -> bool:
        """Set timer for a device"""
        try:
            timer = {
                'on_datetime': on_datetime,
                'off_datetime': off_datetime,
                'daily': daily,
                'enabled': True
            }
            self.timers[device] = timer
            self.save_timers()
            self.start_timer_task(device)
            return True
        except Exception as e:
            print(f"Error setting timer: {str(e)}")
            return False

    def start_timer_task(self, device: str):
        """Start timer task for a device"""
        if device in self.tasks:
            self.tasks[device].cancel()

        self.tasks[device] = asyncio.create_task(self._timer_loop(device))

    async def _timer_loop(self, device: str):
        """Timer loop for a device"""
        while True:
            try:
                timer = self.timers.get(device)
                if not timer or not timer['enabled']:
                    print(f"[TIMER] No active timer found for {device}")
                    break

                now = datetime.now(vn_tz)
                on_dt = datetime.fromisoformat(timer['on_datetime']).astimezone(vn_tz)
                off_dt = datetime.fromisoformat(timer['off_datetime']).astimezone(vn_tz)

                print(f"[TIMER] Detailed check for {device}:")
                print(f"  Current time: {now}")
                print(f"  On time: {on_dt}")
                print(f"  Off time: {off_dt}")
                print(f"  Daily mode: {timer['daily']}")

                if timer['daily']:
                    current_time = now.time()
                    on_time = on_dt.time()
                    off_time = off_dt.time()
                    
                    print(f"  Current time (HH:MM): {current_time.hour}:{current_time.minute}")
                    print(f"  On time (HH:MM): {on_time.hour}:{on_time.minute}")
                    print(f"  Off time (HH:MM): {off_time.hour}:{off_time.minute}")
                    
                    if current_time.hour == on_time.hour and current_time.minute == on_time.minute:
                        print(f"  [ACTION] Turning ON {device} (daily schedule)")
                        await self._control_device(device, True)
                    if current_time.hour == off_time.hour and current_time.minute == off_time.minute:
                        print(f"  [ACTION] Turning OFF {device} (daily schedule)")
                        await self._control_device(device, False)
                else:
                    print(f"  Time until ON: {(on_dt - now).total_seconds()} seconds")
                    print(f"  Time until OFF: {(off_dt - now).total_seconds()} seconds")
                    
                    if now >= on_dt and now <= on_dt + timedelta(minutes=1):
                        print(f"  [ACTION] Turning ON {device} (one-time schedule)")
                        await self._control_device(device, True)
                    if now >= off_dt and now <= off_dt + timedelta(minutes=1):
                        print(f"  [ACTION] Turning OFF {device} (one-time schedule)")
                        await self._control_device(device, False)
                        print(f"  [ACTION] Clearing timer for {device}")
                        self.clear_timer(device)
                        break

                print(f"[TIMER] Next check in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[TIMER] Error in timer loop: {str(e)}")
                print(f"[TIMER] Stack trace: {traceback.format_exc()}")
                await asyncio.sleep(5)

    async def _control_device(self, device_id: str, status: bool):
        """Điều khiển thiết bị thông qua MQTT"""
        try:
            if not self.mqtt_client.is_connected:
                print(f"❌ MQTT chưa kết nối, thử kết nối lại trước khi điều khiển thiết bị {device_id}...")
                try:
                    await self.mqtt_client.connect()
                except Exception as e:
                    print(f"❌ Không thể kết nối lại MQTT: {str(e)}")
                    return False
                
                if not self.mqtt_client.is_connected:
                    print(f"❌ Không thể điều khiển thiết bị {device_id}: MQTT vẫn chưa kết nối")
                    return False

            success = self.mqtt_client.control_device(device_id, status)
            if not success:
                print(f"❌ Không thể điều khiển thiết bị {device_id}")
                return False

            print(f"✅ Đã điều khiển thiết bị {device_id} thành {'BẬT' if status else 'TẮT'}")
            return True

        except Exception as e:
            print(f"❌ Lỗi điều khiển thiết bị {device_id}: {str(e)}")
            return False

    def clear_timer(self, device: str):
        """Clear timer for a device"""
        if device in self.tasks:
            self.tasks[device].cancel()
            del self.tasks[device]
        
        if device in self.timers:
            del self.timers[device]
            self.save_timers()

    def get_timer(self, device: str) -> Optional[Dict]:
        """Get timer for a device"""
        return self.timers.get(device)