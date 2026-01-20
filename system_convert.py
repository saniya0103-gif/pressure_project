import os
import sys
import time
import sqlite3

# ---------------- ENCODING SETUP ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- PATH SETUP ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_PATH, "db")
DB_PATH = os.path.join(DB_FOLDER, "project.db")

print(f"Database folder: {DB_FOLDER}", flush=True)
print(f"Database file: {DB_PATH}", flush=True)

os.makedirs(DB_FOLDER, exist_ok=True)

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
ADS_AVAILABLE = False

# Force Blinka to use RPi.GPIO in case lgpio fails
os.environ["BLINKA_FORCECHIP"] = "BCM2712"
os.environ["BLINKA_FORCEBOARD"] = "RASPBERRY_PI_5"
os.environ["BLINKA_USE_RPI_GPIO"] = "1"

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp_channel = AnalogIn(ads, 0)
    fp_channel = AnalogIn(ads, 1)
    cr_channel = AnalogIn(ads, 2)
    bc_channel = AnalogIn(ads, 3)

    ADS_AVAILABLE = True
    print("✅ ADS1115 CONNECTED and initialized", flush=True)

except Exception as e:
    print(f"❌ ADS1115 NOT CONNECTED: {e}", flush=True)
    # Use dummy channels that return 0 if ADS is not available
    class DummyChannel:
        @property
        def value(self):
            return 0
        @property
        def voltage(self):
            return 0.0
    bp_channel = fp_channel = cr_channel = bc_channel = DummyChannel()

# ---------------- SENSOR FUNCTIONS ----------------
def read_raw_values():
    return (
        bp_channel.value,
        fp_channel.value,
        cr_channel.value,
        bc_channel.value
    )

def convert_to_pressure(raw):
    # Convert raw ADC value to pressure (assuming 16-bit ADC)
    return round((raw / 32767) * 10, 2) if raw else 0

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Logging data every 10 seconds\n", flush=True)

while True:
    raw = read_raw_values()
    pressures = tuple(convert_to_pressure(r) for r in raw)

    # Check last DB entry to avoid duplicates
    cursor.execute("""
        SELECT bp_pressure, fp_pressure, cr_pressure, bc_pressure
        FROM brake_pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    if not last or any(abs(n - l) >= 0.5 for n, l in zip(pressures, last)):
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?)
        """, pressures)
        conn.commit()

    print(
        f"ADS STATUS: {'CONNECTED' if ADS_AVAILABLE else 'NOT CONNECTED'}\n"
        f"RAW VALUES\n"
        f"BP:{raw[0]} | FP:{raw[1]} | CR:{raw[2]} | BC:{raw[3]}\n"
        f"PRESSURE VALUES\n"
        f"BP:{pressures[0]} bar | FP:{pressures[1]} bar | "
        f"CR:{pressures[2]} bar | BC:{pressures[3]} bar\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "---------------------------------------------",
        flush=True
    )

    time.sleep(10)
