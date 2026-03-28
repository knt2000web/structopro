import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Faltan SUPABASE_URL o SUPABASE_KEY en el archivo .env")

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
    
    if response.status_code in [200, 201]:
        res_data = response.json()
        user_id = res_data.get("user", {}).get("id")
        user_email = res_data.get("user", {}).get("email", email)
        access_token = res_data.get("access_token")
        return AuthResponse(user=DummyUser(email=user_email, id=user_id, access_token=access_token))
    else:
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
    else:
        err_msg = res_data.get("error_description") or res_data.get("msg") or "Credenciales inválidas"
        raise Exception(err_msg)

def sign_out_user():
    return True

def get_current_user():
    return None

def save_project_to_db(user: DummyUser, nombre: str, propietario: str, direccion: str, telefono: str, estado_json: dict):
    if not user or not user.access_token or not user.id:
        raise Exception("La sesión expiró o carece de token. Cierra sesión e ingresa nuevamente.")
    
    url = f"{SUPABASE_URL}/rest/v1/proyectos"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    data = {
        "user_id": user.id,
        "nombre_proyecto": nombre,
        "propietario": propietario,
        "direccion": direccion,
        "telefono": telefono,
        "estado_json": estado_json
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code not in [200, 201, 204]:
        err = response.json().get("message", "Error al guardar el proyecto en la nube")
        raise Exception(f"Error {response.status_code}: {err}")
    return True

def get_projects_from_db(user: DummyUser):
    if not user or not user.access_token or not user.id:
        raise Exception("La sesión expiró o carece de token.")
        
    url = f"{SUPABASE_URL}/rest/v1/proyectos?select=id,nombre_proyecto,propietario,created_at,estado_json&order=created_at.desc"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {user.access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        err = response.json().get("message", "Error al recuperar los proyectos")
        raise Exception(f"Error {response.status_code}: {err}")
