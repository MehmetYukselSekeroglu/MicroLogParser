import sys
from datetime import datetime

def _get_timestamp():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def p_info(message):
    print(f"[INFO] {_get_timestamp()} - {message}", file=sys.stdout)

def p_error(message):
    print(f"[ERROR] {_get_timestamp()} - {message}", file=sys.stderr)

def p_warn(message):
    print(f"[WARN] {_get_timestamp()} - {message}", file=sys.stderr)

def p_log(message):
    print(f"[LOG] {_get_timestamp()} - {message}", file=sys.stdout)

def p_title(title):
    print(f"\n--- {title} ---\n", file=sys.stdout) 