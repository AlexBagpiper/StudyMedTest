import json
from datetime import datetime

def debug_log(hypothesis_id, message, data=None):
    log_path = r"e:\pythonProject\StudyMedTest\.cursor\debug.log"
    log_entry = {
        "sessionId": "debug-session",
        "timestamp": datetime.now().isoformat(),
        "hypothesisId": hypothesis_id,
        "location": "test_log.py",
        "message": message,
        "data": data or {}
    }
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
        print(f"Log written to {log_path}")
    except Exception as e:
        print(f"Failed to write log: {e}")

if __name__ == "__main__":
    debug_log("H0", "Test log message")
