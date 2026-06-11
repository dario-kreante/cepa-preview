from sqlalchemy import text

from app.db.session import get_db


def test_get_db_entrega_una_sesion_funcional():
    gen = get_db()
    db = next(gen)
    try:
        assert db.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        gen.close()
