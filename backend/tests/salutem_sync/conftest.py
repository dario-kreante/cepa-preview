from datetime import datetime, timezone

import pytest

from app.services.salutem_sync.ritmo import Ritmo
from tests.salutem_falso import SalutemFalso

# 12:00 en Santiago (UTC-3 en septiembre).
AHORA = datetime(2026, 9, 16, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def salutem() -> SalutemFalso:
    return SalutemFalso()


@pytest.fixture
def ritmo() -> Ritmo:
    """Sin límite de frecuencia ni esperas reales."""
    return Ritmo(0, dormir=lambda segundos: None)
