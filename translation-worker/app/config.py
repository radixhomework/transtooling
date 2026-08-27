from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_path: str = "/data/app.db"
    translation_models_path: str = "/translation_models"
    translation_tmp_path: str = "/translation_tmp"
    translations_path: str = "/translations"

    # Intervalle de polling de la base pour détecter de nouveaux jobs /
    # demandes de téléchargement de modèle (en secondes).
    poll_interval_seconds: int = 5

    # CTranslate2
    translation_compute_type: str = "int8"
    # Nombre max de segments envoyés au moteur par appel translate_batch.
    translation_batch_size: int = 32

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
