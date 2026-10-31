import streamlit as st
import pandas as pd
import re
import pdfplumber
import sqlite3
import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import fitz  # PyMuPDF
import tempfile
import os
import pytz
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from dotenv import load_dotenv
from lab_preload import (accept_api_payload, clear_patient_state, sync_form_state, remember_result, fingerprint, finite_number, prepare_api_import)
from lab_catalog import build_lab_catalog
from lab_reference import score_lab_results, classify_result, reference_label, assess_result, parse_interval

# Load environment variables for local testing
load_dotenv()

# ============================================================
# ==================== AUTHENTICATION ========================
# ============================================================

#if not st.user.is_logged_in:
#    st.markdown("# Welcome to Lab Results Report Generator")
#    if st.button("Log in with Google", type="primary"):
#        st.login(provider="google")
#    st.stop()

# Domain restriction
#if not st.user.email.endswith("@1stoptimal.com"):
#    st.error("Access denied: Only @1stoptimal.com emails are allowed.")
#    if st.button("Log out"):
#        st.logout()
#    st.stop()

# Logout button in sidebar (with unique key to avoid duplicate ID error)
#if st.sidebar.button("Log out", key="logout_btn"):
#    st.logout()

# Personalized greeting
#st.sidebar.markdown(f"Welcome, {st.user.name}! ({st.user.email})")

# ============================================================
# ==================== PASSWORD PROTECTION (via Secrets) =====
# ============================================================

import streamlit as st

# Read password from Streamlit Secrets (never exposed in GitHub)
APP_PASSWORD = st.secrets.get("APP_PASSWORD", "")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("# Welcome to Lab Results Report Generator")
    st.info("This app is currently in limited access mode.")

    password = st.text_input("Enter access password", type="password", key="pwd_input")

    if st.button("Enter", type="primary"):
        if password == APP_PASSWORD and APP_PASSWORD != "":
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password. Please try again.")
    st.stop()

# If user reaches here, they are authenticated
st.sidebar.success("✅ Access granted")

# ============================================================
# ==================== BRANDING & STYLING ====================
# ============================================================
PRIMARY_COLOR = "#06B6D4"
SECONDARY_COLOR = "#737373"
vibrant_red = "#FF5555"
in_range_color = "#FFA500"
BACKGROUND_COLOR = "#EBEBEB"
FONT_PRIMARY = "Exo2-Regular.ttf"
FONT_SECONDARY = "Source Sans Pro"
st.set_page_config(page_title="1st Optimal Lab Results Report Generator", page_icon="🧪", layout="wide", initial_sidebar_state="expanded")
st.markdown(
    f"""
    <style>
    body {{
        background-color: {BACKGROUND_COLOR};
        font-family: '{FONT_SECONDARY}', sans-serif;
    }}
    .report-title {{
        color: {PRIMARY_COLOR};
        font-family: '{FONT_PRIMARY}', sans-serif;
        font-size: 36px;
        text-align: center;
    }}
    .subtitle {{
        color: {SECONDARY_COLOR};
        font-family: '{FONT_SECONDARY}', sans-serif;
        font-size: 20px;
        text-align: center;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)
logo_path = "1st-Optimal-Logo-Dark.png"
if os.path.exists(logo_path):
    st.image(logo_path, width=500)
st.markdown('<h1 class="report-title">Lab Results Report Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Generate The Optimal Lab Report</p>', unsafe_allow_html=True)

# Load JSON Data
GITHUB_BASE_URL = "https://raw.githubusercontent.com/theebuddylee/HealthReport/main/data/"
@st.cache_data
def load_json_from_github(filename):
    url = f"{GITHUB_BASE_URL}{filename}"
    try:
        response = requests.get(url, timeout=20, allow_redirects=False)
        if response.status_code == 200:
            return response.json()
        st.error(f"Failed to load {filename}. HTTP {response.status_code}")
    except (requests.RequestException, ValueError):
        st.error(f"Could not load {filename}. Please try again.")
    return {}
contact_info = load_json_from_github("contact_info.json")
lab_markers = build_lab_catalog(load_json_from_github("lab_markers.json"))

# Database Initialization
try:
    conn = sqlite3.connect("lab_results.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS report_analytics (
        report_id INTEGER PRIMARY KEY AUTOINCREMENT,
        membership_manager TEXT,
        marker TEXT,
        is_optimal_out INTEGER,
        is_clinical_out INTEGER,
        timestamp TEXT
    )
    """)
    conn.commit()
except sqlite3.Error as e:
    st.error(f"Database error: {e}")

# Manual Mapping (expanded for variants)
manual_map = {
    "t": "Free T4",
    "wbc": "White Blood Cell (WBC) Count",
    "rbc": "Red Blood Cell (RBC) Count",
    "mcv": "Mean Corpuscular Volume (MCV)",
    "mch": "Mean Corpuscular Hemoglobin (MCH)",
    "mchc": "Mean Corpuscular Hemoglobin Concentration (MCHC)",
    "rdw": "Red Cell Distribution Width (RDW)",
    "platelets": "Platelet Count",
    "lymphs": "Lymphocytes (%)",
    "eos": "Eosinophils (%)",
    "basos": "Basophils (%)",
    "bun": "Blood Urea Nitrogen (BUN)",
    "protein total": "Total Protein",
    "bilirubin total": "Total Bilirubin",
    "ast sgot": "Aspartate Aminotransferase (AST)",
    "alt sgpt": "Alanine Aminotransferase (ALT)",
    "cholesterol total": "Total Cholesterol",
    "testosterone": "Total Testosterone",
    "hdl cholesterol": "HDL",
    "testosterone total lcms a": "Total Testosterone (LC/MS) [uncapped]",
    "hemoglobin a": "Hemoglobin (Hgb)",
    "dheasulfate": "Dehydroepiandrosterone Sulfate (DHEA-S)",
    "lh": "Luteinizing Hormone (LH)",
    "fsh": "Follicle-Stimulating Hormone (FSH)",
    "prolactin": "Prolactin",
    "Prolactin": "Prolactin",
    "PROLACTIN": "Prolactin",
    "PROLACTIN_TEST": "Prolactin",
    "estradiol": "Estradiol",
    "Estradiol": "Estradiol",
    "ESTRADIOL": "Estradiol",
    "ESTRADIOL (SERUM)": "Estradiol",
    "estradiol (serum)": "Estradiol",
    "ggt": "Glutamyl Transferase (GGT)",
    "insulin": "Fasting Insulin",
    "triiodothyronine t": "Free T3",
    "prostate specific ag": "Prostate Specific Antigen (PSA)",
    "shbg": "Sex Hormone Binding Globulin (SHBG)",
    "neutrophils absolute": "Neutrophils (Absolute)",
    "lymphs absolute": "Lymphocytes (Absolute)",
    "monocytesabsolute": "Monocytes (Absolute)",
    "eos absolute": "Eosinophils (Absolute)",
    "baso absolute": "Basophils (Absolute)",
    "vldl cholesterol cal": "VLDL (calculated)",
    "ldl chol calc nih": "LDL (calculated)",
    "psa value": "Prostate Specific Antigen (PSA)",
    "hematocri": "Hematocrit",
    "WBC": "White Blood Cell (WBC) Count",
    "RBC": "Red Blood Cell (RBC) Count",
    "Hemoglobin": "Hemoglobin (Hgb)",
    "Hematocrit": "Hematocrit",
    "MCV": "Mean Corpuscular Volume (MCV)",
    "MCH": "Mean Corpuscular Hemoglobin (MCH)",
    "MCHC": "Mean Corpuscular Hemoglobin Concentration (MCHC)",
    "RDW": "Red Cell Distribution Width (RDW)",
    "Platelets": "Platelet Count",
    "Neutrophils": "Neutrophils (%)",
    "Lymphs": "Lymphocytes (%)",
    "Monocytes": "Monocytes (%)",
    "Eos": "Eosinophils (%)",
    "Basos": "Basophils (%)",
    "Neutrophils (Absolute)": "Neutrophils (Absolute)",
    "Lymphs (Absolute)": "Lymphocytes (Absolute)",
    "Monocytes(Absolute)": "Monocytes (Absolute)",
    "Eos (Absolute)": "Eosinophils (Absolute)",
    "Baso (Absolute)": "Basophils (Absolute)",
    "Glucose": "Glucose",
    "BUN": "Blood Urea Nitrogen (BUN)",
    "Creatinine": "Creatinine",
    "eGFR": "Estimated Glomerular Filtration Rate (eGFR)",
    "BUN/Creatinine Ratio": "BUN/Creatinine Ratio",
    "Sodium": "Sodium",
    "Potassium": "Potassium",
    "Chloride": "Chloride",
    "Carbon Dioxide, Total": "Carbon Dioxide (CO\u2082), Total",
    "Calcium": "Calcium",
    "Protein, Total": "Total Protein",
    "Albumin": "Albumin",
    "Globulin, Total": "Globulin, Total",
    "Bilirubin, Total": "Total Bilirubin",
    "Alkaline Phosphatase": "Alkaline Phosphatase",
    "AST (SGOT)": "Aspartate Aminotransferase (AST)",
    "ALT (SGPT)": "Alanine Aminotransferase (ALT)",
    "Cholesterol, Total": "Total Cholesterol",
    "Triglycerides": "Triglycerides",
    "HDL Cholesterol": "HDL",
    "VLDL Cholesterol Cal": "VLDL (calculated)",
    "LDL Cholesterol Calc": "LDL (calculated)",
    "LH": "Luteinizing Hormone (LH)",
    "FSH": "Follicle-Stimulating Hormone (FSH)",
    "Free Testosterone(Direct)": "Free Testosterone (Direct assay)",
    "Hemoglobin A1c": "HbA1c",
    "Sex Horm Binding Glob, Serum": "Sex Hormone Binding Globulin (SHBG)",
    "Testosterone, Serum": "Total Testosterone",
    "Glucose, Serum": "Glucose",
    "Creatinine, Serum": "Creatinine",
    "Sodium, Serum": "Sodium",
    "Potassium, Serum": "Potassium",
    "Chloride, Serum": "Chloride",
    "Calcium, Serum": "Calcium",
    "Protein, Total, Serum": "Total Protein",
    "Albumin, Serum": "Albumin",
    "Alkaline Phosphatase, S": "Alkaline Phosphatase",
    "Prostate Specific Ag, Serum": "Prostate Specific Antigen (PSA)",
    "Immature Granulocytes": "Immature Granulocytes",
    "Immature Grans (Abs)": "Immature Granulocytes (Absolute)",
    "C-Reactive Protein, Cardiac": "C-Reactive Protein, High Sensitivity (hsCRP)",
    "Cortisol": "Cortisol",
    "Estradiol, Sensitive": "Estradiol, Sensitive / Ultrasensitive (LC/MS)",
    "Ferritin, Serum": "Ferritin",
    "Iron Bind.Cap.(TIBC)": "TIBC (Total Iron Binding Capacity)",
    "Iron Saturation": "Transferrin Saturation",
    "Iron, Serum": "Iron",
    "UIBC": "UIBC (Unsaturated Iron Binding Capacity)",
    "Hb A1c Diabetic Assessment": "Hemoglobin A1c",
    "Testosterone, Total, LC/MS": "Total Testosterone (LC/MS) [uncapped]",
    "Triiodothyronine,Free,Serum": "Free T3",
    "T4,Free(Direct)": "Free T4",
    "Vitamin D, 25-Hydroxy": "Vitamin D (25-OH)",
    "DHEA-Sulfate": "Dehydroepiandrosterone Sulfate (DHEA-S)",
    "LDL Chol Calc (NIH)": "LDL (calculated)",
    "LDL/HDL Ratio": "LDL/HDL Ratio",
    "Lipoprotein (a)": "Lipoprotein (a)",
    "Insulin": "Fasting Insulin",
    "Insulin-Like Growth Factor I": "Insulin-Like Growth Factor I (IGF-1)",
    "Progesterone": "Progesterone",
    "TSH": "TSH",
    "GGT": "Glutamyl Transferase (GGT)",
    "Apolipoprotein B": "Apolipoprotein B",
    "Transferrin": "Transferrin",
    "Hgb A1c MFr Bld": "HbA1c",
    "GGT SerPl-cCnc": "Glutamyl Transferase (GGT)",
    "T3Free SerPl-mCnc": "Free T3",
    "LPa SerPl-sCnc": "Lipoprotein (a)",
    "25(OH)D SerPl-mCnc": "Vitamin D (25-OH)",
    "Vitamin D3 SerPl-mCnc": "Vitamin D3",
    "Vitamin D2 SerPl-mCnc": "Vitamin D2",
    "WBC # Bld Auto": "White Blood Cell (WBC) Count",
    "RBC # Bld Auto": "Red Blood Cell (RBC) Count",
    "Hgb Bld-mCnc": "Hemoglobin (Hgb)",
    "Hct VFr Bld Auto": "Hematocrit",
    "MCV RBC Auto": "Mean Corpuscular Volume (MCV)",
    "MCH RBC Qn Auto": "Mean Corpuscular Hemoglobin (MCH)",
    "MCHC RBC Auto-mCnc": "Mean Corpuscular Hemoglobin Concentration (MCHC)",
    "RDW RBC Auto-Rto": "Red Cell Distribution Width (RDW)",
    "Platelet # Bld Auto": "Platelet Count",
    "PMV Bld Rees-Ecker": "Mean Platelet Volume (MPV)",
    "Neutrophils # Bld Auto": "Neutrophils (Absolute)",
    "Cholest SerPl-mCnc": "Total Cholesterol",
    "HDLc SerPl-mCnc": "HDL",
    "Trigl SerPl-mCnc": "Triglycerides",
    "LDLc SerPl Calc-mCnc": "LDL (calculated)",
    "LDLc/HDLc SerPl-mRto": "LDL/HDL Ratio",
    "TSH SerPl-aCnc": "TSH",
    "T4 Free SerPl-mCnc": "Free T4",
    "Apo B SerPl-mCnc": "Apolipoprotein B",
    "Glucose SerPl-mCnc": "Glucose",
    "BUN SerPl-mCnc": "Blood Urea Nitrogen (BUN)",
    "Creat SerPl-mCnc": "Creatinine",
    "eGFRcr SerPlBld CKD-EPI 2021": "Estimated Glomerular Filtration Rate (eGFR)",
    "BUN/Creat SerPl": "BUN/Creatinine Ratio",
    "Sodium SerPl-sCnc": "Sodium",
    "Potassium SerPl-sCnc": "Potassium",
    "Chloride SerPl-sCnc": "Chloride",
    "CO2 SerPl-sCnc": "Carbon Dioxide (CO\u2082), Total",
    "Calcium SerPl-mCnc": "Calcium"
}

# CharmHealth API Functions

def charm_response(request, action, *args, **kwargs):
    """Bound HTTPS calls and suppress response bodies containing private details."""
    try:
        response = request(*args, timeout=20, allow_redirects=False, **kwargs)
        if response.status_code != 200:
            st.error(f"{action} failed (HTTP {response.status_code}). Please try again.")
            return None
        data = response.json()
        if not isinstance(data, dict):
            st.error(f"{action} returned an unsupported response. Please try again.")
            return None
        return data
    except (requests.RequestException, ValueError):
        st.error(f"{action} could not complete. Check your connection and try again.")
        return None


def refresh_access_token():
    refresh_token = st.session_state.get("refresh_token", "")
    client_id = st.session_state.get("client_id", "")
    client_secret = st.session_state.get("client_secret", "")
    if not (refresh_token and client_id and client_secret):
        refresh_token = st.secrets.get("REFRESH_TOKEN", os.getenv("REFRESH_TOKEN"))
        client_id = st.secrets.get("CLIENT_ID", os.getenv("CLIENT_ID"))
        client_secret = st.secrets.get("CLIENT_SECRET", os.getenv("CLIENT_SECRET"))
    if not (refresh_token and client_id and client_secret):
        st.error("The existing API configuration is incomplete.")
        return None
    data = charm_response(requests.post, "Token refresh",
        'https://accounts.charmtracker.com/oauth/v2/token', data={
            'refresh_token': refresh_token, 'client_id': client_id,
            'client_secret': client_secret, 'grant_type': 'refresh_token'})
    if data is None:
        return None
    token = data.get('access_token')
    if not token:
        st.error("Token refresh returned no access token.")
    return token


def search_patients(access_token, search_term):
    return charm_response(requests.get, "Patient search",
        'https://apiehr.charmtracker.com/api/ehr/v1/patients',
        params={'facility_id': 'ALL', 'full_name_contains': search_term},
        headers={'Authorization': f'Bearer {access_token}',
                 'api_key': st.secrets.get("API_KEY", os.getenv("API_KEY"))})


def get_lab_results(access_token, patient_id):
    return charm_response(requests.get, "Lab retrieval",
        f'https://apiehr.charmtracker.com/api/ehr/v1/fhir/patients/{patient_id}/labresults',
        headers={'Authorization': f'Bearer {access_token}',
                 'api_key': st.secrets.get("API_KEY", os.getenv("API_KEY"))})

# API imports retain collection dates, units and duplicate observations in lab_preload.py.

# Extraction Functions
def filter_metadata(text):
    skip_keywords = [
        "Patient", "Specimen", "Date", "Labcorp", "Physician", "Ordered", "Account", "Phone",
        "Age", "Sex", "Fasting", "Collected", "Received", "Reported", "©", "Please", "Prediabetes",
        "Diabetes", "Glycemic", "Branch", "Control", "NPI", "Values obtained", "Roche", "methodology",
        "interchangeably", "Results", "evidence", "malignant", "Disclaimer", "Icon", "Performing",
        "Details", "AUA", "prostatectomy", "recurrence", "Adult male", "Travison", "PMID",
        "Previous Result", "Reference Interval", "Current Result", "Flag", "Units", "Enterprise",
        "healthy nonobese males", "JCEM", "BMI", "between 19 and 39 years old", "28324103",
        "Immature Granulocytes", "Immature Grans (Abs)", "CBC With Differential/Platelet",
        "or greater followed by a subsequent confirmatory"
    ]
    lines = text.split("\n")
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if (line and re.search(r'[0-9]', line) and not any(kw in line for kw in skip_keywords) and
            not re.match(r'^\d+\.\d+$', line)):
            filtered_lines.append(line)
    return "\n".join(filtered_lines)

def parse_marker_values(text):
    pattern = re.compile(
        r'^([A-Za-z][A-Za-z\s\(\),./-]+?)(?:\s+\$\^\{[^{}]*\}\$)?(?:\s+0[1-3])?\s+([><]?\d+(?:\.\d+)?)(?:\s+.*)?$',
        re.MULTILINE
    )
    matches = pattern.findall(text)
    marker_values = []
    seen_markers = {}
    for marker, value in matches:
        marker = re.sub(r'\$\^\{[^{}]*\}\$', '', marker).strip()
        if marker == "Sex Horm Binding Glob":
            marker = "Sex Horm Binding Glob, Serum"
        marker = manual_map.get(marker, marker)
        if marker not in seen_markers:
            seen_markers[marker] = True
            marker_values.append({
                "Marker": marker,
                "Value": value,
                "Units": "N/A",
                "Reference Interval": "N/A"
            })
    return marker_values

# Sidebar
st.sidebar.title("Member Details")
if contact_info:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", list(contact_info.keys()))
else:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", ["Manager1", "Manager2"])

st.sidebar.markdown("### Search Patient via CharmHealth API")
if 'patients' not in st.session_state:
    st.session_state.patients = []
search_term = st.sidebar.text_input("Search Patient by Name (or partial name)", value="")
#st.sidebar.markdown("### Debug: Manual Credential Input")
#st.session_state["refresh_token"] = st.sidebar.text_input("Refresh Token", value="", key="refresh_token_input")
#st.session_state["client_id"] = st.sidebar.text_input("Client ID", value="", key="client_id_input")
#st.session_state["client_secret"] = st.sidebar.text_input("Client Secret", value="", type="password", key="client_secret_input")
if st.sidebar.button("Search Patients"):
    with st.spinner("Searching patients..."):
        access_token = refresh_access_token()
        if access_token:
            patient_search_results = search_patients(access_token, search_term)
            if patient_search_results and 'patients' in patient_search_results:
                st.session_state.patients = patient_search_results['patients']
                st.sidebar.success(f"Found {len(st.session_state.patients)} matching patients.")
            else:
                st.session_state.patients = []
                st.sidebar.warning("No patients found or error in search results.")
        else:
            st.sidebar.error("Cannot proceed without a valid access token.")
patient_options = [(patient['patient_id'], patient.get('full_name', 'Unknown')) for patient in st.session_state.patients]
selected_patient = st.sidebar.selectbox(
    "Select a Patient",
    options=[f"{name} (ID: {pid})" for pid, name in patient_options],
    index=0 if patient_options else None,
    key="patient_selectbox"
)
patient_id = None
patient_sex = None
patient_name = ""
if selected_patient:
    patient_id = next(pid for pid, name in patient_options if f"{name} (ID: {pid})" == selected_patient)
    patient_data = next(p for p in st.session_state.patients if p['patient_id'] == patient_id)
    patient_name = patient_data.get('full_name', '')
    patient_sex = patient_data.get('sex', '').lower()
st.session_state.selected_patient = selected_patient
clear_patient_state(st.session_state, patient_id, patient_name)
member_name = st.sidebar.text_input("Enter Member/Patient Name", key="member_name_input")

if selected_patient and st.sidebar.button("Fetch Lab Results from API"):
    with st.spinner("Fetching lab results..."):
        access_token = refresh_access_token()
        if access_token:
            lab_data = get_lab_results(access_token, patient_id)
            if lab_data is not None:
                accept_api_payload(st.session_state, lab_data)
                st.sidebar.success("Lab results fetched. Review the result set and preloaded values below.")
            else:
                st.sidebar.warning("Fetch failed; existing results were retained. Check the selected source before proceeding.")
        else:
            st.sidebar.error("Cannot proceed without a valid access token. Existing results were retained.")

api_batches = st.session_state.get('api_batches', [])
selected_api_batch = None
if api_batches:
    labels = {batch['id']: batch['label'] for batch in api_batches}
    batch_id = st.sidebar.selectbox("Choose API collection/result set", list(labels),
                                    index=None, key='api_batch_choice', format_func=labels.get,
                                    placeholder="Choose one collection/result set")
    selected_api_batch = next((b for b in api_batches if b['id'] == batch_id), None)
    if selected_api_batch:
        st.caption(f"API source: {selected_api_batch['label']}")
    else:
        st.info("Multiple API result sets were found. Choose one collection/result set before values are preloaded. Dates are never combined automatically.")

# File Upload Section
st.header("Upload LabCorp Report")
uploaded_file = st.file_uploader("Choose a LabCorp report file", type=["pdf", "txt"], key=f"lab_upload:{patient_id}")
extracted_data = []
extracted_markers_dict = {}
patient_name_extracted = None
if uploaded_file:
    # Extraction belongs only to the file currently present in this uploader.
    # Empty/failed replacements must not retain the preceding file's values.
    st.session_state.extracted_markers_dict = {}
    text = ""
    if uploaded_file.name.lower().endswith(".pdf"):
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
    elif uploaded_file.name.lower().endswith(".txt"):
        try:
            text = uploaded_file.read().decode("utf-8")
        except Exception as e:
            st.error(f"Error reading TXT file: {e}")
    if text:
        first_line = text.split("\n")[0].strip()
        if ',' in first_line:
            parts = first_line.split(',')
            last = parts[0].strip()
            first = parts[1].strip().split()[0]
            patient_name_extracted = f"{first} {last}"
        filtered_text = filter_metadata(text)
        extracted_data = parse_marker_values(filtered_text)
        if extracted_data:
            st.subheader("Extracted Lab Results from File")
            df_extracted = pd.DataFrame(extracted_data)
            st.dataframe(df_extracted)
            extracted_markers_dict = {item["Marker"]: str(item["Value"]) for item in extracted_data}
            st.session_state.extracted_markers_dict = extracted_markers_dict
        else:
            st.session_state.extracted_markers_dict = {}
            st.error("No lab marker data found.")
else:
    st.session_state.extracted_markers_dict = {}

# Marker Selection and Input
def normalize_marker(marker):
    marker = marker.lower().strip()
    marker = re.sub(r'\([^)]*\)', '', marker)
    marker = re.sub(r'\s*(absolute|calculated|cal|nih)', '', marker).strip()
    corrections = {
        'hematocri': 'hematocrit',
        'psa value': 'prostate specific antigen',
        'lymphs': 'lymphocytes',
        'eos': 'eosinophils',
        'basos': 'basophils'
    }
    for typo, correct in corrections.items():
        if typo in marker:
            marker = marker.replace(typo, correct)
    marker = re.sub(r'[^a-z0-9\s]', '', marker).strip()
    return marker

selected_markers = []
lab_results = {}
if lab_markers:
    groups = list(lab_markers)
    st.markdown("### Select Group of Lab Markers:")
    selected_group = st.selectbox("Choose a group:", groups, index=groups.index('Men') if 'Men' in groups else 0)
    st.session_state.selected_group = selected_group
    available_markers = lab_markers[selected_group]
    api_values, api_issues, available_markers = prepare_api_import(selected_api_batch, manual_map, available_markers)
    st.session_state.api_markers_dict = api_values
    for issue in api_issues:
        st.warning(issue)
    if selected_api_batch:
        st.subheader("API Lab Results — selected result set")
        st.dataframe(pd.DataFrame([{'Marker': row['marker'], 'Value': row['value'], 'Units': row['unit'],
                                   'Reported interval': reference_label(row.get('reference_range')),
                                   'Method': row.get('method') or 'Not supplied',
                                   'Laboratory': row.get('lab_source') or 'Not supplied'} for row in selected_api_batch['rows']]))
    extracted = st.session_state.get('extracted_markers_dict', {})
    # Avoid mixing an uploaded report with an API collection without a date match.
    # Uploaded-file extraction has no reliable collection-date model in this app.
    if api_batches and extracted:
        st.warning("An uploaded report is also present. Only the selected API result set is preloaded; uploaded values are not combined with it.")
    combined = api_values if api_batches else extracted
    matched_values = {}
    unmatched = []
    for name, value in combined.items():
        marker = manual_map.get(name, name)
        if marker not in available_markers and not api_batches:
            matches = [m for m in available_markers if normalize_marker(m) == normalize_marker(name)]
            marker = matches[0] if len(matches) == 1 else None
        if marker in available_markers and finite_number(value) is not None:
            matched_values[marker] = finite_number(value)
        else:
            unmatched.append(name)
    if unmatched:
        st.warning("Some extracted markers could not be preloaded. Review the source and enter valid results manually.")
        st.write(unmatched)
    signature = (patient_id, selected_group, st.session_state.get('api_payload_fingerprint'),
                 selected_api_batch['id'] if selected_api_batch else None, fingerprint(combined))
    sync_form_state(st.session_state, signature, available_markers, matched_values)
    st.markdown("### Select Lab Markers to Include:")
    grouped_by_panel = {}
    for marker, info in available_markers.items():
        if not info.get('selectable', True):
            continue
        grouped_by_panel.setdefault(info.get('panel', 'Other'), []).append(marker)
    desired_panel_order = [
        "Hormone, Gonadotropin & Neurosteroid Panel", "Thyroid, Growth Factors & Glucose", "Metabolic Panel",
        "CBC w/ Differential and Platelet", "Lipid Panel", "Iron Markers", "Inflammatory Markers"
    ]
    panels = [p for p in desired_panel_order if p in grouped_by_panel]
    panels += sorted(p for p in grouped_by_panel if p not in desired_panel_order)
    for panel in panels:
        widget_key = f'lab_panel:{selected_group}:{panel}'
        with st.expander(panel, expanded=bool(st.session_state.get(widget_key))):
            selected_markers.extend(st.multiselect(f"Select markers from {panel}:", sorted(grouped_by_panel[panel]), key=widget_key))
else:
    st.error("Lab markers could not be loaded.")
if selected_markers:
    st.markdown("### Input Lab Results:")
    for marker in selected_markers:
        widget_key = f'lab_value:{selected_group}:{marker}'
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state.get('lab_manual_values', {}).get(marker)
        lab_results[marker] = st.number_input(f"Enter result for {marker}:", value=None, key=widget_key,
                                             on_change=remember_result, args=(st.session_state, marker, widget_key),
                                             help=f"Units: {available_markers[marker].get('units', 'not specified')}. {available_markers[marker].get('description', '')} No automatic unit conversion is applied.")
        info = available_markers[marker]
        assessment = assess_result(lab_results[marker], info)
        target_label = 'Optimal range (temporary lab target)' if info.get('optimal_origin') == 'new' else 'Optimal range'
        st.caption(f"Lab interval: {info.get('clinical_range', 'Not supplied')} {info.get('clinical_units', info.get('units', ''))}")
        st.caption(f"{target_label}: {info.get('optimal_range', 'Not supplied')} {info.get('optimal_units', info.get('units', ''))}")
        if assessment['category'] == 'unscored':
            if not info.get('optimal_units_compatible', True) or not info.get('optimal_identity_confirmed', True):
                st.warning('Unscored: ' + assessment['reason'])
            else:
                st.caption('Unscored: ' + assessment['reason'])
        else:
            st.caption(f"Assessment: {assessment['category'].capitalize()} ({assessment['points']:g} points)")
        if info.get('assumed_ratio_unit'):
            st.caption('Dimensionless BUN/Creatinine ratio: an absent API unit is accepted for this marker.')
        if info.get('assay_method') or info.get('source_method'):
            st.caption(f"Assay: {info.get('source_method') or info.get('assay_method')} · Laboratory: {info.get('lab_source', 'Not supplied')}")

# Visualization Functions
def parse_range(range_str):
    bounds = parse_interval(range_str)
    if bounds and bounds['low'] is not None and bounds['high'] is not None:
        return bounds['low'], bounds['high']
    return None, None


def create_range_chart(marker_name, units, clinical_range, optimal_range, user_value, temporary_target=False):
    clinical_min, clinical_max = parse_range(clinical_range)
    optimal_min, optimal_max = parse_range(optimal_range)
    try:
        user_numeric = float(user_value)
    except ValueError:
        return None
    if None in (clinical_min, clinical_max, optimal_min, optimal_max):
        return None
    overall_min = min(clinical_min, optimal_min, user_numeric)
    overall_max = max(clinical_max, optimal_max, user_numeric)
    padding = 0.15 * (overall_max - overall_min)
    x_min = overall_min - padding
    x_max = overall_max + padding
    fig, ax = plt.subplots(figsize=(6, 2))
    bar_height = 0.075
    optimal_y = 0.0
    clinical_y = optimal_y + bar_height
    ax.broken_barh([(clinical_min, clinical_max - clinical_min)], (clinical_y, bar_height),
                   facecolors=in_range_color, edgecolor='none', label='Clinical Range')
    ax.broken_barh([(optimal_min, optimal_max - optimal_min)], (optimal_y, bar_height),
                   facecolors=PRIMARY_COLOR, edgecolor='none', label='Optimal (temporary)' if temporary_target else 'Optimal Range')
    ax.axvline(user_numeric, color=vibrant_red, linewidth=3, label='Your Value')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, clinical_y + bar_height)
    ax.set_yticks([])
    ax.set_xlabel(f"{marker_name} ({units})")
    ax.legend(loc='best', ncol=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig

# Analytics Logging
def log_analytics(selected_manager, selected_markers, lab_results, available_markers):
    try:
        local_timezone = pytz.timezone("UTC")
        timestamp = datetime.now(local_timezone).strftime("%Y-%m-%d %H:%M:%S")
        for marker in selected_markers:
            user_value = lab_results.get(marker)
            assessment = assess_result(user_value, available_markers[marker])
            if assessment['points'] is None:
                continue
            try:
                user_numeric = float(user_value)
            except ValueError:
                continue
            is_optimal_out = int(assessment['category'] != 'optimal')
            is_clinical_out = int(assessment['clinical'] is False)
            cursor.execute(
                """
                INSERT INTO report_analytics (membership_manager, marker, is_optimal_out, is_clinical_out, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (selected_manager, marker, is_optimal_out, is_clinical_out, timestamp)
            )
        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Failed to log analytics: {e}")

# PDF Merging Helpers
def overwrite_more_information(template_path, output_path, member_name, selected_manager):
    try:
        local_timezone = pytz.timezone("America/Los_Angeles")
        current_date = datetime.now(local_timezone).strftime("%m-%d-%Y")
        manager_info = contact_info.get(selected_manager, {"email": "N/A", "phone": "N/A"})
        manager_name = f"{manager_info.get('first_name', 'Unknown')} {manager_info.get('last_name', 'Unknown')}"
        manager_email = manager_info.get("email", "N/A")
        manager_phone = manager_info.get("phone", "N/A")
        doc = fitz.open(template_path)
        first_page = doc[0]
        for text, y in [
            (member_name or 'Not Provided', 523),
            (manager_phone, 567),
            (manager_email, 610),
        ]:
            font_size = min(17, 470 / max(fitz.get_text_length(text, fontname="helv", fontsize=1), 1))
            first_page.insert_text((84, y), text, fontsize=font_size, color=(1, 1, 1), fontname="helv")
        doc.save(output_path)
        return output_path
    except Exception as e:
        st.error(f"Error in overwrite_more_information: {e}")
        return None

def merge_pdfs(template_path, generated_path, output_path):
    try:
        template_pdf = fitz.open(template_path)
        generated_pdf = fitz.open(generated_path)
        output_pdf = fitz.open()
        output_pdf.insert_pdf(template_pdf, from_page=0, to_page=2)
        output_pdf.insert_pdf(generated_pdf)
        output_pdf.insert_pdf(template_pdf, from_page=3)
        output_pdf.save(output_path)
        output_pdf.close()
        template_pdf.close()
        generated_pdf.close()
    except Exception as e:
        st.error(f"Error during PDF merging: {e}")

def set_font_with_fallback(pdf_obj, font, style, size, text):
    fallback_font = "DejaVuSans"
    if font == "Exo2" and ("γ" in text or "●" in text):
        pdf_obj.set_font(fallback_font, style, size)
    else:
        pdf_obj.set_font(font, style, size)

# PDF Generation
if st.button("Generate PDF"):
    if not member_name.strip():
        st.error("Please enter a Member/Patient Name before generating the PDF.")
    elif not selected_markers:
        st.warning("No lab markers selected.")
    elif not any(lab_results.get(marker) is not None for marker in selected_markers):
        st.error("No valid numeric lab results entered.")
    else:
        pdf = FPDF()
        pdf.add_font("Exo2", "", FONT_PRIMARY)
        pdf.add_font("Exo2", "B", "Exo2-Bold.ttf")
        pdf.add_font("DejaVuSans", "", "DejaVuSans.ttf")
        pdf.add_font("DejaVuSans", "B", "DejaVuSans-Bold.ttf")
        metrics = score_lab_results(selected_markers, lab_results, available_markers)
        total_markers = metrics['total']
        count_optimal, count_inrange = metrics['optimal'], metrics['clinical']
        count_out, count_unscored = metrics['outside'], metrics['unscored']
        optimal_score = metrics['score_percent']
        score_label = f"{optimal_score:.0f}" if optimal_score is not None else 'N/A'
        log_analytics(selected_manager, selected_markers, lab_results, available_markers)
        pdf.add_page()
        pdf.set_fill_color(6, 182, 212)
        pdf.rect(0, 0, 210, 30, style='F')
        pdf.set_y(6)
        pdf.set_text_color(255, 255, 255)
        set_font_with_fallback(pdf, "Exo2", "B", 22, f"Your Optimal Score: {score_label}")
        pdf.cell(210, 18, f" Your Optimal Score: {score_label}", align="C", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)
        pdf.set_text_color(250, 240, 230)
        pdf.set_xy(157, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(0, 10, f"{total_markers} Biomarkers Analyzed", border=0)
        pdf.set_xy(10, 24)
        pdf.set_font('Exo2', '', 10)
        pdf.cell(190, 5, f"Score uses {metrics['scored']} scorable results; {metrics['unscored']} unscored results are excluded.", align='C')
        categories = ['Out of Range', 'Optimal', 'Clinical Range', 'Unscored']
        values = [count_out, count_optimal, count_inrange, count_unscored]
        colors = ['#FF5555', '#06B6D4', '#FFA500', '#B0B0B0']
        fig, ax = plt.subplots(figsize=(14, 22))
        bars = ax.bar(categories, values, color=colors)
        ax.set_ylabel('Number of Markers', fontsize=16)
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(bottom=False, left=False)
        ax.set_xticks(range(len(categories)))
        ax.set_xticklabels(categories, fontsize=20)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.2, int(yval), ha='center', va='bottom', fontsize=20)
        plt.tight_layout(pad=0.1)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            chart_file = tmpfile.name
            fig.savefig(chart_file, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        pdf.image(chart_file, x=32.5, y=32, w=160, h=192)
        os.remove(chart_file)
        pdf.set_y(234)
        legend_start_x = 32.5
        legend_box_size = 6
        spacing = 4
        for label, count, color in [
            ('Out of Range', count_out, (255,85,85)),
            ('Optimal Range', count_optimal, (6,182,212)),
            ('Clinical Range', count_inrange, (255,165,0)),
            ('Unscored', count_unscored, (176,176,176)),
        ]:
            pdf.set_xy(legend_start_x, pdf.get_y())
            pdf.set_fill_color(*color)
            pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style='F')
            pdf.set_x(legend_start_x + legend_box_size + spacing)
            pdf.set_text_color(0,0,0)
            pdf.set_font('Exo2','',12)
            pdf.cell(40,10,label,border=0)
            pdf.set_text_color(115,115,115)
            percentage = 100 * count / total_markers if total_markers else 0
            pdf.cell(0,10,f'{percentage:.0f}%',border=0,new_x=XPos.LMARGIN,new_y=YPos.NEXT)
        grouped_markers = {}
        for marker in selected_markers:
            panel = available_markers[marker].get('panel', 'Other')
            grouped_markers.setdefault(panel, []).append(marker)
        # Standardize panel order to match marker selection
        for panel in desired_panel_order + [p for p in grouped_markers if p not in desired_panel_order]:
            if panel in grouped_markers:
                pdf.add_page()
                marker_count = 0
                pdf.set_fill_color(6, 182, 212)
                pdf.rect(0, 0, 210, 20, style='F')
                pdf.set_y(6)
                pdf.set_text_color(255, 255, 255)
                set_font_with_fallback(pdf, "Exo2", "B", 20, panel)
                pdf.cell(0, 10, panel, align="C", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(10)
                for marker in grouped_markers[panel]:
                    pdf.set_font('Exo2', '', 12)
                    description_height = pdf.multi_cell(0, 6, available_markers[marker].get('description', ''), dry_run=True, output='HEIGHT')
                    if marker_count == 3 or pdf.will_page_break(description_height + 85):
                        pdf.add_page()
                        marker_count = 0
                        pdf.set_text_color(6, 182, 212)
                        set_font_with_fallback(pdf, "Exo2", "B", 20, panel)
                        pdf.cell(0, 12, panel, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.set_draw_color(115, 115, 115)
                        pdf.set_line_width(0.5)
                        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(3)
                    marker_count += 1
                    pdf.set_text_color(6, 182, 212)
                    set_font_with_fallback(pdf, "Exo2", "B", 18, marker)
                    pdf.cell(0, 10, marker, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.set_text_color(115, 115, 115)
                    set_font_with_fallback(pdf, "Exo2", "", 12, marker)
                    pdf.multi_cell(0, 6, available_markers[marker].get('description', ''))
                    pdf.ln(2)
                    value = lab_results.get(marker)
                    if value is None:
                        pdf.cell(0, 10, "No value entered.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(5)
                        continue
                    user_numeric = float(value)
                    dot_color = None
                    assessment = assess_result(user_numeric, available_markers[marker])
                    clinical_min, clinical_max = parse_range(available_markers[marker]['clinical_range'])
                    optimal_min, optimal_max = parse_range(available_markers[marker]['optimal_range'])
                    dot_color = {'optimal':(6,182,212), 'clinical':(255,165,0), 'outside':(255,85,85)}.get(assessment['category'])
                    fig = create_range_chart(
                        marker,
                        available_markers[marker]['units'],
                        available_markers[marker]['clinical_range'],
                        available_markers[marker]['optimal_range'],
                        user_numeric, temporary_target=available_markers[marker].get('optimal_origin') == 'new'
                    ) if assessment['points'] is not None else None
                    if fig:
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                            chart_file = tmpfile.name
                            fig.savefig(chart_file, bbox_inches='tight')
                        plt.close(fig)
                        current_x = pdf.get_x()
                        current_y = pdf.get_y()
                        pdf.image(chart_file, x=current_x, y=current_y, w=120, h=30)
                        os.remove(chart_file)
                        result_text = f"Result: {value} {available_markers[marker]['units']}"
                        pdf.set_xy(current_x + 125, current_y)
                        pdf.set_font("Exo2", "", 12)
                        pdf.cell(0, 30, result_text, border=0)
                        result_text_width = pdf.get_string_width(result_text) + 2
                        pdf.set_xy(current_x + 125 + result_text_width, current_y)
                        if dot_color:
                            pdf.set_text_color(*dot_color)
                            pdf.set_font("DejaVuSans", "B", 16)
                            pdf.cell(0, 30, "●", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                            pdf.set_text_color(0, 0, 0)
                            pdf.set_font("Exo2", "", 14)
                        else:
                            pdf.ln(30)
                    else:
                        pdf.multi_cell(0, 7, f"Result: {value} {available_markers[marker]['units']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        note = ('Not scored: ' + assessment['reason']) if assessment['points'] is None else 'Clinical and Optimal ranges shown below.'
                        pdf.multi_cell(0, 7, note, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(1)
                    clinical_label = "Lab Reference:"
                    set_font_with_fallback(pdf, "Exo2", "", 14, clinical_label)
                    pdf.set_text_color(115, 115, 115)
                    clinical_value = f" {available_markers[marker]['clinical_range']} {available_markers[marker].get('clinical_units', available_markers[marker]['units'])}"
                    pdf.multi_cell(0, 7, clinical_label + clinical_value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    optimal_label = "Optimal Range (temporary lab target):" if available_markers[marker].get("optimal_origin") == "new" else "Optimal Range:"
                    set_font_with_fallback(pdf, "Exo2", "", 14, optimal_label)
                    pdf.set_text_color(115, 115, 115)
                    optimal_value = f" {available_markers[marker]['optimal_range']} {available_markers[marker].get('optimal_units', available_markers[marker]['units'])}"
                    pdf.multi_cell(0, 7, optimal_label + optimal_value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(5)
        # Each report owns its output paths, even when coaches generate concurrently.
        with tempfile.TemporaryDirectory(prefix="lab-report-") as report_dir:
            generated_pdf = os.path.join(report_dir, "generated_lab_report.pdf")
            pdf.output(generated_pdf)
            template_pdf = "LabResultsV3.pdf"
            updated_template = overwrite_more_information(template_pdf,
                os.path.join(report_dir, "updated_template.pdf"), member_name, selected_manager)
            if updated_template:
                merged_pdf = os.path.join(report_dir, "final_report.pdf")
                merge_pdfs(updated_template, generated_pdf, merged_pdf)
                if os.path.isfile(merged_pdf):
                    downloadable_filename = f"{member_name.replace(' ', '_')}_Lab_Results.pdf"
                    with open(merged_pdf, "rb") as file:
                        report_bytes = file.read()
                    st.download_button("Download Final Report", report_bytes,
                                       file_name=downloadable_filename, mime="application/pdf")

st.text(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
conn.close()
