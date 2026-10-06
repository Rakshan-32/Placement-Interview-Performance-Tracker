import db
from bulk_upload_module import parser


def parse_drive(content, filename):
    return parser.parse_drive_records(content, filename)


def parse_user_access(content, filename, default_role):
    return parser.parse_user_access_records(content, filename, default_role=default_role)


def parse_student_roster(content, filename):
    return parser.parse_student_roster_records(content, filename)


def parse_company_drives(content, filename):
    return parser.parse_company_drives_records(content, filename)


def record_failure(upload_type, filename, error):
    db.record_upload_log(upload_type, filename, 0, 0, 0, status=f"FAILED: {error}")
