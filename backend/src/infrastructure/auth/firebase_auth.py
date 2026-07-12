from firebase_admin import auth
from src.shared.errors import UnauthenticatedError
from src.shared.logging import logger

def verify_firebase_token(id_token: str) -> dict:
    """
    Verify Firebase ID Token and return decoded claims.
    Raises UnauthenticatedError if token is invalid or expired.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.warning(f"Firebase token verification failed: {e}")
        raise UnauthenticatedError("Invalid or expired authentication token")

def sync_custom_claims(uid: str, role_id: str, permission_keys: list[str]) -> None:
    """
    Sync role and permission list to Firebase Auth custom claims for Security Rules verification.
    """
    try:
        # Keep claims size under 1000 bytes by limiting permissions list if necessary, 
        # but standard set is expected to fit.
        claims = {
            "roleId": role_id,
            "permissions": permission_keys
        }
        auth.set_custom_user_claims(uid, claims)
        logger.info(f"Successfully synced custom claims to Firebase Auth for UID {uid}")
    except Exception as e:
        logger.error(f"Failed to sync custom claims to Firebase Auth for UID {uid}: {e}")
        # We don't propagate this exception to fail the transaction, but we log the error
        # because the backend's primary RBAC is cached-load, auth custom claims is defense-in-depth.
