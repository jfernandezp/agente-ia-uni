import socket
import requests
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def get_client_ip() -> str:
    """
    Obtiene la IP del cliente de forma segura.
    Prioridad:
    1. X-Forwarded-For (proxy/load balancer)
    2. API externa (ipify)
    3. Localhost fallback
    """
    try:
        # 1. Intentar desde Streamlit context
        if hasattr(st, 'context') and hasattr(st.context, 'headers'):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For")
            if ip:
                return ip.split(",")[0].strip()
    except Exception as e:
        logger.debug(f"Error getting IP from Streamlit context: {e}")

    try:
        # 2. Intentar con API externa
        response = requests.get("https://api.ipify.org?format=json", timeout=2)
        if response.status_code == 200:
            return response.json().get("ip", "0.0.0.0")
    except Exception as e:
        logger.debug(f"Error getting IP from ipify: {e}")

    try:
        # 3. Fallback a localhost
        hostname = socket.gethostname()
        return socket.gethostbyname(hostname)
    except Exception as e:
        logger.debug(f"Error getting local IP: {e}")

    # 4. Último recurso
    return "0.0.0.0"


def get_ip_info(ip: str) -> dict:
    """
    Obtiene información geográfica de una IP.
    Retorna dict vacío si falla.
    """
    if not ip or ip in ["0.0.0.0", "127.0.0.1", "localhost"]:
        return {}
    
    try:
        response = requests.get(f"https://ipapi.co/{ip}/json/", timeout=2)
        if response.status_code == 200:
            data = response.json()
            # Filtrar solo campos relevantes
            return {
                "city": data.get("city", "Desconocida"),
                "country": data.get("country_name", "Desconocido"),
                "country_code": data.get("country_code", ""),
                "isp": data.get("org", "Desconocido"),
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude")
            }
    except Exception as e:
        logger.debug(f"Error getting IP info: {e}")
    
    return {}