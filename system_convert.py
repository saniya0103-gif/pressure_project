import sqlite3
import time
import os
import sys

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- DYNAMIC DB PATH ----------------
# Use /app/db if exists, else fallback to local ./db folder
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_PATH, "db")

# Ensure the folder exists and is writable
os.makedirs(DB_FOLDER, exist_ok=True)
DB_PATH = os.path.join(DB_FOLDER, "project.db")

# Debug
print("Database folder:", DB_FOLDER)
print("Database file:", DB_PATH)

# ---------------- DATABASE SETUP ----------------
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

# ---------------- SENSOR SETUP ----------------
# Replace with your actual ADS1115 sensor code if needed
# For now, dummy values will allow it to run
def read_raw_values():
    return (0, 0, 0, 0)

def convert_to_pressure(raw):
    return round((raw / 32767) * 10, 2)

def get_pressures():
    raw = read_raw_values()
    pressures = tuple(convert_to_pressure(r) for r in raw)
    return raw, pressures

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Logging data every 20 seconds\n")

while True:
    raw_values, pressures = get_pressures()

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
        f"RAW VALUES\n"
        f"BP:{raw_values[0]} | FP:{raw_values[1]} | "
        f"CR:{raw_values[2]} | BC:{raw_values[3]}\n"
        f"PRESSURE VALUES\n"
        f"BP:{pressures[0]} bar | FP:{pressures[1]} bar | "
        f"CR:{pressures[2]} bar | BC:{pressures[3]} bar\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "---------------------------------------------",
        flush=True
    )

    time.sleep(20)
