import json
from datetime import datetime, timezone

def read_state_file(file_path):
    """Reads a state file and returns its content, or an empty string if not found."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {file_path}"
    except Exception as e:
        return f"Error reading {file_path}: {e}"

def run_perch_cycle():
    """
    Simulates a single "perch" cycle for Thoth.

    1. Reads key state files.
    2. Formulates a thought based on the current state.
    3. Logs the thought to a dedicated perch log file.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # 1. Read state files
    today_content = read_state_file('state/today.md')
    inbox_content = read_state_file('state/inbox.md')
    commitments_content = read_state_file('state/commitments.md')

    # 2. Formulate a thought
    thought = {
        "type": "perch_thought",
        "timestamp": timestamp,
        "summary": "Perch cycle executed. Reviewing current state.",
        "state_review": {
            "today": today_content.strip(),
            "inbox": inbox_content.strip(),
            "commitments": commitments_content.strip()
        }
    }

    # 3. Log the thought
    log_entry = json.dumps(thought)
    try:
        with open('logs/perch_log.jsonl', 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
        print(f"Successfully logged perch thought at {timestamp}")
    except Exception as e:
        print(f"Error writing to perch_log.jsonl: {e}")

if __name__ == "__main__":
    run_perch_cycle()
