import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

# Project Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Create data directory if it doesn't exist
os.makedirs(DATA_DIR, exist_ok=True)

# Configuration Variables
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DB_NAME = os.path.join(DATA_DIR, "database.db")

# Parse Admin IDs (comma-separated in .env)
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_raw:
    try:
        ADMIN_IDS = [int(aid.strip()) for aid in admin_ids_raw.split(",") if aid.strip()]
    except ValueError:
        print("Warning: ADMIN_IDS environment variable contains invalid integers.")

# DTM Rules configuration
# Standard distribution: Subject 1 = 16 Qs, Subject 2 = 17 Qs, Subject 3 = 17 Qs
TEST_QUESTION_DISTRIBUTION = [16, 17, 17]
TOTAL_QUESTIONS = sum(TEST_QUESTION_DISTRIBUTION)
