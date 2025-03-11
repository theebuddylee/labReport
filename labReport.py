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

# Branding and Styling (unchanged)
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

# Load JSON Data (unchanged)
GITHUB_BASE_URL = "https://raw.githubusercontent.com/theebuddylee/HealthReport/main/data/"
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

# Database Initialization (unchanged)
conn = sqlite3.connect("lab_results.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marker TEXT,
    value TEXT,
    date TEXT
)
""")
conn.commit()

# New Extraction Functions from ExtractResults
def filter_metadata(text):
    """Filter out metadata and irrelevant lines from the text."""
    skip_keywords = [
        "Patient", "Specimen", "Date", "Labcorp", "Physician", "Ordered", "Account", "Phone",
        "Age", "Sex", "Fasting", "Collected", "Received", "Reported", "©", "Please", "Prediabetes",
        "Diabetes", "Glycemic", "Branch", "Control", "NPI", "Values obtained", "Roche", "methodology",
        "interchangeably", "Results", "evidence", "malignant", "Disclaimer", "Icon", "Performing",
        "Details", "AUA", "prostatectomy", "recurrence", "Adult male", "Travison", "PMID",
        "Previous Result", "Reference Interval", "Current Result", "Flag", "Units", "Enterprise",
        "healthy nonobese males", "JCEM", "BMI", "between 19 and 39 years old", "28324103",
        "Immature Granulocytes", "Immature Grans (Abs)", "CBC With Differential/Platelet",
        "Comp. Metabolic Panel (14)", "Lipid Panel", "FSH and LH", "Testosterone,Free and Total",
        "Hemoglobin A1c", "Prolactin", "Estradiol", "Prostate-Specific Ag", "Sex Horm Binding Glob, Serum",
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
    """Parse marker-value pairs, including units and reference intervals."""
    pattern = re.compile(
        r'^([A-Za-z][A-Za-z\s\(\),./-]+?)(?:\s+\$\^\{[^{}]*\}\$)?(?:\s+0[1-3])?\s+([><]?\d+(?:\.\d+)?|High|Low)(?:\s+([\w\/\^%\.x-]+))?(?:\s+([\d\.\-,]+))?$',
        re.MULTILINE
    )
    matches = pattern.findall(text)
    marker_values = []
    seen_markers = {}
    for match in matches:
        marker = match[0].strip()
        value = match[1]
        units = match[2] if match[2] else "N/A"
        ref_interval = match[3] if match[3] else "N/A"
        # Handle specific multi-word markers
        if marker == "Sex Horm Binding Glob":
            marker = "Sex Horm Binding Glob, Serum"
        if marker not in seen_markers:  # Avoid duplicates
            try:
                numeric_value = float(value)
                value_out = numeric_value
            except ValueError:
                value_out = value
            seen_markers[marker] = True
            marker_values.append({
                "Marker": marker,
                "Value": value_out,
                "Units": units,
                "Reference Interval": ref_interval
            })
    return marker_values

# File Upload & Lab Marker Extraction (Updated)
st.write("Upload your LabCorp report (PDF or TXT) to extract patient and lab marker details.")
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
    else:
        st.error("Unsupported file type.")

    if text:
        # Extract Patient Name (unchanged)
        first_line = text.split("\n")[0].strip()
        if ',' in first_line:
            parts = first_line.split(',')
            last = parts[0].strip()
            first = parts[1].strip().split()[0]
            patient_name_extracted = f"{first} {last}"
        else:
            patient_name_extracted = first_line

        # Extract Lab Markers using ExtractResults logic
        filtered_text = filter_metadata(text)
        extracted_data = parse_marker_values(filtered_text)

        if extracted_data:
            st.subheader("Extracted Lab Results")
            df_extracted = pd.DataFrame(extracted_data)
            df_extracted["Value"] = pd.to_numeric(df_extracted["Value"], errors='coerce')
            df_extracted["Value"] = df_extracted["Value"].apply(lambda x: "" if pd.isna(x) else str(x))
            st.dataframe(df_extracted)

            for item in extracted_data:
                key = item["Marker"].strip()
                extracted_markers_dict[key] = str(item["Value"])
        else:
            st.error("No lab marker data found. The report format may be different from expected.")
else:
    st.info("Please upload a LabCorp report file.")

# Sidebar: Member Details (unchanged)
st.sidebar.title("Member Details")
if contact_info:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", list(contact_info.keys()))
else:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", ["Manager1", "Manager2"])
default_member_name = patient_name_extracted if patient_name_extracted else ""
member_name = st.sidebar.text_input("Enter Member/Patient Name", value=default_member_name)

# Marker Group Selection and Input (Updated Manual Map)
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
    "estradiol sensitive a": "Estradiol",
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
    # Added from ExtractResults aliases
    "WBC": "White Blood Cell (WBC) Count",
    "RBC": "Red Blood Cell (RBC) Count",
    "Hemoglobin": "Hemoglobin (Hgb)",
    "Hematocrit": "Hematocrit",
    "MCV": "Mean Corpuscular Volume (MCV)",
    "MCH": "Mean Corpuscular Hemoglobin (MCH)",
    "MCHC": "Mean Corpuscular Hemoglobin Concentration (MCHC)",
    "ROM": "Red Cell Distribution Width (RDW)",
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
    "LDL Chol Calc (NIH)": "LDL (calculated)",
    "LH": "Luteinizing Hormone (LH)",
    "FSH": "Follicle-Stimulating Hormone (FSH)",
    "Testosterone": "Total Testosterone",
    "Free Testosterone(Direct)": "Free Testosterone",
    "Hemoglobin A1c": "HbA1c",
    "Prolactin": "Prolactin",
    "Estradiol": "Estradiol",
    "Prostate Specific Ag": "Prostate Specific Antigen (PSA)",
    "Sex Horm Binding Glob, Serum": "Sex Hormone Binding Globulin (SHBG)"
}

selected_markers = []
lab_results = {}
if lab_markers:
    st.markdown("### Select Group of Lab Markers:")
    selected_group = st.selectbox("Choose a group:", list(lab_markers.keys()))
    available_markers = lab_markers[selected_group]

    preselected_markers = []
    matched_extracted = set()
    for avail_marker in available_markers.keys():
        norm_avail = normalize_marker(avail_marker)
        for extracted_marker in extracted_markers_dict.keys():
            norm_extracted = normalize_marker(extracted_marker)
            if norm_avail == norm_extracted:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break
            if norm_extracted in manual_map and manual_map[norm_extracted] == avail_marker:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break

    normalized_extracted = {normalize_marker(key): key for key in extracted_markers_dict.keys()}
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
        "Hormone, Gonadotropin & Neurosteroid Panel",
        "Thyroid, Growth Factors & Glucose",
        "Metabolic Panel",
        "CBC w/ Differential and Platelet",
        "Lipid Panel",
        "Iron Markers",
        "Inflammatory Markers"
    ]
    for panel in desired_panel_order:
        if panel in grouped_by_panel:
            markers_in_panel = sorted(grouped_by_panel[panel])
            default_markers = sorted([m for m in markers_in_panel if m in preselected_markers])
            with st.expander(panel, expanded=True):
                selected_from_panel = st.multiselect(f"Select markers from {panel}:", markers_in_panel, default=default_markers, key=panel)
                selected_markers.extend(selected_from_panel)
    remaining_panels = [p for p in grouped_by_panel.keys() if p not in desired_panel_order]
    for panel in sorted(remaining_panels):
        markers_in_panel = sorted(grouped_by_panel[panel])
        default_markers = sorted([m for m in markers_in_panel if m in preselected_markers])
        with st.expander(panel, expanded=True):
            selected_from_panel = st.multiselect(f"Select markers from {panel}:", markers_in_panel, default=default_markers, key=panel)
            selected_markers.extend(selected_from_panel)
else:
    st.error("Lab markers could not be loaded.")

if selected_markers:
    st.markdown("### Input Lab Results:")
    for marker in selected_markers:
        default_val = lab_results.get(marker, "")
        lab_results[marker] = st.text_input(f"Enter result for {marker}:", value=str(default_val))
    if st.button("Save Results"):
        for marker, value in lab_results.items():
            cursor.execute(
                "INSERT INTO lab_results (marker, value, date) VALUES (?, ?, date('now'))",
                (marker, value)
            )
        conn.commit()
        st.success("Results saved successfully!")

# Visualization Functions (unchanged)
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

# PDF Merging Helpers (unchanged)
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
        first_page.insert_text((73, 598), f"{manager_name} exclusively for {member_name or 'Not Provided'}", fontsize=21, color=(1, 1, 1))
        first_page.insert_text((73, 636), f"{manager_phone}", fontsize=21, color=(1, 1, 1))
        first_page.insert_text((73, 673.5), f"{manager_email}", fontsize=21, color=(1,1,1))
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
        output_pdf.insert_pdf(template_pdf, from_page=0, to_page=1)
        output_pdf.insert_pdf(generated_pdf)
        output_pdf.insert_pdf(template_pdf, from_page=2, to_page=2)
        output_pdf.save(output_path)
        output_pdf.close()
        template_pdf.close()
        generated_pdf.close()
    except Exception as e:
        st.error(f"Error during PDF merging: {e}")

# Font Helper (unchanged)
def set_font_with_fallback(pdf_obj, font, style, size, text):
    fallback_font = "DejaVuSans"
    if font == "Exo2" and ("γ" in text or "●" in text):
        pdf_obj.set_font(fallback_font, style, size)
    else:
        pdf_obj.set_font(font, style, size)

# PDF Generation (unchanged)
if st.button("Generate PDF"):
    if not member_name.strip():
        st.error("Please enter a Member/Patient Name before generating the PDF.")
    elif not selected_markers:
        st.warning("Please select at least one lab marker to generate the report.")
    elif not any(str(lab_results.get(marker, "")).strip() != "" for marker in selected_markers):
        st.error("None of the lab result values have been entered. Please check your inputs.")
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
            try:
                user_numeric = float(lab_results[marker])
            except ValueError:
                continue
            clinical_range_parsed = parse_range(available_markers[marker]['clinical_range'])
            optimal_range_parsed = parse_range(available_markers[marker]['optimal_range'])
            if (clinical_range_parsed and optimal_range_parsed and
                all(x is not None for x in clinical_range_parsed + optimal_range_parsed)):
                clinical_min, clinical_max = clinical_range_parsed
                optimal_min, optimal_max = optimal_range_parsed
                if optimal_min <= user_numeric <= optimal_max:
                    score_sum += 1
                    count_optimal += 1
                elif clinical_min <= user_numeric <= clinical_max:
                    score_sum += 0.75
                    count_inrange += 1
                else:
                    score_sum += 0
                    count_out += 1
            else:
                score_sum += 0
                count_out += 1
        optimal_score = (score_sum / total_markers) * 100 if total_markers > 0 else 0
        pdf.add_page()
        pdf.set_fill_color(6, 182, 212)
        pdf.rect(0, 0, 210, 30, style='F')
        pdf.set_y(6)
        pdf.set_text_color(255, 255, 255)
        set_font_with_fallback(pdf, "Exo2", "B", 22, f"Your Optimal Score: {optimal_score:.0f}")
        pdf.cell(210, 18, f" Your Optimal Score: {optimal_score:.0f}", border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)
        pdf.set_text_color(250, 240, 230)
        pdf.set_xy(157, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(0, 10, f"{total_markers} Biomarkers Analyzed", border=0)
        categories = ['Out of Range', 'Optimal', 'In Range']
        values = [count_out, count_optimal, count_inrange]
        colors = ['#FF5555', PRIMARY_COLOR, in_range_color]
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
            chart_filename = tmpfile.name
        fig.savefig(chart_filename, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        pdf.image(chart_filename, x=32.5, y=32, w=160, h=192)
        os.remove(chart_filename)
        pct_out = (count_out / total_markers) * 100 if total_markers > 0 else 0
        pct_optimal = (count_optimal / total_markers) * 100 if total_markers > 0 else 0
        pct_inrange = (count_inrange / total_markers) * 100 if total_markers > 0 else 0
        pdf.set_y(238)
        legend_start_x = 32.5
        legend_box_size = 6
        spacing = 4
         # Legend Item: Out of Range.
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(255, 85, 85)  # vibrant red (#FF5555)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(40, 10, "Out of Range", border=0)
        pdf.set_text_color(115, 115, 115)  # SECONDARY_COLOR
        pdf.cell(0, 10, f"{pct_out:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Legend Item: Optimal Range.
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(6, 182, 212)  # PRIMARY_COLOR (#06B6D4)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 10, "Optimal Range", border=0)
        pdf.set_text_color(115, 115, 115)
        pdf.cell(0, 10, f"{pct_optimal:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Legend Item: In Range.
        pdf.set_xy(legend_start_x, pdf.get_y())
        pdf.set_fill_color(255, 165, 0)  # Orange (#FFA500)
        pdf.rect(pdf.get_x(), pdf.get_y(), legend_box_size, legend_box_size, style="F")
        pdf.set_x(legend_start_x + legend_box_size + spacing)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(40, 10, "In Range", border=0)
        pdf.set_text_color(115, 115, 115)
        pdf.cell(0, 10, f"{pct_inrange:.0f}%", border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        # ---- END FIRST PAGE ----

        #Groups markers by panel
        grouped_selected_markers = {}
        for marker in selected_markers:
            panel = available_markers[marker].get("panel", "Other")
            grouped_selected_markers.setdefault(panel, []).append(marker)
        desired_panel_order = [
            "Hormone, Gonadotropin & Neurosteroid Panel",
            "Thyroid, Growth Factors & Glucose",
            "Metabolic Panel",
            "CBC w/ Differential and Platelet",
            "Lipid Panel"
        ]
        ordered_panels = [p for p in desired_panel_order if p in grouped_selected_markers]
        remaining_panels = [p for p in grouped_selected_markers.keys() if p not in desired_panel_order]
        ordered_panels.extend(sorted(remaining_panels))
        for panel in ordered_panels:
            pdf.add_page()
            marker_count = 0
            pdf.set_fill_color(6, 182, 212)
            pdf.rect(0, 0, 210, 20, style='F')
            pdf.set_y(6)
            pdf.set_text_color(255, 255, 255)
            set_font_with_fallback(pdf, "Exo2", "B", 20, panel)
            pdf.cell(0, 10, panel, border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(10)
            markers_in_panel = grouped_selected_markers[panel]
            for marker in markers_in_panel:
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
                marker_info = available_markers[marker]
                pdf.set_text_color(6, 182, 212)
                set_font_with_fallback(pdf, "Exo2", "B", 19, marker)
                pdf.cell(0, 10, marker, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_text_color(115, 115, 115)
                set_font_with_fallback(pdf, "Exo2", "", 10, marker_info["description"])
                pdf.multi_cell(0, 5, marker_info["description"])
                pdf.ln(3)
                entered_value = lab_results[marker]
                result_text = f"Result: {entered_value} {marker_info['units']}"
                try:
                    user_numeric = float(entered_value)
                except ValueError:
                    user_numeric = None
                dot_color = None
                if user_numeric is not None:
                    clinical_range_parsed = parse_range(marker_info['clinical_range'])
                    optimal_range_parsed = parse_range(marker_info['optimal_range'])
                    if (clinical_range_parsed and optimal_range_parsed and
                        all(x is not None for x in clinical_range_parsed + optimal_range_parsed)):
                        clinical_min, clinical_max = clinical_range_parsed
                        optimal_min, optimal_max = optimal_range_parsed
                        if optimal_min <= user_numeric <= optimal_max:
                            dot_color = (6, 182, 212)
                        elif user_numeric < clinical_min or user_numeric > clinical_max:
                            dot_color = (255, 85, 85)
                if user_numeric is not None:
                    fig = create_range_chart(marker, marker_info['units'], marker_info['clinical_range'], marker_info['optimal_range'], entered_value)
                    if fig:
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                            chart_filename = tmpfile.name
                        fig.savefig(chart_filename, bbox_inches='tight')
                        plt.close(fig)
                        current_x = pdf.get_x()
                        current_y = pdf.get_y()
                        pdf.image(chart_filename, x=current_x, y=current_y, w=120, h=30)
                        os.remove(chart_filename)
                        pdf.set_xy(current_x + 125, current_y)
                        pdf.set_font("Exo2", "", 12)
                        pdf.cell(0, 30, result_text, border=0)
                        result_text_width = pdf.get_string_width(result_text)
                        pdf.set_xy(current_x + 125 + result_text_width + 2, current_y)
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
                else:
                    pdf.cell(0, 10, "Chart not available (non-numeric result).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(1)
                clinical_label = "Clinical Range:"
                set_font_with_fallback(pdf, "Exo2", "", 14, clinical_label)
                pdf.set_text_color(115, 115, 115)  # SECONDARY_COLOR for the label
                label_width = pdf.get_string_width(clinical_label) + 2
                pdf.cell(label_width, 10, clinical_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                clinical_value = f" {marker_info['clinical_range']}"
                set_font_with_fallback(pdf, "Exo2", "B", 14, clinical_value)
                pdf.set_text_color(255, 165, 0)  # Gold for the clinical value
                value_width = pdf.get_string_width(clinical_value) + 2
                pdf.cell(value_width, 10, clinical_value, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                pdf.cell(10, 10, "", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                optimal_label = "Optimal Range:"
                set_font_with_fallback(pdf, "Exo2", "", 14, optimal_label)
                pdf.set_text_color(115, 115, 115)  # SECONDARY_COLOR for the label
                label_width = pdf.get_string_width(optimal_label) + 2
                pdf.cell(label_width, 10, optimal_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                optimal_value = f" {marker_info['optimal_range']}"
                set_font_with_fallback(pdf, "Exo2", "B", 14, optimal_value)
                pdf.set_text_color(6, 182, 212)  # PRIMARY_COLOR for the optimal value
                value_width = pdf.get_string_width(optimal_value) + 2
                pdf.cell(value_width, 10, optimal_value, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(5)
        generated_pdf = "generated_lab_report.pdf"
        pdf.output(generated_pdf)
        template_pdf = "LabResults.pdf"
        updated_template = overwrite_more_information(template_pdf, "updated_template.pdf", member_name, selected_manager)
        merged_pdf = "final_report.pdf"
        merge_pdfs(updated_template, generated_pdf, merged_pdf)
        downloadable_filename = f"{member_name.replace(' ', '_')}_Lab_Results.pdf"
        with open(merged_pdf, "rb") as file:
            st.download_button("Download Final Report", file, file_name=downloadable_filename)

# Close Database (unchanged)
conn.close()
