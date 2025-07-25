import streamlit as st
import pandas as pd
import gspread
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from datetime import datetime
import json
from urllib.parse import urlencode

# --- GOOGLE SHEETS CONFIGURATION ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SHEET_ID = '1C55hWzwDbiOt7vC8jvM2-YIKc6WHIorbIV6UaWgIg8Y'
SHEET_NAME = 'Sheet1'

# --- AUTHENTICATION FUNCTION ---
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
            st.markdown("### 🔐 Authorize your Google account")
            st.info("You will be redirected to a new tab to authorize access. After authorizing, **return to this tab to continue.**")
            st.markdown(f"[👉 Authorize on Google]({auth_url})")
            st.stop()

        elif "code" in query_params and "google_creds" not in st.session_state:
            try:
                full_redirect_uri = f"{redirect_uri}?{urlencode(query_params, doseq=True)}"
                flow.fetch_token(authorization_response=full_redirect_uri)
                creds = flow.credentials
                st.session_state["google_creds"] = json.loads(creds.to_json())
                st.success("✅ Authentication successful! You can now use the generator.")
                st.rerun()

            except Exception as e:
                st.error(f"❌ Authentication error: {e}")
                st.stop()

    return gspread.authorize(creds)


# --- STREAMLIT CONFIG ---
st.set_page_config(page_title="Prompt Generator", layout="centered")
st.title("🤖 Smart Prompt Generator")

# --- FORCE AUTHENTICATION ---
if "google_creds" not in st.session_state:
    st.warning("🔐 Please authenticate with Google to continue.")
    get_gsheet_client()
    st.stop()

# --- FORM STATE RESET ---
if "clear_form" not in st.session_state:
    st.session_state.clear_form = False

if st.session_state.clear_form:
    st.session_state.clear_form = False
    for key in ["user", "task", "role", "context", "outcome", "tone"]:
        st.session_state[key] = "" if key != "tone" else "Professional"

# --- PROMPT FORM ---
st.write("Fill out the form to generate a custom prompt:")
default_roles = [
    "Marketing Analyst",
    "Software Engineer",
    "Customer Support Agent",
    "Sales Representative",
    "Data Scientist",
    "Content Writer",
    "Product Manager",
    "Other (specify below)"
]


user = st.text_input("🧑 Your name or email", key="user")
selected_role = st.selectbox("👤 What role should ChatGPT assume?", default_roles, key="selected_role")

if selected_role == "Other (specify below)":
    role = st.text_input("✏️ Enter custom role", key="role_custom")
else:
    role = selected_role
    
task = st.text_input("🎯 What should ChatGPT do?", key="task", placeholder="e.g. Write an email, Summarize a report")
context = st.text_area("📋 What information should it consider?", key="context")
outcome = st.text_input("📦 What result do you expect?", key="outcome", placeholder="e.g. A summary, A 150-word post")
tone = st.selectbox("🎨 Preferred tone?", ["Professional", "Casual", "Creative", "Technical", "Neutral"], key="tone")

# --- ACTION BUTTONS ---
generate = False
prompt = ""

col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 Generate Prompt"):
        if not (user and task and role and context and outcome):
            st.warning("⚠️ Please complete all fields before generating.")
        else:
            generate = True
            prompt = f"""Act as a {role.lower()}. Your task is to {task.lower()}.
Consider the following: {context.strip()}
The expected result is: {outcome.lower()}. Use a {tone.lower()} tone."""

with col2:
    if st.button("🧹 Clear Form"):
        st.session_state.clear_form = True
        st.rerun()

# --- DISPLAY GENERATED PROMPT ---
if generate:
    st.markdown("### 📝 Generated Prompt:")
    st.code(prompt.strip(), language="markdown")

    # --- SAVE TO GOOGLE SHEETS ---
    try:
        gc = get_gsheet_client()
        sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
        sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            user, task, role, context, outcome, tone, prompt.strip()
        ])
        st.success("✅ Prompt saved to Google Sheets.")
    except Exception as e:
        import traceback
        st.error("❌ Error saving prompt:")
        st.code(traceback.format_exc())

# --- PROMPT HISTORY ---
st.markdown("---")
st.subheader("📚 Prompt History")

try:
    gc = get_gsheet_client()
    sheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    search = st.text_input("🔍 Search in history")

    if search:
        df = df[df.apply(lambda row: search.lower() in str(row).lower(), axis=1)]

    st.dataframe(df[::-1], use_container_width=True)
except Exception as e:
    st.error(f"❌ Error loading history: {e}")
