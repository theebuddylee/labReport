import streamlit as st
from fpdf import FPDF
import fitz  # PyMuPDF
from PIL import Image
import json
import os
from datetime import datetime
import pytz

# Brand color styles
st.markdown(
    """
    <style>
        h1 {
            color: #06B6D4;
        }
        .subheader {
            color: #737373;
        }
        .light-bg {
            background-color: #EBEBEB;
            padding: 10px;
            border-radius: 5px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Membership Manager Dropdown and Member's Name input
st.sidebar.title("Member Details")
membership_managers = ["Allison", "Amber", "Buddy", "Dillon", "Justin", "Joe", "Ramsey"]
selected_manager = st.sidebar.selectbox("Select Membership Manager", membership_managers)
member_name = st.sidebar.text_input("Enter Member/Patient Name")

# Membership data with descriptions, indication, and monthly prices
memberships = [
    {"name": "Coaching Partnership", "description": "", "indication": "Comprehensive physical training and monitoring.", "price": "USD 200.00/month"},
    {"name": "Performance Care Membership - (T1)", "description": "", "indication": "Ideal for individuals focused on performance enhancement and recovery.", "price": "USD 49.00/month"},
    {"name": "Guided Hormone Care Membership - (T2)", "description": "", "indication": "Hormone care tailored to your lab results for hormonal balance.", "price": "USD 99.00/month"},
    {"name": "Weight Loss Care Membership - (T3)", "description": "", "indication": "Targeted for individuals aiming for sustainable weight loss.", "price": "USD 129.00/month"},
    {"name": "Guided Hormone Care (PLUS) Membership - Member (T4)", "description": "Choose 1: Testosterone Cypionate 10ml/200mg or Enclomiphine", "indication": "Enhanced hormone care with choice of specific treatments for personalized hormone balance.", "price": "USD 159.00/month"},
]

# Diagnostic Tests
diagnostic_tests = [
    {"name": "Male Testosterone Starter Therapy Kit",
     "description": "Convenient, private, and easy-to-use, this kit provides accurate insights into your testosterone levels, helping you optimize strength, energy, and performance from the comfort of your home.",
     "indication": "Lab Markers: SHBG, Free Testosterone, Total PSA, Total Testosterone, Estradiol."},
    {"name": "Male Basic Hormone Health Panel",
     "description": "Get a clear snapshot of your essential hormone levels to uncover hidden imbalances impacting your energy, performance, and overall health.",
     "indication": "Lab Markers: Total Testosterone, Free Testosterone, Estradiol, SHBG, Prolactin, LH, FSH, PSA, Lipid Panel, HbA1c, CBC, Metabolic Panel."},
    {"name": "Male Hormone Health Panel",
     "description": "Dive deeper into your hormone profile to optimize strength, recovery, weight loss, and physical vitality tailored to your unique needs.",
     "indication": "Lab Markers: Testosterone, SHBG, DHEA-S, PSA, TSH, Free T3, Free T4, IGF-1, Lipid Panel, HbA1c, CBC, Metabolic Panel, Fasting Insulin."},
    {"name": "Male Comprehensive Hormone Panel",
     "description": "A full-spectrum hormone analysis to ensure you're at your peak in energy, performance, weight management, and overall health.",
     "indication": "Lab Markers: Total Testosterone (uncapped), SHBG, Cortisol, Progesterone, DHEA-S, PSA, Thyroid Panel, IGF-1, ApoB, Ferritin, HbA1c, Inflammatory Markers, and more."},
    {"name": "Male Follow-Up Panel",
     "description": "Track your progress and ensure your treatment is delivering optimal results in strength, performance, hormone, and weight management.",
     "indication": "Lab Markers: Estradiol, SHBG, PSA, CBC, Metabolic Panel."},
    {"name": "Female Hormone Health Panel",
     "description": "Unlock insights into your hormones to enhance energy, weight loss, and physical well-being with a tailored approach to your health.",
     "indication": "Lab Markers: Testosterone, Estradiol, SHBG, DHEA-S, Progesterone, Thyroid Panel, Lipid Panel, HbA1c, CBC, and more."},
    {"name": "Female Comprehensive Hormone Health Panel",
     "description": "A detailed hormone assessment to optimize performance, balance, and physical appearance for a healthier, more confident you.",
     "indication": "Lab Markers: Testosterone (uncapped), Estradiol, SHBG, Progesterone, Cortisol, Thyroid Panel, ApoB, Ferritin, HbA1c, Inflammatory Markers, and more."}
]

# Medications
medications = [
    {"name": "Anastrozole",
     "description": "A medication used to manage estrogen levels in men undergoing testosterone replacement therapy (TRT).",
     "indication": "Helps maintain hormonal balance and reduce estrogen-related side effects."},
    {"name": "DHEA",
     "description": "A naturally occurring hormone that serves as a precursor to testosterone and estrogen.",
     "indication": "Supports adrenal health, improves energy, and enhances overall hormone balance."},
    {"name": "Enclomiphene",
     "description": "A selective estrogen receptor modulator (SERM) used to increase testosterone production in men.",
     "indication": "Stimulates natural testosterone production to restore vitality and improve performance."},
    {"name": "Levothyroxin",
     "description": "A synthetic form of thyroid hormone used to treat hypothyroidism.",
     "indication": "Restores proper metabolism, energy levels, and overall thyroid function."},
    {"name": "Retatrutide",
     "description": "A next-generation multi-receptor agonist used in clinical trials for weight management.",
     "indication": "Accelerates weight loss and improves metabolic health."},
    {"name": "Semaglutide",
     "description": "A GLP-1 receptor agonist used for weight loss and blood sugar management.",
     "indication": "Improves insulin sensitivity, reduces appetite, and supports weight management."},
    {"name": "Sermorelin",
     "description": "A synthetic peptide that stimulates the natural release of growth hormone.",
     "indication": "Boosts growth hormone for improved recovery, strength, and anti-aging benefits."},
    {"name": "Sildenafil",
     "description": "Commonly known as Viagra, this medication treats erectile dysfunction by increasing blood flow.",
     "indication": "Improves blood flow for better performance and confidence."},
    {"name": "Tadalafil",
     "description": "A long-acting PDE5 inhibitor used to treat erectile dysfunction and improve urinary symptoms.",
     "indication": "Provides long-lasting support for improved performance and blood flow."},
    {"name": "Tesamorelin",
     "description": "A growth hormone-releasing hormone analog that promotes the release of growth hormone.",
     "indication": "Supports fat loss and muscle definition through natural hormone stimulation."},
    {"name": "Testosterone Capsule",
     "description": "An oral testosterone replacement therapy option that supports hormone balance.",
     "indication": "Improves symptoms of low testosterone, including fatigue and reduced muscle mass."},
    {"name": "Testosterone Cream",
     "description": "A topical testosterone replacement therapy applied directly to the skin.",
     "indication": "Enhances testosterone levels for better performance and muscle tone."},
    {"name": "Testosterone Injectable",
     "description": "An injectable form of testosterone replacement therapy that delivers consistent hormone levels.",
     "indication": "Provides a direct approach to optimizing testosterone for peak strength and vitality."},
    {"name": "Trizepitide",
     "description": "A novel dual-receptor agonist for weight management.",
     "indication": "Targets appetite and fat metabolism to accelerate weight loss."}
]

# Supplements
supplements = [
    {"name": "Berberine",
     "description": "A natural compound that supports blood sugar regulation and metabolic health.",
     "indication": "Enhances insulin sensitivity and supports weight loss."},
    {"name": "Creatine",
     "description": "Enhances strength, power, and recovery while supporting brain health.",
     "indication": "Improves muscle performance and cognitive function."},
    {"name": "Cortisol Calm",
     "description": "Designed to support adrenal health and stress management by balancing cortisol levels.",
     "indication": "Reduces stress and improves recovery and sleep quality."},
    {"name": "Douglas Labs D3 Liquid",
     "description": "A high-potency liquid vitamin D3 supplement for bone and immune health.",
     "indication": "Boosts immune system and supports bone health."},
    {"name": "GLP-1 Agonist Side Effect Support Bundle",
     "description": "Alleviates common side effects of GLP-1 receptor agonist therapies.",
     "indication": "Manages nausea and enhances GLP-1 therapy benefits."},
    {"name": "GLP-1 Probiotic Pro",
     "description": "A specialized probiotic blend to enhance gut health for GLP-1 users.",
     "indication": "Improves gastrointestinal tolerance and microbiome balance."},
    {"name": "Thyroid Support Bundle",
     "description": "Nutrients and adaptogens to optimize thyroid function.",
     "indication": "Improves thyroid health and supports metabolism."},
    {"name": "Magnesium",
     "description": "Supports muscle function, energy production, and nerve health.",
     "indication": "Improves recovery, sleep quality, and energy levels."},
    {"name": "Multi-Vitamin Premier",
     "description": "A high-quality multivitamin for nutritional support.",
     "indication": "Fills nutritional gaps for overall health and wellness."},
    {"name": "Joint Health Bundle",
     "description": "Reduces inflammation and improves joint mobility.",
     "indication": "Supports joint health and enhances physical performance."},
    {"name": "Omega-3",
     "description": "Supports heart, brain, and joint health.",
     "indication": "Reduces inflammation and improves cardiovascular health."},
    {"name": "Tudca",
     "description": "A bile acid supplement for liver health.",
     "indication": "Supports liver detoxification and reduces liver stress."},
    {"name": "Vitamin D",
     "description": "Supports bone health, immune function, and mood regulation.",
     "indication": "Enhances energy and bone health for peak wellness."}
]
# Path to the PDF template
template_pdf_path = "1st Optimal Treatment Plan.pdf"

# Function to merge PDFs
def merge_pdfs(template_path, generated_path, output_path):
    with fitz.open(template_path) as template_pdf:
        output_pdf = fitz.open()

        # Add first 2 pages from template
        for page_num in range(2):
            output_pdf.insert_pdf(template_pdf, from_page=page_num, to_page=page_num)

        # Append the generated content PDF
        with fitz.open(generated_path) as generated_pdf:
            output_pdf.insert_pdf(generated_pdf)

        # Append the last 6 pages from the template
        total_pages = len(template_pdf)
        for page_num in range(total_pages - 5, total_pages):
            output_pdf.insert_pdf(template_pdf, from_page=page_num, to_page=page_num)

        output_pdf.save(output_path)

# Function to write More Information Section onto merged PDF
def overwrite_more_information(template_path, output_path, member_name, membership_manager):
    try:
        # Set your desired timezone
        local_timezone = pytz.timezone("America/Los_Angeles")
        current_date = datetime.now(local_timezone).strftime("%m-%d-%Y")

        # Open the template PDF
        doc = fitz.open(template_path)
        page = doc[0]  # Access the first page

        # Define the text to insert with their respective positions
        more_info_content = [
            (f"Prepared for {member_name or 'Not Provided'}", 1.1 * 72, 8.8 * 72),  # X: 1.1 inches, Y: 8.81 inches
            (f"{current_date}", 1.1 * 72, 9.31 * 72),  # X: 1.1 inches, Y: 9.3 inches
            (f"Prepared by {membership_manager or 'Not Selected'}", 1.1 * 72, 9.85 * 72),  # X: 1.1 inches, Y: 9.85 inches
        ]

        # Write the text on the PDF at the specified coordinates
        for content, x, y in more_info_content:
            page.insert_text(
                (x, y),
                content,
                fontsize=21,
                color=(1, 1, 1),  # White text color
                fontname="helv",  # Replace with Exo 2 when supported
            )

        # Save the updated PDF
        doc.save(output_path)
        doc.close()
        return output_path
    except Exception as e:
        print(f"Error in overwrite_more_information: {e}")
        return None

# PDF generation function
def generate_pdf(selected_membership, selected_tests, selected_medications, selected_supplements):
    try:
        generated_pdf_path = "generated_content.pdf"
        merged_pdf_path = "final_treatment_plan.pdf"
        updated_pdf_path = "updated_treatment_plan.pdf"

        # Step 1: Generate the content PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Add Exo 2 font
        pdf.add_font("Exo2", "", "Exo2-Regular.ttf")
        pdf.add_font("Exo2", "B", "Exo2-Bold.ttf")
        pdf.add_font("Exo2", "I", "Exo2-Italic.ttf")

        pdf.set_text_color(6, 182, 212)
        pdf.set_font("Exo2", "B", 36)
        pdf.cell(0, 10, "1st Optimal Treatment Plan", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        # Add sections for selected items
        def add_section(title, items, data_source, show_price=False):
            pdf.set_fill_color(230, 230, 250)
            pdf.set_text_color(6, 182, 212)
            pdf.set_font("Exo2", "B", 22)
            pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
            pdf.ln(5)

            pdf.set_text_color(115, 115, 115)
            pdf.set_font("Exo2", "", 22)
            for item_name in items:
                item = next((x for x in data_source if x['name'] == item_name), None)
                if item:
                    pdf.set_font("Exo2", "B", 20)
                    pdf.cell(0, 8, f"{item['name']}", new_x="LMARGIN", new_y="NEXT")

                    pdf.set_font("Exo2", "B", 16)
                    pdf.cell(0, 6, "Description:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Exo2", "", 14)
                    pdf.multi_cell(0, 6, f"  {item.get('description', 'No description available.')}")

                    pdf.ln(3)
                    pdf.set_font("Exo2", "B", 16)
                    pdf.cell(0, 6, "Indication:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("Exo2", "", 14)
                    pdf.multi_cell(0, 6, f"  {item.get('indication', 'No indication provided.')}")

                    if show_price:
                        pdf.ln(3)
                        pdf.set_font("Exo2", "B", 16)
                        pdf.cell(0, 6, "Price:", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("Exo2", "", 14)
                        pdf.multi_cell(0, 6, f"  {item.get('price', 'TBD')}")
                    pdf.ln(5)

        add_section("Membership", selected_membership, memberships, show_price=True)
        add_section("Diagnostic Testing", selected_tests, diagnostic_tests, show_price=False)
        add_section("Medications", selected_medications, medications, show_price=False)
        add_section("Supplements", selected_supplements, supplements, show_price=False)

        # Step 2: Save the generated content PDF
        pdf.output(generated_pdf_path)

        # Step 3: Merge the template and content PDFs
        merge_pdfs(template_pdf_path, generated_pdf_path, merged_pdf_path)

        # Step 4: Overwrite "More Information" section
        overwrite_more_information(
            merged_pdf_path,
            updated_pdf_path,
            member_name,
            selected_manager,
        )

        return updated_pdf_path
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

# File path for analytics data
analytics_file = "analytics.json"

# Function to log selections
def log_selections(data):
    # Add a timestamp to the data
    data["timestamp"] = datetime.now().isoformat()

    # Check if the file exists, otherwise create an empty list
    if os.path.exists(analytics_file):
        with open(analytics_file, "r") as file:
            try:
                analytics_data = json.load(file)
            except json.JSONDecodeError:
                # If the file exists but is corrupted or empty, start fresh
                analytics_data = []
    else:
        analytics_data = []

    # Append the new data to the analytics
    analytics_data.append(data)

    # Write the updated analytics back to the file
    with open(analytics_file, "w") as file:
        json.dump(analytics_data, file, indent=4)

# Load and display the logo
logo_path = "1st-Optimal-Logo-Dark (500x500 px).png"  # Replace with your actual logo file path
st.image(logo_path, width=500)  # Adjust width as needed

# Streamlit UI
st.title("1st Optimal Treatment Plan Generator")
st.subheader("Select Products for Your Report")

selected_membership = st.multiselect("Membership", [item['name'] for item in memberships], max_selections=1)
selected_tests = st.multiselect("Diagnostic Testing", [item['name'] for item in diagnostic_tests], max_selections=5)
selected_medications = st.multiselect("Medications", [item['name'] for item in medications], max_selections=5)
selected_supplements = st.multiselect("Supplements", [item['name'] for item in supplements], max_selections=10)

if "Guided Hormone Care (PLUS) Membership - Member (T4)" in selected_membership:
    st.info(memberships[-1]["description"])

if st.button("Generate PDF"):
    data = {
        "member_name": member_name,
        "manager": selected_manager,
        "membership": selected_membership,
        "tests": selected_tests,
        "medications": selected_medications,
        "supplements": selected_supplements,
    }
    log_selections(data)
    if selected_membership or selected_tests or selected_medications or selected_supplements:
        pdf_path = generate_pdf(selected_membership, selected_tests, selected_medications, selected_supplements)
        if pdf_path:
            st.success("PDF generated successfully!")
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("Download Treatment Plan", data=pdf_file, file_name="1stOptimal_treatment_plan.pdf", mime="application/pdf")
        else:
            st.error("PDF generation failed.")
    else:
        st.warning("Please select at least one item from any category.")
