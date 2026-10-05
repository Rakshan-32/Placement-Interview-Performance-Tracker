import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.environ.get("BULK_UPLOAD_DB_PATH", os.path.join(ROOT_DIR, "database.db"))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Allowed extensions
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit

