import streamlit as st
import pandas as pd
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from datetime import datetime
import json

# --- Google Sheets Auth Configuration ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = '1C55hWzwDbiOt7vC8jvM2-YIKc6WHIorbIV6UaWgIg8Y'  # <- Replace with your actual sheet ID
SHEET_NAME = 'Sheet1'  # Or the name of your tab

# --- GOOGLE SHEETS AUTHENTICATION ---
def get_gsheet_client():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            #flow = InstalledAppFlow.from_client_secrets_file('commands.json', SCOPES)
            #creds = flow.run_local_server(port=0)
            client_config = st.secrets["client_secret.json"]
            flow = InstalledAppFlow.from_client_config({"installed": client_config}, SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

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
        sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            usuario, tarea, rol, contexto, resultado, tono, prompt.strip()
        ])
        st.success("✅ Prompt saved to Google Sheets.")
    except Exception as e:
        st.error(f"❌ Error saving prompt: {e}")

# --- PROMPT HISTORY ---
st.markdown("---")
st.subheader("📚 Prompt History")

try:
    gc = get_gsheet_client()
    sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    filtro = st.text_input("🔍 Search prompt history")

    if filtro:
        df = df[df.apply(lambda row: filtro.lower() in str(row).lower(), axis=1)]

    st.dataframe(df[::-1], use_container_width=True)

except Exception as e:
    st.error(f"Error loading history: {e}")