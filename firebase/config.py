import os
import firebase_admin
from firebase_admin import credentials, auth, db

# Fetch the service account file path from environment variables or default to the local path
cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'firebase/service_account.json')

# Initialize Firebase Admin SDK
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        print("Firebase initialized successfully.")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Firebase: {e}")

# Global reference to Firebase Authentication
firebase_auth = auth
