from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Configuration chargée depuis les variables d'environnement (.env)."""

    # Admin par défaut (utilisé uniquement à la création initiale du compte)
    admin_login: str = "admin"
    # Héritage : anciennes instances utilisant ADMIN_EMAIL (le compte admin
    # préexistant garde son identifiant d'origine après la migration).
    admin_email: str = ""
    admin_password: str = "changeme"

    # Sécurité / JWT
    jwt_secret: str = "change_this_secret_before_deploying"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60
    jwt_refresh_expiration_days: int = 7

    # Limites par défaut (valeurs de départ, ensuite modifiables en base via /admin/settings)
    default_max_file_size_mb: int = 200
    default_max_duration_min: int = 60

    # Whisper
    default_whisper_model: str = "small"
    whisper_engine: str = "faster-whisper"
    whisper_models_path: str = "/models"
    whisper_compute_type: str = "int8"

    # Stockage
    sqlite_path: str = "/data/app.db"
    audio_tmp_path: str = "/audio_tmp"
    transcripts_path: str = "/transcripts"

    # Traduction (archives uploadées / résultats produits)
    translation_tmp_path: str = "/translation_tmp"
    translations_path: str = "/translations"

    # CORS
    cors_origins: str = "http://localhost"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
