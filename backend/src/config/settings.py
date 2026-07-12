import os
from pydantic import BaseModel, Field, ValidationError, ConfigDict
from dotenv import load_dotenv

class Settings(BaseModel):
    firebase_project_id: str = Field(..., alias="FIREBASE_PROJECT_ID")
    firebase_storage_bucket: str = Field(..., alias="FIREBASE_STORAGE_BUCKET")
    port: int = Field(8000, alias="PORT")
    log_level: str = Field("info", alias="LOG_LEVEL")

    model_config = ConfigDict(populate_by_name=True)

def load_settings() -> Settings:
    # Load .env file if present
    load_dotenv()
    try:
        # Load from environment variables
        env_data = {
            "FIREBASE_PROJECT_ID": os.getenv("FIREBASE_PROJECT_ID"),
            "FIREBASE_STORAGE_BUCKET": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "PORT": int(os.getenv("PORT", "8000")),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "info"),
        }
        
        # Verify required keys are present
        missing = [key for key, val in env_data.items() if val is None and key in ("FIREBASE_PROJECT_ID", "FIREBASE_STORAGE_BUCKET")]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return Settings(**env_data)
    except ValidationError as e:
        print(f"Configuration validation failed: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"Failed to load environment configuration: {e}")
        raise SystemExit(1)

# Central settings instance
settings = load_settings()
