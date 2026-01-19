import sqlite3
import time
import sys
import os

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- DATABASE ----------------
# Docker-safe path
DB_FOLDER = "/app/db"               # Must match your docker-compose volume
DB_PATH = os.path.join(DB_FOLDER, "project.db")

# Ensure folder exists
os.makedirs(DB_FOLDER, exist_ok=True)

# Connect to database
try:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    print(f"✅ Database connected: {DB_PATH}", flush=True)
except Exception as e:
    print(f"❌ Failed to connect to database: {e}", flush=True)
    sys.exit(1)

# Create table if it doesn't exist
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

    # Pi 5 compatibility
    os.environ["BLINKA_FORCEBOARD"] = "RASPBERRY_PI_5"
    os.environ["BLINKA_FORCECHIP"] = "BCM2712"
    os.environ["BLINKA_USE_LGPIO"] = "1"

    # Initialize I2C and ADS1115
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp_channel = AnalogIn(ads, 0)
    fp_channel = AnalogIn(ads, 1)
    cr_channel = AnalogIn(ads, 2)
    bc_channel = AnalogIn(ads, 3)

    print("✅ ADS1115 initialized successfully", flush=True)

except Exception as e:
    ADS_AVAILABLE = False
    print("❌ ADS1115 init failed:", e, flush=True)

# ---------------- SENSOR FUNCTIONS ----------------
def read_raw_values():
    if ADS_AVAILABLE:
        return bp_channel.value, fp_channel.value, cr_channel.value, bc_channel.value
    else:
        return 0, 0, 0, 0

def convert_to_pressure(raw):
    # Convert raw ADC value (0–32767) to 0–10 bar
    return round((raw / 32767) * 10, 2)

def get_pressures():
    raw = read_raw_values()
    pressures = tuple(convert_to_pressure(r) for r in raw)
    return raw, pressures

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Logging every 20 seconds\n", flush=True)

while True:
    raw_values, pressures = get_pressures()

    # Fetch last logged values
    cursor.execute("""
        SELECT bp_pressure, fp_pressure, cr_pressure, bc_pressure
        FROM brake_pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    # Insert only if first reading or any sensor changes >= 0.5 bar
    if not last or any(abs(n - l) >= 0.5 for n, l in zip(pressures, last)):
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?)
        """, pressures)
        conn.commit()

    # Print RAW and converted pressures
    print(
        f"RAW: BP={raw_values[0]} FP={raw_values[1]} CR={raw_values[2]} BC={raw_values[3]}\n"
        f"BAR: BP={pressures[0]} FP={pressures[1]} CR={pressures[2]} BC={pressures[3]}\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "----------------------------------",
        flush=True
    )

    time.sleep(20)
