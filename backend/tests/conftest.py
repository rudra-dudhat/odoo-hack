import os
import sys
from unittest.mock import MagicMock

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock firebase_admin credentials to bypass local OpenSSL private key parsing errors
import firebase_admin
from firebase_admin import credentials
import google.auth.credentials

# Create an anonymous Google Auth Credentials instance
anon_g_cred = google.auth.credentials.AnonymousCredentials()

# Create mock firebase credential object
mock_cred = MagicMock(spec=credentials.Base)
mock_cred.get_credential.return_value = anon_g_cred

# Patch Certificate constructor to return our mock credential
credentials.Certificate = MagicMock(return_value=mock_cred)

# Set the emulator host environment variable to enable Firestore offline emulator client mode
if not os.getenv("FIRESTORE_EMULATOR_HOST"):
    os.environ["FIRESTORE_EMULATOR_HOST"] = "localhost:8080"
