from typing import List, Dict

# NOTE: in-memory store for now; replace with DB later
_INTENTS: List[Dict] = []

def add_intent(d: Dict) -> Dict:
    _INTENTS.append(d)
    return d

def list_intents(limit: int = 50):
    return list(reversed(_INTENTS))[:limit]
