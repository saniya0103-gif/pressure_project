import sqlite3
import time
import sys

# ADS1115 imports
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "project.db"
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

#--I2C + ADS1115--
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

bp_channel = AnalogIn(ads, 0)
fp_channel = AnalogIn(ads, 1)
cr_channel = AnalogIn(ads, 2)
bc_channel = AnalogIn(ads, 3)

# SENSOR FUNCTIONS

def generate_raw_sensors():
    """
    Reads raw ADC values from ADS1115
    """
    return (
        bp_channel.value,
        fp_channel.value,
        cr_channel.value,
        bc_channel.value
    )

def convert_to_pressure(raw_value):
    """
    Converts ADC value to pressure (0–10 bar)
    ADS1115 range: 0–32767
    """
    return round((raw_value / 32767) * 10, 2)

def generate_pressures():
    raw = generate_raw_sensors()
    return tuple(convert_to_pressure(r) for r in raw)

# MAIN LOOP 

while True:
    new_pressures = generate_pressures()

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

        print(
            f"Inserted -> BP:{new_pressures[0]} | FP:{new_pressures[1]} | "
            f"CR:{new_pressures[2]} | BC:{new_pressures[3]} | "
            f"Time:{time.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True
        )
    else:
        print("No significant change, skipping...", flush=True)

    time.sleep(20)
