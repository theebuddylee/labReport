import streamlit as st
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import sqlite3
import requests
import json

# Branding Colors and Fonts
PRIMARY_COLOR = "#06B6D4"
SECONDARY_COLOR = "#737373"
BACKGROUND_COLOR = "#EBEBEB"
FONT_PRIMARY = "Exo2-Regular.ttf"
FONT_SECONDARY = "Source Sans Pro"

# Streamlit UI with Branding
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

# Membership Manager Dropdown and Member's Name input
st.sidebar.title("Member Details")
membership_managers = ["Allison", "Amber", "Buddy", "Dillon", "Justin", "Joe", "Ramsey"]
selected_manager = st.sidebar.selectbox("Select Membership Manager", membership_managers)
member_name = st.sidebar.text_input("Enter Member/Patient Name")

# Base URL for GitHub raw content
GITHUB_BASE_URL = "https://raw.githubusercontent.com/theebuddylee/HealthReport/main/data/"

# Function to load JSON files from GitHub
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

# Load JSON data
contact_info = load_json_from_github("contact_info.json")
lab_markers = load_json_from_github("lab_markers.json")

# Load and display the logo and page info
logo_path = "1st-Optimal-Logo-Dark.png"  # Replace with your actual logo file path
st.image(logo_path, width=500)  # Adjust width as needed
st.markdown('<h1 class="report-title">Lab Results Report Generator</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Generate The Optimal Lab Report</p>', unsafe_allow_html=True)

# Initialize database
conn = sqlite3.connect("lab_results.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS lab_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    marker TEXT,
    value REAL,
    date TEXT
)
""")
conn.commit()

# ***Select Group of Markers ***
if lab_markers:
    st.markdown("### Select Group of Lab Markers:")
    # The keys of the lab_markers JSON should be the groups, e.g. "Men", "Women", etc.
    selected_group = st.selectbox("Choose a group:", list(lab_markers.keys()))

    # Once a group is selected, retrieve its markers.
    available_markers = lab_markers[selected_group]

    # Now let the user choose markers from the selected group.
    st.markdown("### Select Lab Markers to Include:")
    selected_markers = st.multiselect("Choose lab markers:", list(available_markers.keys()))
else:
    st.error("Lab markers could not be loaded.")
    # Ensure selected_markers is defined even if lab_markers failed to load.
    selected_markers = []

# User inputs values for selected markers (if any)
if selected_markers:
    st.markdown("### Input Lab Results:")
    lab_results = {}
    for marker in selected_markers:
        lab_results[marker] = st.number_input(f"Enter result for {marker}:", min_value=0.0, step=0.1)

    # Save results to the database
    if st.button("Save Results"):
        for marker, value in lab_results.items():
            cursor.execute(
                "INSERT INTO lab_results (marker, value, date) VALUES (?, ?, date('now'))",
                (marker, value)
            )
        conn.commit()
        st.success("Results saved successfully!")

# Generate PDF report
if st.button("Generate PDF"):
    # Validate that a member name has been entered
    if not member_name.strip():
        st.error("Please enter a Member/Patient Name before generating the PDF.")
    elif selected_markers:
        # Error handling: check that at least one lab result is not left at the default 0.0.
        if not any(value != 0.0 for value in lab_results.values()):
            st.error("It appears that none of the lab result values have been updated from 0.0. Please check your inputs before generating the report.")
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
            pdf.cell(0, 10, "1st Optimal Lab Results Report",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            pdf.ln(15)

            pdf.set_text_color(0, 0, 0)
            for marker in selected_markers:
                marker_info = available_markers[marker]
                # Marker name in bold
                pdf.set_font("Exo2", style="B", size=12)
                pdf.cell(0, 10, marker,
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                # Marker description
                pdf.set_font("Exo2", size=10)
                pdf.multi_cell(0, 10, marker_info["description"])
                pdf.ln(5)  # Add some space before result line
                # The entered result (with units)
                entered_value = lab_results[marker]
                pdf.cell(0, 10, f"Result: {entered_value} {marker_info['units']}",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                # Clinical and Optimal ranges
                pdf.cell(0, 10,
                         f"Clinical Range: {marker_info['clinical_range']}   Optimal Range: {marker_info['optimal_range']}",
                         new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(5)

            # Build file name using member name
            file_name = f"{member_name}_lab_interpretation.pdf"
            pdf.output(file_name)
            with open(file_name, "rb") as file:
                st.download_button("Download Report", file, file_name=file_name)
    else:
        st.warning("Please select at least one marker to generate the report.")

# Close the database connection
conn.close()
