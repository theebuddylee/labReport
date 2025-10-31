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

# Load environment variables for local testing
load_dotenv()

# Authentication Setup (Built-in OIDC/OAuth)
if not st.user.is_logged_in:
    st.markdown("# Welcome to Lab Results Report Generator")
    if st.button("Log in with Google"):
        st.login()  # Redirects to Google for auth
    st.stop()  # Halt app until logged in
else:
    # Check domain restriction (fallback for External OAuth app)
    if not st.user.email.endswith('@1stoptimal.com'):
        st.error("Access denied: Only @1stoptimal.com emails are allowed.")
        if st.button("Log out"):
            st.logout()
        st.stop()

    # Add logout button in sidebar
    if st.sidebar.button("Log out"):
        st.logout()

    # Personalized greeting
    st.sidebar.markdown(f"Welcome, {st.user.name}! ({st.user.email})")

# Branding and Styling
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
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            st.error(f"Error decoding JSON from {url}")
            return {}
    else:
        st.error(f"Failed to load {filename}. HTTP {response.status_code}")
        return {}
contact_info = load_json_from_github("contact_info.json")
lab_markers = load_json_from_github("lab_markers.json")

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
    "lymphs": "Lymphocytes",
    "eos": "Eosinophils",
    "basos": "Basophils",
    "bun": "Blood Urea Nitrogen (BUN)",
    "protein total": "Total Protein",
    "bilirubin total": "Total Bilirubin",
    "ast sgot": "Aspartate Aminotransferase (AST)",
    "alt sgpt": "Alanine Aminotransferase (ALT)",
    "cholesterol total": "Total Cholesterol",
    "testosterone": "Total Testosterone",
    "hdl cholesterol": "HDL",
    "testosterone total lcms a": "Total Testosterone",
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
    "neutrophils absolute": "Neutrophils",
    "lymphs absolute": "Lymphocytes",
    "monocytesabsolute": "Monocytes",
    "eos absolute": "Eosinophils",
    "baso absolute": "Basophils",
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
    "Neutrophils": "Neutrophils",
    "Lymphs": "Lymphocytes",
    "Monocytes": "Monocytes",
    "Eos": "Eosinophils",
    "Basos": "Basophils",
    "Neutrophils (Absolute)": "Neutrophils",
    "Lymphs (Absolute)": "Lymphocytes",
    "Monocytes(Absolute)": "Monocytes",
    "Eos (Absolute)": "Eosinophils",
    "Baso (Absolute)": "Basophils",
    "Glucose": "Glucose",
    "BUN": "Blood Urea Nitrogen (BUN)",
    "Creatinine": "Creatinine",
    "eGFR": "Estimated Glomerular Filtration Rate (eGFR)",
    "BUN/Creatinine Ratio": "BUN/Creatinine Ratio",
    "Sodium": "Sodium",
    "Potassium": "Potassium",
    "Chloride": "Chloride",
    "Carbon Dioxide, Total": "Carbon Dioxide (CO₂), Total",
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
    "Free Testosterone(Direct)": "Free Testosterone",
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
    # New mappings for Quest labs 
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
    "Neutrophils # Bld Auto": "Neutrophils",
    #"Neuts Band # Bld": "Neutrophils",
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
    "CO2 SerPl-sCnc": "Carbon Dioxide (CO₂), Total",
    "Calcium SerPl-mCnc": "Calcium"
}

# CharmHealth API Functions
def refresh_access_token():
    # Try sidebar inputs first for debugging
    refresh_token = st.session_state.get("refresh_token", "")
    client_id = st.session_state.get("client_id", "")
    client_secret = st.session_state.get("client_secret", "")

    # Fall back to st.secrets or .env
    if not (refresh_token and client_id and client_secret):
        try:
            refresh_token = st.secrets.get("REFRESH_TOKEN", os.getenv("REFRESH_TOKEN"))
            client_id = st.secrets.get("CLIENT_ID", os.getenv("CLIENT_ID"))
            client_secret = st.secrets.get("CLIENT_SECRET", os.getenv("CLIENT_SECRET"))
        except Exception:
            st.error("Credentials not found in st.secrets or .env file.")
            return None

    # Debug: Log credential usage (non-sensitive parts)
    # st.write(f"Using CLIENT_ID: {client_id[:10]}... (first 10 chars)")
    # st.write(f"Using REFRESH_TOKEN: {refresh_token[:10]}... (first 10 chars)")

    # Use V3's URL query string and Cookie header
    url = f'https://accounts.charmtracker.com/oauth/v2/token?refresh_token={refresh_token}&client_id={client_id}&client_secret={client_secret}&grant_type=refresh_token'
    headers = {
        'Content-Type': 'application/json',
        'Cookie': '_zcsr_tmp=24918cc4-64c5-49be-b6f4-edc5ee7d2068; iamcsr=24918cc4-64c5-49be-b6f4-edc5ee7d2068'
    }
    response = requests.post(url, headers=headers, json={})
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error(f"Failed to refresh token: {response.status_code} - {response.text}")
        return None

def search_patients(access_token, search_term):
    url = f'http://apiehr.charmtracker.com/api/ehr/v1/patients?facility_id=ALL&full_name_contains={search_term}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'api_key': st.secrets.get("API_KEY", os.getenv("API_KEY"))
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to search patients: {response.status_code} - {response.text}")
        return None

def get_lab_results(access_token, patient_id):
    url = f'http://apiehr.charmtracker.com/api/ehr/v1/fhir/patients/{patient_id}/labresults'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'api_key': st.secrets.get("API_KEY", os.getenv("API_KEY"))
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to get lab results: {response.status_code} - {response.text}")
        return None

def format_lab_results_to_markers(lab_data):
    if not lab_data or 'data' not in lab_data or 'entry' not in lab_data['data']:
        st.warning("No lab data provided or invalid structure.")
        return {}
    marker_values = {}
    unmapped_markers = set()
    entries = lab_data['data']['entry']
    for entry in entries:
        resource = entry.get('resource', {})
        components = resource.get('component', [])
        for comp in components:
            api_marker = comp.get('code', {}).get('text', 'Unknown')
            value = comp.get('valueQuantity', {}).get('value', 'N/A')
            if api_marker in manual_map:
                standard_marker = manual_map[api_marker]
                try:
                    marker_values[standard_marker] = float(value)
                except (ValueError, TypeError):
                    marker_values[standard_marker] = None
            else:
                unmapped_markers.add(api_marker)
        if 'valueQuantity' in resource:
            api_marker = resource.get('code', {}).get('text', 'Unknown')
            value = resource.get('valueQuantity', {}).get('value', 'N/A')
            if api_marker in manual_map:
                standard_marker = manual_map[api_marker]
                try:
                    marker_values[standard_marker] = float(value)
                except (ValueError, TypeError):
                    marker_values[standard_marker] = None
            else:
                unmapped_markers.add(api_marker)
    if unmapped_markers:
        st.warning(f"Unmapped API markers: {sorted(unmapped_markers)}")
    return marker_values

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

default_member_name = ""
if "patients" in st.session_state and st.session_state.patients and "selected_patient" in st.session_state:
    patient_options = [(p['patient_id'], p.get('full_name', 'Unknown')) for p in st.session_state.patients]
    selected_patient = st.session_state.get("selected_patient", None)
    if selected_patient:
        for pid, name in patient_options:
            if f"{name} (ID: {pid})" == selected_patient:
                default_member_name = name
                break
member_name = st.sidebar.text_input("Enter Member/Patient Name", value=default_member_name, key="member_name_input")

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
if selected_patient:
    st.session_state.selected_patient = selected_patient
patient_sex = None
if selected_patient:
    patient_id = next(pid for pid, name in patient_options if f"{name} (ID: {pid})" == selected_patient)
    patient_data = next(p for p in st.session_state.patients if p['patient_id'] == patient_id)
    patient_sex = patient_data.get('sex', '').lower()

# Fetch Lab Results Button
api_markers_dict = {}
if selected_patient and st.sidebar.button("Fetch Lab Results from API"):
    with st.spinner("Fetching lab results..."):
        patient_id = next(pid for pid, name in patient_options if f"{name} (ID: {pid})" == selected_patient)
        access_token = refresh_access_token()
        if access_token:
            lab_data = get_lab_results(access_token, patient_id)
            if lab_data:
                api_markers_dict = format_lab_results_to_markers(lab_data)
                st.session_state.api_markers_dict = api_markers_dict
                st.sidebar.success("Lab results fetched successfully!")
                st.subheader("API Lab Results")
                st.dataframe(pd.DataFrame(api_markers_dict.items(), columns=["Marker", "Value"]))
            else:
                st.session_state.api_markers_dict = {}
                st.sidebar.warning("No lab results available to display.")
        else:
            st.session_state.api_markers_dict = {}
            st.sidebar.error("Cannot proceed without a valid access token.")

# File Upload Section
st.header("Upload LabCorp Report")
uploaded_file = st.file_uploader("Choose a LabCorp report file", type=["pdf", "txt"])
extracted_data = []
extracted_markers_dict = {}
patient_name_extracted = None
if uploaded_file:
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
    if "extracted_markers_dict" not in st.session_state:
        st.session_state.extracted_markers_dict = {}

# Combine Data Sources
combined_markers_dict = st.session_state.get("extracted_markers_dict", {}).copy()
if "api_markers_dict" in st.session_state:
    combined_markers_dict.update(st.session_state.api_markers_dict)

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
    # Determine if data is from API or PDF
    is_api_data = "selected_patient" in st.session_state and st.session_state["selected_patient"]
    if is_api_data:
        # Default to "Men" for API data
        default_group = "Men"
    else:
        # Preserve existing logic for PDF uploads
        default_group = "Men" if patient_sex == "male" else "Women" if patient_sex == "female" else "Post Menopausal Women"
    try:
        default_index = list(lab_markers.keys()).index(default_group)
    except ValueError:
        default_index = 0
        st.warning(f"Default group '{default_group}' not found in lab_markers. Using first available group.")
    st.markdown("### Select Group of Lab Markers:")
    selected_group = st.selectbox("Choose a group:", list(lab_markers.keys()), index=default_index)
    st.session_state.selected_group = selected_group
    available_markers = lab_markers[selected_group]

    preselected_markers = []
    matched_extracted = set()
    for avail_marker in available_markers.keys():
        for extracted_marker in combined_markers_dict.keys():
            if extracted_marker in manual_map and manual_map[extracted_marker] == avail_marker:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = combined_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break
            norm_avail = normalize_marker(avail_marker)
            norm_extracted = normalize_marker(extracted_marker)
            if norm_avail == norm_extracted:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = combined_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break

    normalized_extracted = {normalize_marker(key): key for key in combined_markers_dict.keys()}
    normalized_available = {normalize_marker(key): key for key in available_markers.keys()}
    matched_normalized = {normalize_marker(key) for key in matched_extracted}
    unmatched_normalized = [normalized_extracted[norm_key] for norm_key in normalized_extracted if norm_key not in matched_normalized]
    if unmatched_normalized:
        st.warning("The following extracted markers did not match any available markers (after normalization):")
        st.write(unmatched_normalized)

    st.markdown("### Select Lab Markers to Include:")
    grouped_by_panel = {}
    for marker, info in available_markers.items():
        panel = info.get("panel", "Other")
        grouped_by_panel.setdefault(panel, []).append(marker)
    desired_panel_order = [
        "Hormone, Gonadotropin & Neurosteroid Panel", "Thyroid, Growth Factors & Glucose", "Metabolic Panel",
        "CBC w/ Differential and Platelet", "Lipid Panel", "Iron Markers", "Inflammatory Markers"
    ]
    for panel in desired_panel_order:
        if panel in grouped_by_panel:
            markers_in_panel = sorted(grouped_by_panel[panel])
            default_markers = sorted([m for m in markers_in_panel if m in preselected_markers])
            with st.expander(panel, expanded=False):
                selected_from_panel = st.multiselect(f"Select markers from {panel}:", markers_in_panel, default=default_markers, key=panel)
                selected_markers.extend(selected_from_panel)
    remaining_panels = [p for p in grouped_by_panel.keys() if p not in desired_panel_order]
    for panel in sorted(remaining_panels):
        markers_in_panel = sorted(grouped_by_panel[panel])
        default_markers = sorted([m for m in markers_in_panel if m in preselected_markers])
        with st.expander(panel, expanded=False):
            selected_from_panel = st.multiselect(f"Select markers from {panel}:", markers_in_panel, default=default_markers, key=panel)
            selected_markers.extend(selected_from_panel)
else:
    st.error("Lab markers could not be loaded.")

if selected_markers:
    st.markdown("### Input Lab Results:")
    for marker in selected_markers:
        default_val = lab_results.get(marker, None)
        try:
            default_float = float(default_val) if default_val is not None else None
        except ValueError:
            default_float = None
        lab_results[marker] = st.number_input(f"Enter result for {marker}:", value=default_float)

# Visualization Functions
def parse_range(range_str):
    if '-' in range_str:
        parts = range_str.split('-')
        try:
            low = float(parts[0].strip())
            high = float(parts[1].strip())
            return low, high
        except ValueError:
            return None, None
    return None, None

def create_range_chart(marker_name, units, clinical_range, optimal_range, user_value):
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
                   facecolors=PRIMARY_COLOR, edgecolor='none', label='Optimal Range')
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
            if user_value is None:
                continue
            try:
                user_numeric = float(user_value)
            except ValueError:
                continue
            clinical_range = parse_range(available_markers[marker]['clinical_range'])
            optimal_range = parse_range(available_markers[marker]['optimal_range'])
            is_optimal_out = 0
            is_clinical_out = 0
            if clinical_range and optimal_range:
                clinical_min, clinical_max = clinical_range
                optimal_min, optimal_max = optimal_range
                if not (optimal_min <= user_numeric <= optimal_max):
                    is_optimal_out = 1
                if not (clinical_min <= user_numeric <= clinical_max):
                    is_clinical_out = 1
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
        first_page.insert_text((70, 538), f"{member_name or 'Not Provided'}", fontsize=17, color=(0.451, 0.451, 0.451))
        first_page.insert_text((70, 577), f"{manager_phone}", fontsize=17, color=(0.451, 0.451, 0.451))
        first_page.insert_text((70, 615), f"{manager_email}", fontsize=17, color=(0.451, 0.451, 0.451))
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
        output_pdf.insert_pdf(template_pdf, from_page=3, to_page=3)
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
        total_markers = len(selected_markers)
        score_sum = 0
        count_optimal = 0
        count_inrange = 0
        count_out = 0
        for marker in selected_markers:
            user_value = lab_results.get(marker)
            if user_value is None:
                count_out += 1
                continue
            user_numeric = float(user_value)
            clinical_min, clinical_max = parse_range(available_markers[marker]['clinical_range'])
            optimal_min, optimal_max = parse_range(available_markers[marker]['optimal_range'])
            if (clinical_min is not None and clinical_max is not None and
                optimal_min is not None and optimal_max is not None):
                if optimal_min <= user_numeric <= optimal_max:
                    score_sum += 1
                    count_optimal += 1
                elif clinical_min <= user_numeric <= clinical_max:
                    score_sum += 0.75
                    count_inrange += 1
                else:
                    count_out += 1
            else:
                count_out += 1
        optimal_score = (score_sum / total_markers) * 100 if total_markers > 0 else 0
        log_analytics(selected_manager, selected_markers, lab_results, available_markers)
        pdf.add_page()
        pdf.set_fill_color(6, 182, 212)
        pdf.rect(0, 0, 210, 30, style='F')
        pdf.set_y(6)
        pdf.set_text_color(255, 255, 255)
        set_font_with_fallback(pdf, "Exo2", "B", 22, f"Your Optimal Score: {optimal_score:.0f}")
        pdf.cell(210, 18, f" Your Optimal Score: {optimal_score:.0f}", align="C", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)
        pdf.set_text_color(250, 240, 230)
        pdf.set_xy(157, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(0, 10, f"{total_markers} Biomarkers Analyzed", border=0)
        categories = ['Out of Range', 'Optimal', 'In Range']
        values = [count_out, count_optimal, count_inrange]
        colors = ['#FF5555', '#06B6D4', '#FFA500']
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
        pct_out = (count_out / total_markers) * 100 if total_markers > 0 else 0
        pct_optimal = (count_optimal / total_markers) * 100 if total_markers > 0 else 0
        pct_inrange = (count_inrange / total_markers) * 100 if total_markers > 0 else 0
        pdf.set_y(238)
        legend_start_x = 32.5
        legend_box_size = 6
        spacing = 4
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(255, 85, 85)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(40, 10, "Out of Range", border=0)
        pdf.set_text_color(115, 115, 115)
        pdf.cell(0, 10, f"{pct_out:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(6, 182, 212)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 10, "Optimal Range", border=0)
        pdf.set_text_color(115, 115, 115)
        pdf.cell(0, 10, f"{pct_optimal:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(255, 165, 0)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 10, "In Range", border=0)
        pdf.set_text_color(115, 115, 115)
        pdf.cell(0, 10, f"{pct_inrange:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
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
                    if marker_count == 3:
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
                    clinical_min, clinical_max = parse_range(available_markers[marker]['clinical_range'])
                    optimal_min, optimal_max = parse_range(available_markers[marker]['optimal_range'])
                    if (clinical_min is not None and clinical_max is not None and
                        optimal_min is not None and optimal_max is not None):
                        if optimal_min <= user_numeric <= optimal_max:
                            dot_color = (6, 182, 212)
                        elif user_numeric < clinical_min or user_numeric > clinical_max:
                            dot_color = (255, 85, 85)
                    fig = create_range_chart(
                        marker,
                        available_markers[marker]['units'],
                        available_markers[marker]['clinical_range'],
                        available_markers[marker]['optimal_range'],
                        user_numeric
                    )
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
                        pdf.cell(0, 10, "Chart not available (unable to parse ranges).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(1)
                    clinical_label = "Clinical Range:"
                    set_font_with_fallback(pdf, "Exo2", "", 14, clinical_label)
                    pdf.set_text_color(115, 115, 115)
                    label_width = pdf.get_string_width(clinical_label) + 2
                    pdf.cell(label_width, 10, clinical_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    clinical_value = f" {available_markers[marker]['clinical_range']}"
                    set_font_with_fallback(pdf, "Exo2", "B", 14, clinical_value)
                    pdf.set_text_color(255, 165, 0)
                    value_width = pdf.get_string_width(clinical_value) + 2
                    pdf.cell(value_width, 10, clinical_value, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    pdf.cell(10, 10, "", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    optimal_label = "Optimal Range:"
                    set_font_with_fallback(pdf, "Exo2", "", 14, optimal_label)
                    pdf.set_text_color(115, 115, 115)
                    label_width = pdf.get_string_width(optimal_label) + 2
                    pdf.cell(label_width, 10, optimal_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                    optimal_value = f" {available_markers[marker]['optimal_range']}"
                    set_font_with_fallback(pdf, "Exo2", "B", 14, optimal_value)
                    pdf.set_text_color(6, 182, 212)
                    value_width = pdf.get_string_width(optimal_value) + 2
                    pdf.cell(value_width, 10, optimal_value, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(5)
        generated_pdf = "generated_lab_report.pdf"
        pdf.output(generated_pdf)
        template_pdf = "LabResultsV2.pdf"
        updated_template = overwrite_more_information(template_pdf, "updated_template.pdf", member_name, selected_manager)
        merged_pdf = "final_report.pdf"
        merge_pdfs(updated_template, generated_pdf, merged_pdf)
        downloadable_filename = f"{member_name.replace(' ', '_')}_Lab_Results.pdf"
        with open(merged_pdf, "rb") as file:
            st.download_button("Download Final Report", file, file_name=downloadable_filename)

st.text(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
conn.close()















