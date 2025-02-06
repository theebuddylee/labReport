import streamlit as st
import pandas as pd
import re
import pdfplumber
import sqlite3
import requests
import json
import matplotlib.pyplot as plt
import os
import tempfile
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ================================================
# Lab Report UI (Markers, Inputs, PDF)
# ================================================

# --- Branding and Styling ---
PRIMARY_COLOR = "#06B6D4"      # e.g., a blue hue for optimal range
SECONDARY_COLOR = "#737373"    # e.g., a grayish hue for out-of-range
dark_green = "#006400"         # dark green for gradient start (clinical)
light_green = "#90EE90"        # light green for gradient end (clinical)
vibrant_red = "#FF5555"        # vibrant red for the user value line
BACKGROUND_COLOR = "#EBEBEB"
FONT_PRIMARY = "Exo2-Regular.ttf"
FONT_SECONDARY = "Source Sans Pro"

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

# --- Load JSON Data from GitHub ---
GITHUB_BASE_URL = "https://raw.githubusercontent.com/theebuddylee/HealthReport/main/data/"

def load_json_from_github(filename):
    url = f"{GITHUB_BASE_URL}{filename}"
    response = requests.get(url)
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            st.error(f"Error decoding JSON from {url}")
            st.write("Response text for debugging:")
            st.write(response.text)
            return {}
    else:
        st.error(f"Failed to load {filename}. HTTP {response.status_code}")
        return {}

contact_info = load_json_from_github("contact_info.json")
lab_markers = load_json_from_github("lab_markers.json")

# --- Logo and Page Heading ---
logo_path = "1st-Optimal-Logo-Dark.png"  # Adjust path as needed
st.image(logo_path, width=500)
st.markdown('<h1 class="report-title">Lab Results Report Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Generate The Optimal Lab Report</p>', unsafe_allow_html=True)

# --- Initialize Database (value stored as TEXT) ---
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

# ================================================
# Extractor Section: File Upload & Marker Extraction
# ================================================

st.write("Upload your LabCorp report (PDF or TXT) to extract patient and lab marker details. Then, match the extracted markers to existing markers and adjust inputs before generating a PDF report.")

uploaded_file = st.file_uploader("Choose a LabCorp report file", type=["pdf", "txt"])

# Initialize variables for extracted patient name and markers.
extracted_data = []         # List of dicts: each has keys "Marker", "Value", "Units", "Reference Interval"
extracted_markers_dict = {} # Mapping: extracted marker name -> value
patient_name_extracted = None

if uploaded_file is not None:
    if uploaded_file.name.lower().endswith(".pdf"):
        text = ""
        try:
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            st.error(f"Error reading PDF: {e}")
            text = ""
    elif uploaded_file.name.lower().endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")
    else:
        st.error("Unsupported file type.")
        text = ""

    if text:
        #st.subheader("Extracted Text (first 500 characters)")
        #st.text(text[:500])

        # --- Extract Patient Name ---
        # Use a flexible regex so that extra whitespace or headers won’t prevent matching.
        patient_match = re.search(r'([\w\s,]+?)\s*DOB:', text)
        if patient_match:
            patient_name_extracted = patient_match.group(1).strip()
        else:
            patient_name_extracted = "Unknown"
        st.write("**Patient Name (extracted):**", patient_name_extracted)

        # --- Extract Lab Marker Data ---
        # This regex captures rows with a test code of 01, 02, or 03.
        regex = re.compile(
            r'^(?P<marker>.+?)\s+(?P<code>0[123])\s+(?P<value>[><]?\d+(?:\.\d+)?)(?:\s+\S+){0,3}\s+(?P<units>[\w\/\^%\.x-]+)\s+(?P<ref>[\d\.\-,]+)',
            re.MULTILINE
        )
        results = regex.findall(text)
        for match in results:
            raw_marker, code, value, units, ref_interval = match
            marker = raw_marker.strip()
            if "Test Current Result" in marker:
                marker = marker.split("Test Current Result")[0].strip()
            # Attempt to convert to float; if it fails, leave as is.
            try:
                numeric_value = float(value)
                value_out = numeric_value
            except ValueError:
                value_out = value
            extracted_data.append({
                "Marker": marker,
                "Value": value_out,
                "Units": units,
                "Reference Interval": ref_interval
            })
        if extracted_data:
            st.subheader("Extracted Lab Results")
            df_extracted = pd.DataFrame(extracted_data)
            st.dataframe(df_extracted)
            # Build a mapping for matching purposes.
            for item in extracted_data:
                key = item["Marker"].strip()
                extracted_markers_dict[key] = item["Value"]
        else:
            st.error("No lab marker data found. The report format may be different from expected.")
else:
    st.info("Please upload a LabCorp report file.")

# --- Sidebar: Member Details ---
st.sidebar.title("Member Details")
membership_managers = ["Allison", "Amber", "Buddy", "Dillon", "Justin", "Joe", "Ramsey"]
selected_manager = st.sidebar.selectbox("Select Membership Manager", membership_managers)
default_member_name = patient_name_extracted if patient_name_extracted else ""
member_name = st.sidebar.text_input("Enter Member/Patient Name", value=default_member_name)

# --- Marker Group & Selection ---
selected_markers = []
lab_results = {}  # This dict will hold marker => user-entered value

if lab_markers:
    st.markdown("### Select Group of Lab Markers:")
    # The keys of the lab_markers JSON represent groups (e.g. "Men", "Women", etc.)
    selected_group = st.selectbox("Choose a group:", list(lab_markers.keys()))
    available_markers = lab_markers[selected_group]
    # Preselect markers that were extracted from the report (if they match available markers).
    preselected_markers = []
    for marker in available_markers.keys():
        # Simple case-insensitive match.
        for extracted_marker in extracted_markers_dict.keys():
            if extracted_marker.lower() == marker.lower():
                preselected_markers.append(marker)
                lab_results[marker] = extracted_markers_dict[extracted_marker]
                break
    st.markdown("### Select Lab Markers to Include:")
    selected_markers = st.multiselect("Choose lab markers:", list(available_markers.keys()), default=preselected_markers)
else:
    st.error("Lab markers could not be loaded.")

# --- Input Lab Result Values ---
if selected_markers:
    st.markdown("### Input Lab Results:")
    for marker in selected_markers:
        default_val = lab_results.get(marker, "")
        # Use text_input to allow non-numeric characters (e.g., ">" or "<")
        lab_results[marker] = st.text_input(f"Enter result for {marker}:", value=str(default_val))

    # --- Save to Database ---
    if st.button("Save Results"):
        for marker, value in lab_results.items():
            cursor.execute(
                "INSERT INTO lab_results (marker, value, date) VALUES (?, ?, date('now'))",
                (marker, value)
            )
        conn.commit()
        st.success("Results saved successfully!")

# ================================================
# Helper Functions & PDF Generation
# ================================================

def parse_range(range_str):
    """
    Parses a range string of the form "min - max" into numeric values.
    Returns (None, None) if the string cannot be parsed.
    """
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
    """
    Creates a horizontal stacked bar chart showing:
      - Clinical Range (light blue, top bar)
      - Optimal Range (light green, bottom bar)
      - A vertical grey line for the user-entered value.
    Returns the matplotlib figure, or None if ranges cannot be parsed or user_value isn’t numeric.
    """
    clinical_min, clinical_max = parse_range(clinical_range)
    optimal_min, optimal_max = parse_range(optimal_range)
    try:
        user_numeric = float(user_value)
    except ValueError:
        return None

    if clinical_min is None or clinical_max is None or optimal_min is None or optimal_max is None:
        return None

    overall_min = min(clinical_min, optimal_min, user_numeric)
    overall_max = max(clinical_max, optimal_max, user_numeric)
    padding = 0.1 * (overall_max - overall_min)
    x_min = overall_min - padding
    x_max = overall_max + padding

    fig, ax = plt.subplots(figsize=(6, 2))
    clinical_y = 0.55
    optimal_y = 0.15
    bar_height = 0.3
    ax.broken_barh([(clinical_min, clinical_max - clinical_min)], (clinical_y, bar_height), facecolors='lightblue', label='Clinical Range')
    ax.broken_barh([(optimal_min, optimal_max - optimal_min)], (optimal_y, bar_height), facecolors='lightgreen', label='Optimal Range')
    ax.plot([user_numeric, user_numeric], [optimal_y, clinical_y + bar_height], color='grey', linewidth=3, label='User Value')
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, 1)
    ax.set_yticks([])
    ax.set_xlabel(f"{marker_name} ({units})")
    ax.legend(loc='upper center', ncol=3)
    plt.tight_layout()
    return fig

# --- PDF Generation ---
if st.button("Generate PDF"):
    if not member_name.strip():
        st.error("Please enter a Member/Patient Name before generating the PDF.")
    elif selected_markers:
        # Ensure that at least one lab result has been entered (non-empty).
        if not any(str(lab_results.get(marker, "")).strip() != "" for marker in selected_markers):
            st.error("It appears that none of the lab result values have been entered. Please check your inputs before generating the report.")
        else:
            pdf = FPDF()
            pdf.add_font("Exo2", style="", fname="Exo2-Regular.ttf")
            pdf.add_font("Exo2", style="B", fname="Exo2-Bold.ttf")
            pdf.add_page()
            pdf.set_font("Exo2", size=12)

            # Branding header
            pdf.set_fill_color(6, 182, 212)
            pdf.rect(0, 0, 210, 30, style='F')
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Exo2", style="B", size=16)
            pdf.cell(0, 10, "1st Optimal Lab Results Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            pdf.ln(15)
            pdf.set_text_color(0, 0, 0)
            for marker in selected_markers:
                marker_info = available_markers[marker]
                # Marker name in bold
                pdf.set_font("Exo2", style="B", size=12)
                pdf.cell(0, 10, marker, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                # Marker description
                pdf.set_font("Exo2", size=10)
                pdf.multi_cell(0, 10, marker_info["description"])
                pdf.ln(5)
                # The entered result (with units)
                entered_value = lab_results[marker]
                pdf.cell(0, 10, f"Result: {entered_value} {marker_info['units']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                # Clinical and Optimal ranges text
                pdf.cell(0, 10,
                         f"Clinical Range: {marker_info['clinical_range']}   Optimal Range: {marker_info['optimal_range']}",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(5)

                # Create and insert chart if possible
                try:
                    user_numeric = float(entered_value)
                except ValueError:
                    user_numeric = None
                if user_numeric is not None:
                    fig = create_range_chart(marker, marker_info['units'], marker_info['clinical_range'], marker_info['optimal_range'], entered_value)
                    if fig is not None:
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
                            chart_filename = tmpfile.name
                        fig.savefig(chart_filename, bbox_inches='tight')
                        plt.close(fig)
                        pdf.image(chart_filename, w=pdf.w - 20)
                        os.remove(chart_filename)
                        pdf.ln(5)
                    else:
                        pdf.cell(0, 10, "Chart not available (unable to parse ranges).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                        pdf.ln(5)
                else:
                    pdf.cell(0, 10, "Chart not available (non-numeric result).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(5)

            file_name = f"{member_name}_lab_interpretation.pdf"
            pdf.output(file_name)
            with open(file_name, "rb") as file:
                st.download_button("Download Report", file, file_name=file_name)
    else:
        st.warning("Please select at least one marker to generate the report.")

# --- Close Database Connection ---
conn.close()
