import sqlite3
import time
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")

# ---------------- DATABASE ----------------
DB_PATH = os.path.join(os.path.dirname(__file__), "db", "project.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# ---------------- ADS1115 ----------------
ADS_AVAILABLE = True
try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp = AnalogIn(ads, ADS.P0)
    fp = AnalogIn(ads, ADS.P1)
    cr = AnalogIn(ads, ADS.P2)
    bc = AnalogIn(ads, ADS.P3)

    print("✅ ADS1115 initialized")

except Exception as e:
    ADS_AVAILABLE = False
    print("❌ ADS1115 init failed:", e)

# ---------------- FUNCTIONS ----------------
def raw_values():
    if not ADS_AVAILABLE:
        return (0, 0, 0, 0)
    return bp.value, fp.value, cr.value, bc.value

def to_bar(raw):
    return round((raw / 32768.0) * 10.0, 2)

# ---------------- LOOP ----------------
print("\nSystem started... Logging every 5 seconds\n")

while True:
    raw = raw_values()
    pressure = tuple(to_bar(r) for r in raw)

    cursor.execute("""
        INSERT INTO brake_pressure_log
        (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
        VALUES (?, ?, ?, ?)
    """, pressure)
    conn.commit()

    print(
        f"RAW: {raw}\n"
        f"BAR: BP={pressure[0]} FP={pressure[1]} "
        f"CR={pressure[2]} BC={pressure[3]}\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "----------------------------------",
        flush=True
    )

    time.sleep(5)
