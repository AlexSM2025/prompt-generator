import streamlit as st
import pandas as pd
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from datetime import datetime
import json
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from urllib.parse import urlparse
from urllib.parse import urlencode

# --- Google Sheets Auth Configuration ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = '1C55hWzwDbiOt7vC8jvM2-YIKc6WHIorbIV6UaWgIg8Y'  # <- Replace with your actual sheet ID
SHEET_NAME = 'Sheet1'  # Or the name of your tab

import streamlit as st
st.write("🔑 Claves en st.secrets:", list(st.secrets.keys()))

# --- GOOGLE SHEETS AUTHENTICATION ---
def get_gsheet_client():
    creds = None

    if "google_creds" in st.session_state:
        creds = Credentials.from_authorized_user_info(st.session_state["google_creds"], SCOPES)
    else:
        client_config = {
            "web": {
                "client_id": st.secrets["client_secret"]["client_id"],
                "project_id": st.secrets["client_secret"]["project_id"],
                "auth_uri": st.secrets["client_secret"]["auth_uri"],
                "token_uri": st.secrets["client_secret"]["token_uri"],
                "auth_provider_x509_cert_url": st.secrets["client_secret"]["auth_provider_x509_cert_url"],
                "client_secret": st.secrets["client_secret"]["client_secret"],
                "redirect_uris": json.loads(st.secrets["client_secret"]["redirect_uris"])
            }
        }

        redirect_uri = client_config["web"]["redirect_uris"][0]
        flow = Flow.from_client_config(client_config, SCOPES)
        flow.redirect_uri = redirect_uri

        query_params = st.query_params

        if "code" not in query_params:
            auth_url, _ = flow.authorization_url(prompt='consent', include_granted_scopes='true')
            st.markdown("### 🔐 Autoriza tu cuenta de Google")
            st.markdown(f"[Haz clic aquí para autorizar en Google]({auth_url})")
            st.stop()
        else:
            try:
                # DEBUG: Mostrar el query_params completo
                st.write("🔎 Parámetros de redirección:", query_params)

                # Armar URL de redirección con todos los parámetros
                from urllib.parse import urlencode
                full_url = f"{redirect_uri}?{urlencode({k: v[0] for k, v in query_params.items()})}"
                st.write("🔗 URL reconstruida para fetch_token:", full_url)

                # Intentar obtener credenciales
                flow.fetch_token(authorization_response=full_url)
                creds = flow.credentials
                st.session_state["google_creds"] = json.loads(creds.to_json())
                st.success("✅ Autenticado con éxito")
            except Exception as e:
                st.error(f"Error de autenticación: {e}")
                st.stop()

    return gspread.authorize(creds)



# --- RESET STATE ---
if "clear_form" not in st.session_state:
    st.session_state.clear_form = False

if st.session_state.clear_form:
    st.session_state.clear_form = False
    for key in ["usuario", "tarea", "rol", "contexto", "resultado", "tono"]:
        st.session_state[key] = "" if key != "tono" else "Professional"

# --- STREAMLIT UI CONFIGURATION ---
st.set_page_config(page_title="Prompt Generator", layout="centered")
st.title("🤖 Smart Prompt Generator")
st.write("Fill out the form to generate a personalized prompt.")

# --- FORM FIELDS ---
usuario = st.text_input("🧑 Your name or email", key="usuario")
rol = st.text_input("👤 What role should ChatGPT assume?", key="rol", placeholder="e.g. Marketing analyst, Software engineer, Project manager")
tarea = st.text_input("🎯 What do you want ChatGPT to do?", key="tarea", placeholder="e.g. Write a cold email, Summarize a report, Draft social media post")
contexto = st.text_area("📋 What information should it consider?", key="contexto")
resultado = st.text_input("📦 What result do you expect?", key="resultado", placeholder="e.g. A 3-paragraph summary, A 150-word LinkedIn post, A table with pros and cons")
tono = st.selectbox("🎨 What tone do you prefer?", ["Professional", "Casual", "Creative", "Technical", "Neutral"], key="tono")

# --- ACTION BUTTONS ---
generate = False
prompt = ""

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Generate Prompt"):
        if not (usuario and tarea and rol and contexto and resultado):
            st.warning("Please complete all fields.")
        else:
            generate = True
            prompt = f"""Act as a {rol.lower()}. Your task is to {tarea.lower()}.
Consider the following: {contexto.strip()}
The expected result is: {resultado.lower()}. Use a {tono.lower()} tone."""

with col2:
    if st.button("🧹 Clear All"):
        st.session_state.clear_form = True
        st.rerun()

# --- DISPLAY GENERATED PROMPT ---
if generate:
    st.markdown("### 📝 Generated Prompt:")
    st.code(prompt.strip(), language="markdown")

    # Save to Google Sheets
    try:
        gc = get_gsheet_client()
        if gc:
            sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
            sheet.append_row([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                usuario, tarea, rol, contexto, resultado, tono, prompt.strip()
            ])
            st.success("✅ Prompt saved to Google Sheets.")
        else:
            st.warning("🔐 Connect with Google.")
            
    except Exception as e:
        st.error(f"❌ Error saving prompt: {e}")

# --- PROMPT HISTORY ---
st.markdown("---")
st.subheader("📚 Prompt History")

try:
    gc = get_gsheet_client()
    if gc:
        sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        data = sheet.get_all_records()
        df = pd.DataFrame(data)

        filtro = st.text_input("🔍 Search prompt history")

        if filtro:
            df = df[df.apply(lambda row: filtro.lower() in str(row).lower(), axis=1)]

        st.dataframe(df[::-1], use_container_width=True)
    else:
        st.info("Connect with Google to see the history.")

except Exception as e:
    st.error(f"Error loading history: {e}")
