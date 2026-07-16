from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "_eLedger"
    APP_VERSION: str = "0.1.0"

    DATABASE_URL: str

    UPLOAD_DIR: str = "./uploads"

    @property
    def upload_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Clave Fernet para cifrar secretos guardados en BD (credenciales del PTH).
    # Vacía => se deriva de JWT_SECRET, cómodo en dev. En PRODUCCIÓN debe fijarse
    # explícitamente: si se rota JWT_SECRET sin fijar esta, los tokens ya
    # guardados quedan indescifrables y hay que recapturarlos.
    FE_ENCRYPTION_KEY: str = ""

    # Orígenes explícitos (dominios de producción). En desarrollo se acepta
    # cualquier puerto de localhost/127.0.0.1 vía CORS_ORIGIN_REGEX.
    CORS_ORIGINS: List[str] = []
    CORS_ORIGIN_REGEX: str = r"http://(localhost|127\.0\.0\.1):\d+"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
