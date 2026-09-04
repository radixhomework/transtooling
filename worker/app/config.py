from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_path: str = "/data/app.db"
    audio_tmp_path: str = "/audio_tmp"
    transcripts_path: str = "/transcripts"
    whisper_models_path: str = "/models"
    whisper_compute_type: str = "int8"

    # Intervalle de polling de la base pour détecter de nouveaux jobs /
    # demandes de téléchargement de modèle (en secondes).
    poll_interval_seconds: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
