import streamlit as st
import pandas as pd
import re
import pdfplumber
import sqlite3
import requests
import json
import matplotlib.pyplot as plt
import numpy as np
import fitz  # PyMuPDF for PDF editing/merging
import tempfile
import os
import pytz
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ====================================================
# Branding, Styling, and Page Layout
# ====================================================

PRIMARY_COLOR = "#06B6D4"      # Blue hue for optimal range and header
SECONDARY_COLOR = "#737373"    # Gray for clinical range text etc.
vibrant_red = "#FF5555"        # Red for the user value indicator
BACKGROUND_COLOR = "#EBEBEB"
FONT_PRIMARY = "Exo2-Regular.ttf"   # Ensure this font file is available
FONT_SECONDARY = "Source Sans Pro"   # You can adjust as needed

# Custom CSS styling
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

# Display a logo and header (adjust the logo path as needed)
logo_path = "1st-Optimal-Logo-Dark.png"  # Replace with your logo path
if os.path.exists(logo_path):
    st.image(logo_path, width=500)
st.markdown('<h1 class="report-title">Lab Results Report Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Generate The Optimal Lab Report</p>', unsafe_allow_html=True)

# ====================================================
# Load JSON Data from GitHub (contact info and lab markers)
# ====================================================

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

# ====================================================
# Initialize (or Connect to) SQLite Database
# ====================================================

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

# ====================================================
# File Upload & Lab Marker Extraction
# ====================================================

st.write("Upload your LabCorp report (PDF or TXT) to extract patient and lab marker details.")

uploaded_file = st.file_uploader("Choose a LabCorp report file", type=["pdf", "txt"])

# Variables to hold extracted data
extracted_data = []         # List of dictionaries for each marker
extracted_markers_dict = {} # Mapping from marker name to extracted value
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
        # --- Extract Patient Name ---
        # Assume the very first line of the extracted text is in "LastName, FirstName ..." format.
        first_line = text.split("\n")[0].strip()
        if ',' in first_line:
            parts = first_line.split(',')
            last = parts[0].strip()
            # Take the first word from the second part as the first name
            first = parts[1].strip().split()[0]
            patient_name_extracted = f"{first} {last}"
        else:
            patient_name_extracted = first_line
        st.write("**Patient Name (extracted):**", patient_name_extracted)

        # --- Extract Lab Marker Data ---
        # Regex from the second code base (with slight post-processing)
        regex = re.compile(
            r'^(?P<marker>.+?)\s+(?P<code>0[123])\s+(?P<value>[><]?\d+(?:\.\d+)?)(?:\s+\S+){0,3}\s+(?P<units>[\w\/\^%\.x-]+)\s+(?P<ref>[\d\.\-,]+)',
            re.MULTILINE
        )
        results = regex.findall(text)
        for raw_marker, code, value, units, ref_interval in results:
            marker = raw_marker.strip()
            # Optionally remove extra text if present
            if "Test Current Result" in marker:
                marker = marker.split("Test Current Result")[0].strip()
            marker = re.split(r'\d', marker)[0].strip()
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
            # Convert 'Value' to numeric where possible; convert NaN to empty string
            df_extracted["Value"] = pd.to_numeric(df_extracted["Value"], errors='coerce')
            df_extracted["Value"] = df_extracted["Value"].apply(lambda x: "" if pd.isna(x) else str(x))
            st.dataframe(df_extracted)

            # Build mapping for matching with available markers
            for item in extracted_data:
                key = item["Marker"].strip()
                extracted_markers_dict[key] = str(item["Value"])
        else:
            st.error("No lab marker data found. The report format may be different from expected.")
else:
    st.info("Please upload a LabCorp report file.")

# ====================================================
# Sidebar: Member Details
# ====================================================

st.sidebar.title("Member Details")
# Use keys from the GitHub-loaded contact_info (if available)
if contact_info:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", list(contact_info.keys()))
else:
    selected_manager = st.sidebar.selectbox("Select Membership Manager", ["Manager1", "Manager2"])

# Use the extracted patient name as default if available
default_member_name = patient_name_extracted if patient_name_extracted else ""
member_name = st.sidebar.text_input("Enter Member/Patient Name", value=default_member_name)

# ====================================================
# Marker Group Selection and User Input for Lab Results
# ====================================================

# --- Define Normalization & Custom Manual Mapping ---
def normalize_marker(marker):
    """
    Normalize marker names by converting to lowercase,
    removing any text in parentheses, and stripping non-alphanumeric characters.
    """
    marker = marker.lower().strip()
    marker = re.sub(r'\([^)]*\)', '', marker)  # Remove text inside parentheses
    marker = re.sub(r'[^a-z0-9]', '', marker)   # Remove non-alphanumeric characters
    return marker

# Custom manual mapping: normalized extracted marker -> JSON key (available marker)
manual_map = {
    normalize_marker("T"): "Free T4 ",
    normalize_marker("WBC"): "White Blood Cell (WBC) Count",
    normalize_marker("RBC"): "Red Blood Cell (RBC) Count",
    normalize_marker("MCV"): "Mean Corpuscular Volume (MCV)",
    normalize_marker("MCH"): "Mean Corpuscular Hemoglobin (MCH)",
    normalize_marker("MCHC"): "Mean Corpuscular Hemoglobin Concentration (MCHC)",
    normalize_marker("RDW"): "Red Cell Distribution Width (RDW)",
    normalize_marker("Platelets"): "Platelet Count",
    normalize_marker("Lymphs"): "Lymphocytes",
    normalize_marker("Eos"): "Eosinophils",
    normalize_marker("Basos"): "Basophils",
    normalize_marker("Neutrophils (Absolute)"): "Neutrophils",
    normalize_marker("Lymphs (Absolute)"): "Lymphocytes",
    normalize_marker("Monocytes(Absolute)"): "Monocytes",
    normalize_marker("Eos (Absolute)"): "Eosinophils",
    normalize_marker("Baso (Absolute)"): "Basophils",
    # For "Immature Granulocytes" and "Immature Grans (Abs)" we choose not to map (omit them)
    normalize_marker("BUN"): "Blood Urea Nitrogen (BUN)",
    normalize_marker("Protein, Total"): "Total Protein",
    normalize_marker("Bilirubin, Total"): "Total Bilirubin",
    normalize_marker("AST (SGOT)"): "Aspartate Aminotransferase (AST)",
    normalize_marker("ALT (SGPT)"): "Alanine Aminotransferase (ALT)",
    # Specific Gravity and Urobilinogen,Semi-Qn are not in the JSON—ignore them.
    normalize_marker("Cholesterol, Total"): "Total Cholesterol",
    normalize_marker("HDL Cholesterol"): "HDL",
    # UIBC and SDMA are not mapped (ignore them)
    normalize_marker("Testosterone, Total, LC/MS A,"): "Total Testosterone",
    normalize_marker("Hemoglobin A"): "Hemoglobin (Hgb)",
    normalize_marker("DHEA-Sulfate"): "Dehydroepiandrosterone Sulfate (DHEA-S)",
    # Cortisol is not in the JSON – ignore it.
    normalize_marker("LH"): "Luteinizing Hormone (LH)",
    normalize_marker("FSH"): "Follicle-Stimulating Hormone (FSH)",
    normalize_marker("Prolactin"): "Prolactin",
    # C-Reactive Protein, Cardiac is not mapped.
    normalize_marker("Estradiol, Sensitive A,"): "Estradiol",
    # Homocyst(e)ine is not mapped.
    normalize_marker("GGT"): "γ-Glutamyl Transferase (GGT)",
    # Progesterone is not mapped.
    normalize_marker("Insulin"): "Fasting Insulin",
    # Ferritin is not mapped.
    normalize_marker("Triiodothyronine (T"): "Free T3",
    normalize_marker("Serum"): "SHBG",
    # Magnesium, RBC B not in Json – ignore them.
}

selected_markers = []
lab_results = {}  # Will hold marker name => user-entered value

if lab_markers:
    st.markdown("### Select Group of Lab Markers:")
    # The keys in lab_markers (e.g. "Men", "Women", etc.) represent groups.
    selected_group = st.selectbox("Choose a group:", list(lab_markers.keys()))
    available_markers = lab_markers[selected_group]

    preselected_markers = []
    matched_extracted = set()

    # For each available marker from the JSON, attempt to find a match among the extracted markers.
    for avail_marker in available_markers.keys():
        norm_avail = normalize_marker(avail_marker)
        found_match = False
        for extracted_marker in extracted_markers_dict.keys():
            norm_extracted = normalize_marker(extracted_marker)
            # First, try direct normalized equality.
            if norm_avail == norm_extracted:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                found_match = True
                break
            # Next, check if a manual mapping applies.
            if norm_extracted in manual_map and manual_map[norm_extracted] == avail_marker:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                found_match = True
                break
        # (Optional) You can log if no match was found for this available marker.

    # Identify any extracted markers that were not matched.
    unmatched_extracted = [em for em in extracted_markers_dict.keys() if em not in matched_extracted]
    if unmatched_extracted:
        st.warning("The following extracted markers did not match any available markers:")
        st.write(unmatched_extracted)

    st.markdown("### Select Lab Markers to Include:")
    selected_markers = st.multiselect("Choose lab markers:", list(available_markers.keys()), default=preselected_markers)
else:
    st.error("Lab markers could not be loaded.")

if selected_markers:
    st.markdown("### Input Lab Results:")
    for marker in selected_markers:
        default_val = lab_results.get(marker, "")
        # Allow non-numeric characters in the input
        lab_results[marker] = st.text_input(f"Enter result for {marker}:", value=str(default_val))

    # --- Save Results to Database ---
    if st.button("Save Results"):
        for marker, value in lab_results.items():
            cursor.execute(
                "INSERT INTO lab_results (marker, value, date) VALUES (?, ?, date('now'))",
                (marker, value)
            )
        conn.commit()
        st.success("Results saved successfully!")

# ====================================================
# Visualization Functions (Charts)
# ====================================================

def parse_range(range_str):
    """
    Parses a range string of the form "min - max" into numeric values.
    Returns (None, None) if parsing fails.
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
    Creates a horizontal stacked bar chart that shows:
      - The clinical range (SECONDARY_COLOR)
      - The optimal range (PRIMARY_COLOR)
      - A vertical line (vibrant_red) indicating the user value.
    """
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
    padding = 0.1 * (overall_max - overall_min)
    x_min = overall_min - padding
    x_max = overall_max + padding

    fig, ax = plt.subplots(figsize=(6, 2))
    bar_height = 0.075
    optimal_y = 0.0
    clinical_y = optimal_y + bar_height

    # Clinical range
    ax.broken_barh([(clinical_min, clinical_max - clinical_min)], (clinical_y, bar_height),
                   facecolors=SECONDARY_COLOR, edgecolor='none', label='Clinical Range')
    # Optimal range
    ax.broken_barh([(optimal_min, optimal_max - optimal_min)], (optimal_y, bar_height),
                   facecolors=PRIMARY_COLOR, edgecolor='none', label='Optimal Range')
    # User value line
    ax.axvline(user_numeric, color=vibrant_red, linewidth=3, label='User Value')

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, clinical_y + bar_height)
    ax.set_yticks([])
    ax.set_xlabel(f"{marker_name} ({units})")
    ax.legend(loc='upper center', ncol=3)
    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.tight_layout()
    return fig

# ====================================================
# PDF Merging Helper Functions
# ====================================================

def overwrite_more_information(template_path, output_path, member_name, selected_manager):
    try:
        local_timezone = pytz.timezone("America/Los_Angeles")
        current_date = datetime.now(local_timezone).strftime("%m-%d-%Y")

        manager_info = contact_info.get(selected_manager, {"email": "N/A", "phone": "N/A"})
        manager_name = f"{manager_info.get('first_name', 'Unknown')} {manager_info.get('last_name', 'Unknown')}"
        manager_email = manager_info.get("email", "N/A")
        manager_phone = manager_info.get("phone", "N/A")

        doc = fitz.open(template_path)
        first_page, last_page = doc[0], doc[-1]

        first_page.insert_text((73, 598), f"{manager_name} exclusively for {member_name or 'Not Provided'}", fontsize=21, color=(1, 1, 1))
        first_page.insert_text((73, 636), f"{manager_phone}", fontsize=21, color=(1, 1, 1))
        first_page.insert_text((73, 673.5), f"{manager_email}", fontsize=21, color=(1,1,1))

        doc.save(output_path)
        return output_path
    except Exception as e:
        print(f"Error in overwrite_more_information: {e}")
        return None

def merge_pdfs(template_path, generated_path, output_path):
    try:
        # Open the template PDF (LabResults.pdf) and the generated lab report PDF
        template_pdf = fitz.open(template_path)
        generated_pdf = fitz.open(generated_path)

        # Create a new PDF to hold the merged result
        output_pdf = fitz.open()

        # Insert pages 1 and 2 from LabResults.pdf (0-indexed: pages 0 and 1)
        output_pdf.insert_pdf(template_pdf, from_page=0, to_page=1)

        # Insert all pages from the generated lab report
        output_pdf.insert_pdf(generated_pdf)

        # Insert page 3 from LabResults.pdf (0-indexed: page 2)
        output_pdf.insert_pdf(template_pdf, from_page=2, to_page=2)

        # Save the merged PDF to the specified output path
        output_pdf.save(output_path)

        # Close all documents
        output_pdf.close()
        template_pdf.close()
        generated_pdf.close()

    except Exception as e:
        st.error(f"Error during PDF merging: {e}")

# ====================================================
# Helper: Set Font with Fallback for Missing Glyphs
# ====================================================
def set_font_with_fallback(pdf_obj, font, style, size, text):
    """
    Sets the font for the PDF. If using the custom font (Exo2) and the text contains
    the Greek letter 'γ', it switches to a Unicode fallback font (DejaVuSans) known to support the glyph.
    """
    fallback_font = "DejaVuSans"  # Make sure DejaVuSans.ttf and DejaVuSans-Bold.ttf are available
    if font == "Exo2" and "γ" in text:
        pdf_obj.set_font(fallback_font, style, size)
    else:
        pdf_obj.set_font(font, style, size)

# ====================================================
# PDF Generation (Lab Report + Template Merge)
# ====================================================

if st.button("Generate PDF"):
    if not member_name.strip():
        st.error("Please enter a Member/Patient Name before generating the PDF.")
    elif not selected_markers:
        st.warning("Please select at least one lab marker to generate the report.")
    elif not any(str(lab_results.get(marker, "")).strip() != "" for marker in selected_markers):
        st.error("None of the lab result values have been entered. Please check your inputs.")
    else:
        # Create the lab report using FPDF (based on the second code base)
        pdf = FPDF()
        # Register fonts – ensure the font files are available in your working directory
        pdf.add_font("Exo2", "", FONT_PRIMARY)
        pdf.add_font("Exo2", "B", "Exo2-Bold.ttf")
        # Register the Unicode fallback font (DejaVu Sans)
        pdf.add_font("DejaVuSans", "", "DejaVuSans.ttf")
        pdf.add_font("DejaVuSans", "B", "DejaVuSans-Bold.ttf")

        pdf.add_page()
        pdf.set_font("Exo2", size=12)

        # Branding header (a colored rectangle and title)
        pdf.set_fill_color(6, 182, 212)
        pdf.rect(0, 0, 210, 30, style='F')
        pdf.set_text_color(255, 255, 255)
        # Use fallback if needed for the header text
        set_font_with_fallback(pdf, "Exo2", "B", 16, "1st Optimal Lab Results Report")
        pdf.cell(0, 10, "1st Optimal Lab Results Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)

        # Loop over each selected marker and add its details and chart (if available)
        for marker in selected_markers:
            marker_info = available_markers[marker]

            # Marker title as H2 in PRIMARY_COLOR
            pdf.set_text_color(6, 182, 212)  # PRIMARY_COLOR
            set_font_with_fallback(pdf, "Exo2", "B", 18, marker)
            pdf.cell(0, 10, marker, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            # Marker description in SECONDARY_COLOR
            pdf.set_text_color(115, 115, 115)
            set_font_with_fallback(pdf, "Exo2", "", 10, marker_info["description"])
            pdf.multi_cell(0, 5, marker_info["description"])
            pdf.ln(4)

            entered_value = lab_results[marker]

            try:
                # Only attempt to create a chart if the user-entered value can be converted to float
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
                    pdf.image(chart_filename, w=120, h=30)
                    os.remove(chart_filename)
                    pdf.ln(1)
                else:
                    pdf.cell(0, 10, "Chart not available (unable to parse ranges).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                    pdf.ln(1)
            else:
                pdf.cell(0, 10, "Chart not available (non-numeric result).", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(1)

            # Print the "Result:" line as before
            result_text = f"Result: {entered_value} {marker_info['units']}"
            pdf.set_text_color(115, 115, 115)
            set_font_with_fallback(pdf, "Exo2", "B", 16, result_text)
            pdf.cell(0, 10, result_text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)

            # --- Print Clinical Range and Optimal Range on the same line ---
            # Clinical Range label (bold, SECONDARY_COLOR)
            clinical_label = "Clinical Range:"
            set_font_with_fallback(pdf, "Exo2", "B", 16, clinical_label)
            pdf.set_text_color(115, 115, 115)
            label_width = pdf.get_string_width(clinical_label) + 2
            pdf.cell(label_width, 10, clinical_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)

            # Clinical Range value (normal, black)
            clinical_value = f" {marker_info['clinical_range']}"
            set_font_with_fallback(pdf, "Exo2", "", 16, clinical_value)
            value_width = pdf.get_string_width(clinical_value) + 2
            pdf.cell(value_width, 10, clinical_value, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)

            # Spacing between the two range sections
            pdf.cell(10, 10, "", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)

            # Optimal Range label (bold, PRIMARY_COLOR)
            optimal_label = "Optimal Range:"
            set_font_with_fallback(pdf, "Exo2", "B", 16, optimal_label)
            pdf.set_text_color(6, 182, 212)  # PRIMARY_COLOR in RGB
            label_width = pdf.get_string_width(optimal_label) + 2
            pdf.cell(label_width, 10, optimal_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)

            # Optimal Range value (normal, PRIMARY_COLOR)
            optimal_value = f" {marker_info['optimal_range']}"
            set_font_with_fallback(pdf, "Exo2", "", 16, optimal_value)
            value_width = pdf.get_string_width(optimal_value) + 2
            pdf.cell(value_width, 10, optimal_value, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(5)

        # Save the generated lab report PDF
        generated_pdf = "generated_lab_report.pdf"
        pdf.output(generated_pdf)

        # --- Merge with Template PDF ---
        # Specify the path to your template PDF (must exist in your working directory)
        template_pdf = "LabResults.pdf"
        # Overwrite the template with member and manager information
        updated_template = overwrite_more_information(template_pdf, "updated_template.pdf", member_name, selected_manager)
        merged_pdf = "final_report.pdf"
        merge_pdfs(updated_template, generated_pdf, merged_pdf)

        # Use the member's name (with spaces replaced by underscores) for the downloadable filename
        downloadable_filename = f"{member_name.replace(' ', '_')}_Lab_Results.pdf"
        with open(merged_pdf, "rb") as file:
            st.download_button("Download Final Report", file, file_name=downloadable_filename)

# ====================================================
# Close the Database Connection on App Exit
# ====================================================
conn.close()
