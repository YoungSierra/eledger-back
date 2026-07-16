"""
Restablece la contraseña de un usuario en adm_usuario.

Uso (desde backend/, con el venv):
    python reset_password.py <email> <nueva_contrasena>

Ejemplo:
    python reset_password.py youngsierra@emperadorsoluciones.co "MiClaveNueva123"

Reutiliza el mismo hash bcrypt (app.core.security.hash_password) y la
misma sesion de BD (app.core.database.SessionLocal) que usa el sistema,
por lo que el hash resultante es indistinguible de uno generado en la app.
"""
import sys

from sqlalchemy import func

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.admin import AdmUsuario


def main() -> int:
    if len(sys.argv) != 3:
        print("Uso: python reset_password.py <email> <nueva_contrasena>")
        return 1

    email = sys.argv[1].strip().lower()
    nueva = sys.argv[2]

    if len(nueva) < 5:
        print("La contrasena debe tener al menos 5 caracteres.")
        return 1

    db = SessionLocal()
    try:
        usuario = (
            db.query(AdmUsuario)
            .filter(func.lower(AdmUsuario.email) == email)
            .first()
        )
        if usuario is None:
            print(f"No existe un usuario con email '{email}'.")
            return 1

        usuario.password_hash = hash_password(nueva)
        db.commit()
        print(f"OK — contrasena restablecida para {usuario.email} "
              f"({usuario.nombre} {usuario.apellido}).")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"Error: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
