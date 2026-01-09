import sqlite3
import time
from awsiot import mqtt_connection_builder
from awscrt import mqtt

# ------------------ AWS MQTT CONNECTION ------------------
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "BrakePressurePi"
TOPIC = "brake/pressure"

mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=ENDPOINT,
    cert_filepath="Brake_Pressure_sensor.cert.pem",
    pri_key_filepath="Brake_Pressure_sensor.private.key",
    client_id=CLIENT_ID,
    ca_filepath="AmazonRootCA1.pem",
    clean_session=False,
    keep_alive_secs=30
)

mqtt_connection.connect().result()
print("Connected to AWS IoT Core")

# ------------------ DATABASE SETUP ------------------
DB_PATH = "project.db"
time.sleep(10)

# Connect to SQLite
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row  # So we can use row["column_name"]
cursor = conn.cursor()

# Dummy upload function (replace with real API call)
def upload_to_app(row):
    try:
        print(
            f"Uploading -> BP:{row['bp_pressure']} | FP:{row['fp_pressure']} | "
            f"CR:{row['cr_pressure']} | BC:{row['bc_pressure']} | Time:{row['created_at']}"
        )
        # Simulate successful upload
        return True
    except Exception as e:
        print("Upload failed:", e)
        return False

while True:
    # Select only rows that are not uploaded yet
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        success = upload_to_app(row)
        if success:
            # Mark row as uploaded
            cursor.execute("""
                UPDATE brake_pressure_log
                SET uploaded = 1
                WHERE id = ?
            """, (row["id"],))
            conn.commit()
            print("Uploaded and marked as done ✅")
    else:
        print("No pending rows to upload.")
    
    time.sleep(5)
