import os
import tempfile


TEST_DIR = tempfile.gettempdir()
ROOT_TEST_DB = os.path.join(TEST_DIR, f"placement_tracker_root_{os.getpid()}.db")
BULK_TEST_DB = os.path.join(TEST_DIR, f"placement_tracker_bulk_{os.getpid()}.db")

for test_db in (ROOT_TEST_DB, BULK_TEST_DB):
    if os.path.exists(test_db):
        os.remove(test_db)

os.environ["DATABASE_URL"] = f"sqlite:///{ROOT_TEST_DB.replace(os.sep, '/')}"
os.environ["BULK_UPLOAD_DB_PATH"] = BULK_TEST_DB
