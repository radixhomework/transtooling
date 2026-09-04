"""
Limitation simple des tentatives de connexion par identifiant, en mémoire.

Suffisant pour une instance unique de backend (pas de scale horizontal
prévu pour ce service). Si le backend venait à être répliqué, cette logique
devrait être déplacée vers un stockage partagé (ex. Redis).
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 minutes

_failed_attempts: dict[str, list[float]] = defaultdict(list)


def is_locked_out(login: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed_attempts[login] if now - t < LOCKOUT_SECONDS]
    _failed_attempts[login] = attempts
    return len(attempts) >= MAX_ATTEMPTS


def register_failed_attempt(login: str) -> None:
    _failed_attempts[login].append(time.time())


def reset_attempts(login: str) -> None:
    _failed_attempts.pop(login, None)
