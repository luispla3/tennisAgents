import os
import sys
from getpass import getpass

import requests

from config import APP_KEY, ENV_FILE, KEEP_ALIVE_URL, LOGIN_URL, SESSION_FILE, load_env_file

PLACEHOLDER_PASSWORDS = {"", "tu_contraseña_aqui", "tu_contraseña"}


def save_session_token(token):
    SESSION_FILE.write_text(token, encoding="utf-8")


def load_session_token():
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text(encoding="utf-8").strip()
    return os.environ.get("BETFAIR_SESSION_TOKEN", "").strip()


def get_credentials(username=None, password=None):
    load_env_file()
    username = username or os.environ.get("BETFAIR_USERNAME", "").strip()
    password = password or os.environ.get("BETFAIR_PASSWORD", "").strip()

    if password in PLACEHOLDER_PASSWORDS:
        password = ""

    if not username:
        username = input("Usuario Betfair: ").strip()

    if not password:
        password = getpass("Contraseña Betfair (2FA: contraseña+codigo): ")

    if not username or not password:
        print("Faltan credenciales.")
        print(f"Configura {ENV_FILE} con BETFAIR_USERNAME y BETFAIR_PASSWORD.")
        sys.exit(1)

    return username, password


def login(username=None, password=None):
    username, password = get_credentials(username, password)

    response = requests.post(
        LOGIN_URL,
        headers={
            "Accept": "application/json",
            "X-Application": APP_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"username": username, "password": password},
        timeout=30,
    )

    try:
        result = response.json()
    except ValueError:
        print(f"Error de login ({response.status_code}): {response.text}")
        sys.exit(1)

    if result.get("status") != "SUCCESS":
        print(f"Login fallido: {result.get('error') or result}")
        sys.exit(1)

    token = result["token"]
    save_session_token(token)
    print("Login correcto. Token guardado en .session_token")
    return token


def keep_alive(token):
    response = requests.post(
        KEEP_ALIVE_URL,
        headers={
            "Accept": "application/json",
            "X-Application": APP_KEY,
            "X-Authentication": token,
        },
        timeout=30,
    )

    try:
        result = response.json()
    except ValueError:
        return False

    if result.get("status") == "SUCCESS":
        token = result.get("token") or token
        save_session_token(token)
        return True

    return False


def ensure_session(force_login=False):
    if force_login:
        return login()

    token = load_session_token()
    if token and keep_alive(token):
        return token

    return login()
