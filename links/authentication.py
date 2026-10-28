
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

    # First, try Firebase credentials from Railway environment variables.
    env_mapping = {
        "type": "FIREBASE_TYPE",
        "project_id": "FIREBASE_PROJECT_ID",
        "private_key_id": "FIREBASE_PRIVATE_KEY_ID",
        "private_key": "FIREBASE_PRIVATE_KEY",
        "client_email": "FIREBASE_CLIENT_EMAIL",
        "client_id": "FIREBASE_CLIENT_ID",
        "auth_uri": "FIREBASE_AUTH_URI",
        "token_uri": "FIREBASE_TOKEN_URI",
        "auth_provider_x509_cert_url": (
            "FIREBASE_AUTH_PROVIDER_X509_CERT_URL"
        ),
        "client_x509_cert_url": "FIREBASE_CLIENT_X509_CERT_URL",
        "universe_domain": "FIREBASE_UNIVERSE_DOMAIN",
    }

    service_account = {
        json_key: os.getenv(env_name, "").strip()
        for json_key, env_name in env_mapping.items()
    }

    if all(service_account.values()):
        service_account["private_key"] = (
            service_account["private_key"].replace("\\n", "\n")
        )

        try:
            cred = credentials.Certificate(service_account)
            return firebase_admin.initialize_app(
                cred,
                name=app_name,
            )
        except Exception as exc:
            print(
                "Firebase environment credentials initialization failed: "
                f"{type(exc).__name__}: {exc}"
            )
            raise AuthenticationFailed(
                "Firebase service account could not be initialized."
            ) from exc

    # If environment variables are incomplete, try the original JSON file.
    service_path = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT",
        "secrets/firebase-service-account.json",
    )
    service_path = Path(service_path)

    if not service_path.is_absolute():
        service_path = Path(settings.BASE_DIR) / service_path

    if not service_path.is_file():
        missing = [
            env_name
            for json_key, env_name in env_mapping.items()
            if not service_account[json_key]
        ]
        print(
            "Firebase service account is not configured. "
            f"Missing environment variable names: {', '.join(missing)}"
        )
        raise AuthenticationFailed(
            "Firebase service account is not configured on the server."
        )

    try:
        cred = credentials.Certificate(str(service_path))
        return firebase_admin.initialize_app(cred, name=app_name)
    except Exception as exc:
        print(
            "Firebase service account file initialization failed: "
            f"{type(exc).__name__}: {exc}"
        )
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
            "Firebase ID token is invalid or expired. Please sign in again."
        ) from exc
