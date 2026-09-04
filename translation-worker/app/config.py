from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    sqlite_path: str = "/data/app.db"
    translation_models_path: str = "/translation_models"
    translation_tmp_path: str = "/translation_tmp"
    translations_path: str = "/translations"

    # Database polling interval to detect new jobs / model download
    # requests (in seconds).
    poll_interval_seconds: int = 5

    # CTranslate2
    translation_compute_type: str = "int8"
    # Max number of segments sent to the engine per translate_batch call.
    translation_batch_size: int = 32

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
