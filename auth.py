import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Soporte dual: Streamlit Cloud (st.secrets) y local (.env)
def _get_secret(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")

SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_KEY = _get_secret("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY. Configuralos en .env (local) o en Secrets de Streamlit Cloud.")

import requests

class DummyUser:
    def __init__(self, email, id=None, access_token=None):
        self.email = email
        self.id = id
        self.access_token = access_token

class AuthResponse:
    def __init__(self, user=None, error=None):
        self.user = user
        self.error = error

def sign_up_user(email: str, password: str):
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {"email": email, "password": password}
    response = requests.post(url, headers=headers, json=data)
    res_data = response.json()
    if response.status_code == 200:
        user_id = res_data.get("user", {}).get("id")
        user_email = res_data.get("user", {}).get("email", email)
        access_token = res_data.get("access_token")
        return AuthResponse(user=DummyUser(email=user_email, id=user_id, access_token=access_token))
    err_msg = response.json().get("msg") or response.json().get("error_description") or "Error desconocido de registro"
    raise Exception(err_msg)

def sign_in_user(email: str, password: str):
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    data = {"email": email, "password": password}
    response = requests.post(url, headers=headers, json=data)
    res_data = response.json()
    if response.status_code == 200:
        user_id = res_data.get("user", {}).get("id")
        user_email = res_data.get("user", {}).get("email", email)
        access_token = res_data.get("access_token")
        return AuthResponse(user=DummyUser(email=user_email, id=user_id, access_token=access_token))
    err_msg = res_data.get("error_description") or res_data.get("msg") or "Credenciales invalidas"
    raise Exception(err_msg)

def sign_out_user():
    return True

def get_current_user():
    return st.session_state.get("user", None)

def save_project_to_db(user, nombre_proyecto, propietario, direccion, telefono, estado_json):
    import json
    user_id = getattr(user, 'id', None)
    access_token = getattr(user, 'access_token', None)
    if not user_id:
        raise Exception("Usuario no autenticado")
    url = f"{SUPABASE_URL}/rest/v1/proyectos"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token or SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    data = {
        "user_id": user_id,
        "nombre_proyecto": nombre_proyecto,
        "propietario": propietario,
        "direccion": direccion,
        "telefono": telefono,
        "estado_json": json.dumps(estado_json) if not isinstance(estado_json, str) else estado_json
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in (200, 201):
        raise Exception(f"Error al guardar: {response.status_code} - {response.text}")
    return response.json()


def get_projects_from_db(user):
    user_id = getattr(user, 'id', None)
    access_token = getattr(user, 'access_token', None)
    if not user_id:
        raise Exception("Usuario no autenticado")
    url = f"{SUPABASE_URL}/rest/v1/proyectos?user_id=eq.{user_id}&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {access_token or SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Error al obtener proyectos: {response.status_code} - {response.text}")
    return response.json()
