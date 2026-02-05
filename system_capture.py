import time
import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

RAW_THRESHOLD = 1638
SENSOR_ID = "RPI_BP_01"
DB_PATH = "pressure_data.db"
READ_INTERVAL = 10

# DATABASE
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT,
    bp_raw INTEGER,
    fp_raw INTEGER,
    cr_raw INTEGER,
    bc_raw INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ADS1115 SETUP
ADS_AVAILABLE = True
try:
    import board, busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp = AnalogIn(ads, 0)
    fp = AnalogIn(ads, 1)
    cr = AnalogIn(ads, 2)
    bc = AnalogIn(ads, 3)

except Exception:
    ADS_AVAILABLE = False

def read_raw():
    if ADS_AVAILABLE:
        return (bp.value, fp.value, cr.value, bc.value)
    return (0, 0, 0, 0)

# ---------------- MAIN LOOP ----------------
print("System started...\n", flush=True)

while True:
    current = read_raw()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    print(
        f"RAW VALUES | BP:{current[0]} FP:{current[1]} "
        f"CR:{current[2]} BC:{current[3]} | {timestamp}",
        flush=True
    )

    # 🔹 Get last DB record
    cursor.execute("""
        SELECT bp_raw, fp_raw, cr_raw, bc_raw
        FROM pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    upload = False

    if last is None:
        upload = True
    else:
        diffs = [abs(current[i] - last[i]) for i in range(4)]
        if any(d >= RAW_THRESHOLD for d in diffs):
            upload = True

    if upload:
        cursor.execute("""
            INSERT INTO pressure_log
            (sensor_id, bp_raw, fp_raw, cr_raw, bc_raw)
            VALUES (?, ?, ?, ?, ?)
        """, (SENSOR_ID, *current))
        conn.commit()
        print("Inseting to database\n", flush=True)
    else:
        print("⏭ No change ≥ threshold → Skipped upload\n", flush=True)

    time.sleep(READ_INTERVAL)
