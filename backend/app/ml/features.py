import json

def payload_size(payload_str: str | None) -> int:
    if not payload_str:
        return 0
    return len(payload_str)

def make_features(job_type: str, priority: int, attempts: int, payload_str: str | None):
    # Simple numeric features + job_type as raw label (encoded later)
    return {
        "type": job_type,
        "priority": priority,
        "attempts": attempts,
        "payload_size": payload_size(payload_str),
    }