import sqlite3
import time
import os
import sys

# ---------------- ENCODING SETUP ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- DYNAMIC PATHS ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_PATH, "db")
DB_PATH = os.path.join(DB_FOLDER, "project.db")

os.makedirs(DB_FOLDER, exist_ok=True)

print(f"Database file: {DB_PATH}", flush=True)

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
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

# ---------------- ADS1115 SETUP ----------------
ADS_AVAILABLE = True

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp_channel = AnalogIn(ads, ADS.P0)
    fp_channel = AnalogIn(ads, ADS.P1)
    cr_channel = AnalogIn(ads, ADS.P2)
    bc_channel = AnalogIn(ads, ADS.P3)

    print("✅ ADS1115 detected", flush=True)

except Exception as e:
    ADS_AVAILABLE = False
    print("ADS1115 NOT detected — data logging disabled", flush=True)

# ---------------- SENSOR FUNCTIONS ----------------
def read_pressures():
    if not ADS_AVAILABLE:
        return None

    def conv(raw):
        return round((raw / 32767.0) * 10, 2)

    pressures = (
        conv(bp_channel.value),
        conv(fp_channel.value),
        conv(cr_channel.value),
        conv(bc_channel.value)
    )

    # Ignore invalid zero-only readings
    if all(p == 0.0 for p in pressures):
        return None

    return pressures

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Logging every 10 seconds\n", flush=True)

while True:
    pressures = read_pressures()

    if pressures is None:
        print("Skipping invalid reading", flush=True)
        time.sleep(10)
        continue

    cursor.execute("""
        SELECT bp_pressure, fp_pressure, cr_pressure, bc_pressure
        FROM brake_pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchall()

    should_insert = False

    if not last:
        should_insert = True
    else:
        last_values = tuple(last)
        if any(abs(n - l) >= 0.5 for n, l in zip(pressures, last_values)):
            should_insert = True

    if should_insert:
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?)
        """, pressures)
        conn.commit()

        print(
            f"INSERTED → BP:{pressures[0]} | FP:{pressures[1]} | "
            f"CR:{pressures[2]} | BC:{pressures[3]} | "
            f"{time.strftime('%Y-%m-%d %H:%M:%S')}",
            flush=True
        )
    else:
        print("No significant change → skipped", flush=True)

    time.sleep(10)
