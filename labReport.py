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
# Set page config
st.set_page_config(
    page_title="1st Optimal Lab Results Report Generator",
    page_icon="🧪",
    layout="wide",  # Optional: adjust as needed
    initial_sidebar_state="expanded",  # Optional
)

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
        #st.write("**Patient Name (extracted):**", patient_name_extracted)

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
    normalize_marker("Lymphs (Absolute)"): "Lymphocytes",  # New mapping for unmatched "Lymphs (Absolute)"
    normalize_marker("Eos"): "Eosinophils",
    normalize_marker("Eos (Absolute)"): "Eosinophils",     # New mapping for unmatched "Eos (Absolute)"
    normalize_marker("Basos"): "Basophils",
    normalize_marker("Neutrophils (Absolute)"): "Neutrophils",
    normalize_marker("Monocytes(Absolute)"): "Monocytes",
    normalize_marker("Baso (Absolute)"): "Basophils",
    # For "Immature Granulocytes" and "Immature Grans (Abs)" we choose not to map (omit them)
    normalize_marker("BUN"): "Blood Urea Nitrogen (BUN)",
    normalize_marker("Protein, Total"): "Total Protein",
    normalize_marker("Bilirubin, Total"): "Total Bilirubin",
    normalize_marker("AST (SGOT)"): "Aspartate Aminotransferase (AST)",
    normalize_marker("ALT (SGPT)"): "Alanine Aminotransferase (ALT)",
    # Specific Gravity and Urobilinogen,Semi-Qn are not in the JSON—ignore them.
    normalize_marker("Cholesterol, Total"): "Total Cholesterol",
    normalize_marker("Testosterone"): "Total Testosterone",
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
    normalize_marker("Prostate Specific Ag"): "Prostate Specific Antigen (PSA)",
    normalize_marker("Serum"): "SHBG"
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
        for extracted_marker in extracted_markers_dict.keys():
            norm_extracted = normalize_marker(extracted_marker)
            # First, try direct normalized equality.
            if norm_avail == norm_extracted:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break
            # Next, check if a manual mapping applies.
            if norm_extracted in manual_map and manual_map[norm_extracted] == avail_marker:
                preselected_markers.append(avail_marker)
                lab_results[avail_marker] = extracted_markers_dict[extracted_marker]
                matched_extracted.add(extracted_marker)
                break

    # Build a set of normalized extracted marker keys.
    normalized_extracted = {normalize_marker(key): key for key in extracted_markers_dict.keys()}

    # Build a set of normalized available marker keys from lab_markers.
    normalized_available = {normalize_marker(key): key for key in available_markers.keys()}

    # Build a set of normalized keys that were successfully matched.
    matched_normalized = set()
    for extracted_marker in matched_extracted:  # matched_extracted should have been collected during matching.
        matched_normalized.add(normalize_marker(extracted_marker))

    # Compute the difference: markers that were extracted but not matched.
    unmatched_normalized = [normalized_extracted[norm_key] for norm_key in normalized_extracted if norm_key not in matched_normalized]

    if unmatched_normalized:
        st.warning("The following extracted markers did not match any available markers (after normalization):")
        st.write(unmatched_normalized)

    st.markdown("### Select Lab Markers to Include:")
    # Group available markers by their panel attribute.
    grouped_by_panel = {}
    for marker, info in available_markers.items():
         panel = info.get("panel", "Other")
         grouped_by_panel.setdefault(panel, []).append(marker)
    # For each panel, create an expander with a multiselect for markers in that panel.
    # We want the panels to appear in a fixed order:
    desired_panel_order = [
         "Hormone, Gonadotropin & Neurosteroid Panel",
         "Thyroid, Growth Factors & Glucose",
         "Metabolic Panel",
         "CBC w/ Differential and Platelet",
         "Lipid Panel",
         "Iron Markers",
         "Inflammatory Markers"
    ]
    selected_markers = []
    # First show panels in desired order (if present)
    for panel in desired_panel_order:
         if panel in grouped_by_panel:
             markers_in_panel = sorted(grouped_by_panel[panel])
             default_markers = sorted([m for m in markers_in_panel if m in preselected_markers])
             with st.expander(panel, expanded=True):
                 selected_from_panel = st.multiselect(f"Select markers from {panel}:", markers_in_panel, default=default_markers, key=panel)
                 selected_markers.extend(selected_from_panel)
    # Then display any other panels not in the desired order.
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
    padding = 0.15 * (overall_max - overall_min)
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
    ax.axvline(user_numeric, color=vibrant_red, linewidth=3, label='Your Value')

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(0, clinical_y + bar_height)
    ax.set_yticks([])
    ax.set_xlabel(f"{marker_name} ({units})")
    ax.legend(loc='best', ncol=3) #originally 'upper center'
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
    fallback_font = "DejaVuSans"  # This font includes the '●' glyph
    # Use the fallback if the primary font (Exo2) is missing 'γ' or '●'
    if font == "Exo2" and ("γ" in text or "●" in text):
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
        # Create the lab report using FPDF
        pdf = FPDF()
        # Register fonts – ensure the font files are available in your working directory
        pdf.add_font("Exo2", "", FONT_PRIMARY)
        pdf.add_font("Exo2", "B", "Exo2-Bold.ttf")
        pdf.add_font("DejaVuSans", "", "DejaVuSans.ttf")
        pdf.add_font("DejaVuSans", "B", "DejaVuSans-Bold.ttf")

        # ---- Optimal Score Page ----
        # Compute overall score and counts.
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
            if (clinical_range_parsed is not None and optimal_range_parsed is not None and
                clinical_range_parsed[0] is not None and clinical_range_parsed[1] is not None and
                optimal_range_parsed[0] is not None and optimal_range_parsed[1] is not None):
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

        # Draw header rectangle at the top, now showing the Optimal Score.
        pdf.set_fill_color(6, 182, 212)  # PRIMARY_COLOR
        pdf.rect(0, 0, 210, 30, style='F')
        pdf.set_y(6)
        pdf.set_text_color(255, 255, 255)  # White text
        set_font_with_fallback(pdf, "Exo2", "B", 22, f"Your Optimal Score: {optimal_score:.0f}")
        pdf.cell(210, 18, f" Your Optimal Score: {optimal_score:.0f}", border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(10)

        # Print total markers in the upper right.
        pdf.set_text_color(250, 240, 230)
        pdf.set_xy(156, 0)
        pdf.set_font("Exo2", "", 12)
        pdf.cell(0, 10, f"{total_markers} Biomarkers Analyzed", border=0)

        # Create an enlarged vertical bar chart for the marker breakdown.
        categories = ['Out of Range', 'Optimal', 'In Range']
        values = [count_out, count_optimal, count_inrange]
        in_range_color = "#FFA500"  # Color for "In Range"
        colors = ['#FF5555', PRIMARY_COLOR, in_range_color]

        # Increase size here as needed
        fig, ax = plt.subplots(figsize=(14, 22))

        bars = ax.bar(categories, values, color=colors)
        ax.set_ylabel('Number of Markers', fontsize=16)
        #ax.set_title('Marker Range Breakdown', fontsize=16, color=PRIMARY_COLOR)
        # Remove y-axis tick labels
        ax.set_yticks([])
        # Remove chart borders and tick marks for a clean look.
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(bottom=False, left=False)
        ax.set_xticks(range(len(categories)))  # set ticks at positions 0, 1, 2
        ax.set_xticklabels(categories, fontsize=20)
        # Annotate bars with counts.
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.2, int(yval), ha='center', va='bottom', fontsize=20)
        plt.tight_layout(pad=0.1)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            chart_filename = tmpfile.name
        fig.savefig(chart_filename, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)


        # Save the chart without extra borders.
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpfile:
            chart_filename = tmpfile.name
        fig.savefig(chart_filename, bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)

        # Insert the chart image.
        pdf.image(chart_filename, x=32.5, y=32, w=160, h=192)
        os.remove(chart_filename)
        # ---- END Graph
        # Add the vertically stacked legend below the chart.
        # ---------------------------
        # Calculate percentages for each range.
        pct_out = (count_out / total_markers) * 100 if total_markers > 0 else 0
        pct_optimal = (count_optimal / total_markers) * 100 if total_markers > 0 else 0
        pct_inrange = (count_inrange / total_markers) * 100 if total_markers > 0 else 0

        # Set the y-coordinate for the legend to be about 80% of the page height.
        # For an A4 page (297 mm tall), 80% is roughly 238 mm.
        pdf.set_y(238)

        legend_start_x = 32.5
        legend_box_size = 6   # Size of the colored square.
        spacing = 4           # Horizontal gap between the square and the label text.

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
        ordered_panels = []
        for panel in desired_panel_order:
            if panel in grouped_selected_markers:
                ordered_panels.append(panel)
        remaining_panels = [p for p in grouped_selected_markers.keys() if p not in desired_panel_order]
        ordered_panels.extend(sorted(remaining_panels))

        for panel in ordered_panels:
            pdf.add_page()  # Open a new page for each panel
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
                    pdf.set_draw_color(115, 115, 115)  # SECONDARY_COLOR
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
                    if (clinical_range_parsed[0] is not None and clinical_range_parsed[1] is not None and
                        optimal_range_parsed[0] is not None and optimal_range_parsed[1] is not None):
                        clinical_min, clinical_max = clinical_range_parsed
                        optimal_min, optimal_max = optimal_range_parsed
                        if optimal_min <= user_numeric <= optimal_max:
                            dot_color = (6, 182, 212)
                        elif user_numeric < clinical_min or user_numeric > clinical_max:
                            dot_color = (255, 85, 85)
                if user_numeric is not None:
                    fig = create_range_chart(marker, marker_info['units'], marker_info['clinical_range'], marker_info['optimal_range'], entered_value)
                    if fig is not None:
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
                        if dot_color is not None:
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
                pdf.set_text_color(115, 115, 115)
                label_width = pdf.get_string_width(clinical_label) + 2
                pdf.cell(label_width, 10, clinical_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                clinical_value = f" {marker_info['clinical_range']}"
                set_font_with_fallback(pdf, "Exo2", "B", 14, clinical_value)
                value_width = pdf.get_string_width(clinical_value) + 2
                pdf.cell(value_width, 10, clinical_value, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                pdf.cell(10, 10, "", border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                optimal_label = "Optimal Range:"
                set_font_with_fallback(pdf, "Exo2", "", 14, optimal_label)
                pdf.set_text_color(6, 182, 212)
                label_width = pdf.get_string_width(optimal_label) + 2
                pdf.cell(label_width, 10, optimal_label, border=0, new_x=XPos.RIGHT, new_y=YPos.TOP)
                optimal_value = f" {marker_info['optimal_range']}"
                set_font_with_fallback(pdf, "Exo2", "B", 14, optimal_value)
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


# ====================================================
# Close the Database Connection on App Exit
# ====================================================
conn.close()
