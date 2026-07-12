import os
import firebase_admin
from firebase_admin import credentials, firestore
from src.config.settings import settings
from src.shared.logging import logger

def initialize_firebase() -> firestore.firestore.Client:
    """Initialize Firebase Admin SDK and return Firestore client."""
    if not firebase_admin._apps:
        # Look for serviceAccountKey.json in the backend directory
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        key_path = os.path.join(base_dir, "serviceAccountKey.json")
        
        # Check if FIRESTORE_EMULATOR_HOST is set (for testing)
        emulator_host = os.getenv("FIRESTORE_EMULATOR_HOST")
        
        if emulator_host:
            logger.info(f"Connecting to Firestore Emulator at {emulator_host} using dummy service account")
            # Use a dummy service account dictionary to bypass GCP Application Default Credentials lookup
            dummy_cert = {
                "type": "service_account",
                "project_id": settings.firebase_project_id or "dummy-project-id",
                "private_key_id": "dummy-key-id",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC3\n-----END PRIVATE KEY-----\n",
                "client_email": "dummy@dummy.iam.gserviceaccount.com",
                "client_id": "dummy-client-id",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/dummy%40dummy.iam.gserviceaccount.com"
            }
            cred = credentials.Certificate(dummy_cert)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.firebase_project_id,
                "storageBucket": settings.firebase_storage_bucket
            })
        elif os.path.exists(key_path):
            logger.info(f"Initializing Firebase with service account key: {key_path}")
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred, {
                "projectId": settings.firebase_project_id,
                "storageBucket": settings.firebase_storage_bucket
            })
        else:
            logger.info("Initializing Firebase using Application Default Credentials (ADC)")
            firebase_admin.initialize_app(options={
                "projectId": settings.firebase_project_id,
                "storageBucket": settings.firebase_storage_bucket
            })
            
    return firestore.client()

# Singleton db client instance
try:
    db = initialize_firebase()
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {e}")
    raise SystemExit(1)
