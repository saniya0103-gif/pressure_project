import os
import time
import sys

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding="utf-8")

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- CERTIFICATE FOLDER ----------------
CERT_DIR = os.path.join(BASE_DIR, "raspi")

# ---------------- CERTIFICATE FILE NAMES ----------------
PRIVATE_KEY = "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-private.pem.key"
CERT_FILE  = "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt"
ROOT_CA    = "AmazonRootCA1.pem"

KEY_PATH  = os.path.join(CERT_DIR, PRIVATE_KEY)
CERT_PATH = os.path.join(CERT_DIR, CERT_FILE)
CA_PATH   = os.path.join(CERT_DIR, ROOT_CA)

# ---------------- FILE CHECK ----------------
def check_file(name, path):
    if not os.path.isfile(path):
        print(f"❌ {name} not found")
        print(f"   Path: {path}")
        sys.exit(1)
    print(f"✅ {name} OK")

check_file("PRIVATE KEY", KEY_PATH)
check_file("CERTIFICATE", CERT_PATH)
check_file("ROOT CA", CA_PATH)

print("✅ All certificates loaded successfully\n")

# ---------------- MAIN LOOP ----------------
def get_pending_rows():
    # DB logic remains SAME
    return []

print("🚀 Pressure uploader started")

while True:
    rows = get_pending_rows()

    if not rows:
        print("⏳ No pending rows. Waiting...")
        time.sleep(5)   # IMPORTANT (prevents exit 137)
        continue

    for row in rows:
        print("📤 Uploading:", row)
        # upload logic unchanged

    time.sleep(1)
