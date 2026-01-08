import sqlite3
import time
import sys
import json
import paho.mqtt.client as mqtt

# ADS1115 imports
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

sys.stdout.reconfigure(encoding='utf-8')

# ---------------- DATABASE SETUP
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bp_pressure REAL,
    fp_pressure REAL,
    cr_pressure REAL,
    bc_pressure REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- I2C + ADS1115 SETUP 
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# ---------------- MQTT SETUP ----------------
MQTT_BROKER = "b32b74b949854cbca498f48f9627cb39.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "project/brake_pressure"

mqtt_client = mqtt.Client(
    client_id="RaspberryPi_Pressure",
    protocol=mqtt.MQTTv311
)

mqtt_client.username_pw_set(
    "Saniya_p",      # from HiveMQ Access Management
    "Saniya@9786"       # from HiveMQ Access Management
)

mqtt_client.tls_set()
result = mqtt_client.connect(MQTT_BROKER, MQTT_PORT)
print("MQTT connect result:", result)

mqtt_client.loop_start()

# ---------------- ADC CHANNEL SETUP ----------------
bp_channel = AnalogIn(ads, 0)
fp_channel = AnalogIn(ads, 1)
cr_channel = AnalogIn(ads, 2)
bc_channel = AnalogIn(ads, 3)

# ---------------- SENSOR FUNCTIONS ----------------
def generate_raw_sensors():
    return (
        bp_channel.value,
        fp_channel.value,
        cr_channel.value,
        bc_channel.value
    )

def convert_to_pressure(raw_value):
    return round((raw_value / 32767) * 10, 2)

def generate_pressures():
    raw = generate_raw_sensors()
    pressures = tuple(convert_to_pressure(r) for r in raw)
    return raw, pressures

# ---------------- MAIN LOOP ----------------
while True:
    raw_values, new_pressures = generate_pressures()

    cursor.execute("""
        SELECT bp_pressure, fp_pressure, cr_pressure, bc_pressure
        FROM brake_pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    if not last or any(abs(n - l) >= 0.5 for n, l in zip(new_pressures, last)):
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?)
        """, new_pressures)
        conn.commit()

        mqtt_data = {
            "bp": new_pressures[0],
            "fp": new_pressures[1],
            "cr": new_pressures[2],
            "bc": new_pressures[3],
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        mqtt_client.publish(MQTT_TOPIC, json.dumps(mqtt_data), qos=1)
        print("MQTT Published:", mqtt_data)

        print(
            f"RAW -> BP:{raw_values[0]} | FP:{raw_values[1]} | "
            f"CR:{raw_values[2]} | BC:{raw_values[3]}\n"
            f"PRESSURE -> BP:{new_pressures[0]} bar | "
            f"FP:{new_pressures[1]} bar | "
            f"CR:{new_pressures[2]} bar | "
            f"BC:{new_pressures[3]} bar | "
            f"Time:{time.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True
        )
    else:
        print("No significant change, skipping...", flush=True)

    time.sleep(20)
