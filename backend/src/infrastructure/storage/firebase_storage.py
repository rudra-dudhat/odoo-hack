from datetime import timedelta
from firebase_admin import storage
from src.shared.logging import logger

def get_storage_bucket():
    """Get the singleton storage bucket."""
    return storage.bucket()

def upload_file_to_storage(file_bytes: bytes, destination_path: str, content_type: str) -> str:
    """
    Upload file bytes to Firebase Storage bucket at destination_path.
    Returns the standard public storage URL.
    """
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(destination_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        
        # In emulator mode or default, public_url might not resolve properly over WAN, 
        # but returning the standard storage path is fine.
        # Alternatively, generate a long-lived download URL or standard storage url.
        url = f"https://storage.googleapis.com/{bucket.name}/{destination_path}"
        logger.info(f"Uploaded file to storage path: {destination_path}")
        return url
    except Exception as e:
        logger.error(f"Failed to upload file to storage path {destination_path}: {e}")
        raise e

def generate_signed_url(destination_path: str, expiration_minutes: int = 60) -> str:
    """
    Generate a signed URL for a private storage resource.
    """
    try:
        bucket = get_storage_bucket()
        blob = bucket.blob(destination_path)
        url = blob.generate_signed_url(expiration=timedelta(minutes=expiration_minutes))
        return url
    except Exception as e:
        logger.error(f"Failed to generate signed URL for path {destination_path}: {e}")
        raise e
