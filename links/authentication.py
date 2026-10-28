import os
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed


@lru_cache(maxsize=1)
def _firebase_app():
    import firebase_admin
    from firebase_admin import credentials

    app_name = "linkpay-backend"

    try:
        return firebase_admin.get_app(app_name)
    except ValueError:
        pass

    service_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT",
        "secrets/firebase-service-account.json",
    )
    service_path = Path(service_path)
    if not service_path.is_absolute():
        service_path = Path(settings.BASE_DIR) / service_path

    if not service_path.is_file():
        raise AuthenticationFailed(
            "Firebase service account is not configured on the server."
        )

    try:
        cred = credentials.Certificate(str(service_path))
        return firebase_admin.initialize_app(cred, name=app_name)
    except Exception as exc:
        raise AuthenticationFailed(
            "Firebase service account could not be initialized."
        ) from exc


def verify_firebase_request(request):
    from firebase_admin import auth

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise AuthenticationFailed(
            "Sign in first. Firebase ID token is missing."
        )

    token = header.split(" ", 1)[1].strip()
    try:
        return auth.verify_id_token(
            token,
            app=_firebase_app(),
            check_revoked=True,
        )
    except AuthenticationFailed:
        raise
    except Exception as exc:
        print(f"Firebase token verification failed: {type(exc).__name__}: {exc}")
        raise AuthenticationFailed(
            "Firebase token is invalid or expired. Please sign in again."
        ) from exc
