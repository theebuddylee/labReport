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

# Company Contact Information, Replace with API call later
contact_info = {
    "Allison": {
        "first_name": "Allison",
        "last_name": "Whiteley",
        "alias_title": "Membership Manager 3",
        "email": "mm3@1stoptimal.com",
        "phone": "(816) 744-6814 x103",
    },
    "Amber": {
        "first_name": "Amber",
        "last_name": "Miller",
        "alias_title": "Support",
        "email": "support@1stoptimal.com",
        "phone": "(816) 744-6814 x100",
    },
    "Buddy": {
        "first_name": "Buddy",
        "last_name": "Turner",
        "alias_title": "Advisor",
        "email": "Buddy@1stOptimal.com",
        "phone": "815.601.3406",
    },
    "Dillon": {
        "first_name": "Dillon",
        "last_name": "Hunter",
        "alias_title": "Production Team Member",
        "email": "dillon.hunter@1stoptimal.com",
        "phone": "(816) 744-6814 x301",
    },
    "Justin": {
        "first_name": "Justin",
        "last_name": "Hokams",
        "alias_title": "Membership Manager 1",
        "email": "mm1@1stoptimal.com",
        "phone": "(816) 744-6814 x101",
    },
    "Joe": {
        "first_name": "Joe",
        "last_name": "Miller",
        "alias_title": "Founder",
        "email": "joe.miller@1stoptimal.com",
        "phone": "(816) 744-6814 x300",
    },
    "Ramsey": {
        "first_name": "Michael",
        "last_name": "Ramsey",
        "alias_title": "Membership Manager 2",
        "email": "mm2@1stoptimal.com",
        "phone": "(816) 744-6814 x102",
    },
}

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
     "indication": "SHBG, Free Testosterone, Total PSA, Total Testosterone, Estradiol."},
    {"name": "Male Basic Hormone Health Panel",
     "description": "Get a clear snapshot of your essential hormone levels to uncover hidden imbalances impacting your energy, performance, and overall health.",
     "indication": "Total Testosterone, Free Testosterone, Estradiol, Standard, SHBG, Prolactin, LH, FSH, PSA, Lipid Panel, HbA1c, CBC, Metabolic Panel."},
    {"name": "Male Hormone Health Panel",
     "description": "Dive deeper into your hormone profile to optimize strength, recovery, weight loss, and physical vitality tailored to your unique needs.",
     "indication": "Total Testosterone*, Free Testosterone*, Estradiol, Standard, SHBG, Prolactin, LH, FSH, DHEA-S, PSA, TSH, Free T3, Free T4, IGF-1, Lipid Panel, HbA1c, CBC, Metabolic Panel, Fasting Insulin, Vitamin D, GGT."},
    {"name": "Male Comprehensive Hormone Panel",
     "description": "A full-spectrum hormone analysis to ensure you're at your peak in energy, performance, weight management, and overall health.",
     "indication": "Total Testosterone (LC/MS) [uncapped], Free Testosterone (Equilibrium Ultrafiltration) [uncapped], Estradiol (LC/MS), SHBG, Prolactin, Cortisol, Progesterone, LH, FSH, DHEA-S, PSA, TSH, Free T3, Free T4, IGF-1, Lipid Panel, ApoB, Lipoprotein (a), Ferritin, HbA1c, CBC, Metabolic Panel, Fasting Insulin, GGT, Vitamin D, Iron Panel, hsCRP."},
    {"name": "Male Follow-Up Panel",
     "description": "Track your progress and ensure your treatment is delivering optimal results in strength, performance, hormone, and weight management.",
     "indication": "Estradiol, Standard, SHBG, PSA, CBC, Metabolic Panel."},
    {"name": "Female Hormone Health Panel",
     "description": "Take control of your hormonal health with our comprehensive Women's Hormone Panel. This test evaluates key hormones that influence energy, mood, menstrual cycles, and overall well-being. Gain insights into imbalances affecting fertility, PMS, or irregular cycles and start your journey toward optimal health today!",
     "indication": "Total Testosterone*, Free Testosterone*, Estradiol, Standard, SHBG, DHEA-S, Progesterone, LH, FSH, TSH, Free T3, Free T4, IGF-1, Lipid Panel, Ferritin, Iron, CBC, Metabolic Panel, HbA1c, Fasting Insulin, Vitamin D, GGT."},
    {"name": "Female Comprehensive Hormone Health Panel",
     "description": "Take control of your hormonal health with our comprehensive Women's Hormone Panel. This test evaluates key hormones that influence energy, mood, menstrual cycles, and overall well-being.",
     "indication": "Total Testosterone (LC/MS) [uncapped], Free Testosterone (Equilibrium Ultrafiltration) [uncapped], Estradiol (LC/MS), SHBG, Progesterone, Prolactin, Cortisol, LH, FSH, DHEA-S, TSH, Free T3, Free T4, IGF-1, Lipid Panel, ApoB, Lipoprotein (a), Ferritin, HbA1c, CBC, Metabolic Panel, Fasting Insulin, GGT, Vitamin D, Iron Panel, hsCRP."}
]

# Medications
medications = [
    {"name": "Anastrozole",
     "description": "A medication used to manage estrogen levels in men undergoing testosterone replacement therapy (TRT). It works as an aromatase inhibitor, blocking the conversion of testosterone to estrogen, thereby maintaining optimal hormonal balance.",
     "indication": "Designed to maintain hormonal balance by managing estrogen levels. By reducing excess estrogen, Anastrozole helps improve energy, mood, and muscle definition while minimizing side effects like water retention or fatigue."},
    {"name": "DHEA",
     "description": "A hormone produced by the adrenal glands. It serves as a precursor to sex hormones like testosterone and estrogen and counterbalances cortisol, the stress hormone.",
     "indication": "Restores hormonal balance, boosts energy, mood, and sexual health. Enhance stress resilience, immunity, and overall well-being, an essential for longevity and performance optimization."},
    {"name": "Enclomiphene",
     "description": "A selective estrogen receptor modulator (SERM) used to increase testosterone production in men by stimulating the natural production of luteinizing hormone (LH) and follicle-stimulating hormone (FSH).",
     "indication": "A powerful testosterone booster that enhances natural production while supporting fertility. Unlike traditional options, Enclomiphene helps maintain testicular function and sperm count, ensuring optimized hormone levels without compromising reproductive health."},
    {"name": "Levothyroxin",
     "description": "A synthetic form of thyroid hormone used to treat hypothyroidism. It helps restore proper metabolism, energy levels, and overall thyroid function.",
     "indication": "Boost energy, metabolism, and overall wellness with Levothyroxine—the gold standard in thyroid hormone replacement therapy."},
    {"name": "Retatrutide",
     "description": "A next-generation multi-receptor agonist used in clinical trials for weight management and metabolic improvements.",
     "indication": "The next-generation triple-action peptide therapy. By targeting GLP-1, GIP, and glucagon receptors, Retatrutide supports enhanced appetite control, improved metabolic health, and sustainable fat loss."},
    {"name": "Semaglutide",
     "description": "A GLP-1 receptor agonist used for weight loss and blood sugar management.",
     "indication": "The proven GLP-1 receptor agonist. Backed by science, Semaglutide enhances appetite control, stabilizes blood sugar, and promotes sustainable fat loss."},
    {"name": "Sermorelin",
     "description": "A synthetic peptide that stimulates the natural release of growth hormone from the pituitary gland.",
     "indication": "Boost your growth hormone levels naturally with Sermorelin, a peptide therapy designed to enhance fat loss, improve muscle tone, and support recovery."},
    {"name": "Sildenafil",
     "description": "Commonly known as Viagra, this medication treats erectile dysfunction by increasing blood flow to the penis.",
     "indication": "Enhance your confidence and performance with improved blood flow and vitality."},
    {"name": "Tadalafil",
     "description": "A long-acting PDE5 inhibitor used to treat erectile dysfunction and improve urinary symptoms associated with benign prostatic hyperplasia (BPH).",
     "indication": "Long-lasting support for improved performance and blood flow, helping you feel and perform at your best."},
    {"name": "Tesamorelin",
     "description": "A peptide therapy that boosts natural growth hormone production.",
     "indication": "Achieve targeted fat loss and enhanced metabolic health with Tesamorelin. Known for its ability to reduce stubborn visceral fat, it supports improved body composition, muscle definition, and energy."},
    {"name": "Testosterone Capsule",
     "description": "An oral testosterone replacement therapy option that supports hormone balance and improves symptoms of low testosterone such as fatigue, low libido, and reduced muscle mass.",
     "indication": "A convenient way to boost testosterone for improved energy, strength, and physical appearance."},
    {"name": "Testosterone Cream",
     "description": "A topical testosterone replacement therapy applied directly to the skin.",
     "indication": "Easily applied, this therapy enhances testosterone levels for better performance, weight loss, and muscle tone."},
    {"name": "Testosterone Injectable",
     "description": "An injectable form of testosterone replacement therapy that delivers consistent hormone levels.",
     "indication": "A powerful, direct approach to optimizing testosterone for peak strength, vitality, and a leaner physique."},
    {"name": "Tirzepatide",
     "description": "A novel dual-receptor agonist for weight management.",
     "indication": "The dual-action GLP-1 and GIP receptor agonist. Tirzepatide targets multiple pathways to enhance appetite control, improve insulin sensitivity, and promote effective fat loss."}
]

# Supplements
supplements = [
    {"name": "Berberine",
     "description": "A natural compound derived from plants that supports blood sugar regulation and metabolic health.",
     "indication": "Nature’s powerful metabolic optimizer. Known for its ability to support healthy blood sugar levels, improve insulin sensitivity, and promote fat metabolism."},
    {"name": "Creatine",
     "description": "A naturally occurring compound stored in muscles and used to produce energy during high-intensity activities.",
     "indication": "Fuel your body and mind with Creatine. By enhancing energy production, Creatine helps maintain muscle mass during aging or recovery while also improving memory, focus, and mental clarity."},
    {"name": "Cortisol Calm",
     "description": "A supplement designed to support adrenal health and stress management by balancing cortisol levels.",
     "indication": "A premium adaptogen blend designed to regulate cortisol levels and support a balanced stress response."},
    {"name": "Douglas Labs D3 Liquid",
     "description": "A high-potency liquid vitamin D3 supplement that supports bone health, immune function, and optimal calcium absorption.",
     "indication": "Boost your immune system and improve overall health with this easily absorbed vitamin D3."},
    {"name": "GLP-1 Agonist Side Effect Support Bundle",
     "description": "A combination of supplements designed to alleviate common side effects of GLP-1 receptor agonist therapies.",
     "indication": "GLP-1 therapy side effects with our GLP-1 Agonist Side Effect Support Bundle."},
    {"name": "GLP-1 Probiotic Pro",
     "description": "A specialized probiotic blend formulated to enhance gut health and improve gastrointestinal tolerance in individuals using GLP-1 agonists.",
     "indication": "Enhance your GLP-1 journey with our Probiotic Support."},
    {"name": "Thyroid Support Bundle",
     "description": "A comprehensive supplement package designed to support thyroid function.",
     "indication": "Optimize your thyroid function with our Thyroid Support Bundle, featuring Selenium, D3 Liquid, and more."},
    {"name": "Magnesium",
     "description": "An essential mineral that supports muscle function, energy production, nerve health, and sleep quality.",
     "indication": "Stress depletes magnesium levels, impairing relaxation, sleep, and muscle function. Magnesium helps regulate the nervous system, reduce cortisol, and promote a calm, balanced mood."},
    {"name": "Multi-Vitamin Premier",
     "description": "A high-quality multivitamin providing essential vitamins, minerals, and antioxidants.",
     "indication": "A high-quality multivitamin to fill nutritional gaps and support overall health and vitality."},
    {"name": "Joint Health Bundle",
     "description": "A supplement pack that supports joint health and mobility, featuring ingredients like glucosamine, chondroitin, and MSM.",
     "indication": "Relieve joint pain and support musculoskeletal health with our comprehensive Joint Support Bundle."},
    {"name": "Omega-3",
     "description": "A fatty acid supplement derived from fish oil, providing EPA and DHA for heart health, brain function, and anti-inflammatory support.",
     "indication": "Omega-3s help reduce systemic inflammation, protect cardiovascular health, and improve joint mobility."},
    {"name": "Tudca",
     "description": "A bile acid supplement that supports liver health and detoxification processes.",
     "indication": "A breakthrough bile acid supplement. TUDCA supports optimal liver function by promoting bile flow, reducing liver inflammation, and protecting against oxidative stress."},
    {"name": "Vitamin D",
     "description": "A critical vitamin for bone health, immune function, and mood regulation.",
     "indication": "Support your overall health with Vitamin D3, essential for strong bones, a robust immune system, and optimal mood."}
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

# Function to write More Information Sections of 1st and last page
def overwrite_more_information(template_path, output_path, member_name, selected_manager):
    try:
        # Set your desired timezone
        local_timezone = pytz.timezone("America/Los_Angeles")
        current_date = datetime.now(local_timezone).strftime("%m-%d-%Y")

        # Retrieve manager info from the dictionary
        manager_info = contact_info.get(selected_manager, {"email": "N/A", "phone": "N/A"})
        manager_name = f"{manager_info.get('first_name', 'Unknown')} {manager_info.get('last_name', 'Unknown')}"
        manager_email = manager_info.get("email", "N/A")
        manager_phone = manager_info.get("phone", "N/A")

        # Open the template PDF
        doc = fitz.open(template_path)
        first_page = doc[0]  # Access the first page
        last_page = doc[-1]  # Access the last page

        # Define the text to insert on the first page
        first_page_content = [
            (f"Prepared for {member_name or 'Not Provided'}", 1.1 * 72, 8.8 * 72),
            (f"{current_date}", 1.1 * 72, 9.31 * 72),
            (f"Prepared by {selected_manager or 'Not Selected'}", 1.1 * 72, 9.85 * 72),
        ]

        # Write the text on the first page
        for content, x, y in first_page_content:
            first_page.insert_text(
                (x, y),
                content,
                fontsize=21,
                color=(1, 1, 1),  # White text color
                fontname="helv",
            )

        # Define the text to insert on the last page
        last_page_content = [
            (f"Member Manager: {manager_name}", 73, 8.36 * 72),
            (f"Phone: {manager_phone}", 73, 8.84 * 72),
        ]

        # Write the text on the last page
        for content, x, y in last_page_content:
            last_page.insert_text(
                (x, y),
                content,
                fontsize=21,
                color=(1, 1, 1),  # White text color
                fontname="helv",
            )

        # Add clickable email hyperlink
        email_text = f"Email: {manager_email}"
        email_x = 73  # X coordinate
        email_y = 9.36 * 72  # Y coordinate
        last_page.insert_text(
            (email_x, email_y),
            email_text,
            fontsize=21,
            color=(0.0235, 0.7137, 0.8314),  # Corresponds to #06B6D4
            fontname="helv",
        )
        if manager_email != "N/A":
            # Add a clickable hyperlink
            email_rect = fitz.Rect(email_x, email_y, email_x + 300, email_y + 21)  # Adjust width and height as needed
            last_page.insert_link({
                "kind": fitz.LINK_URI,
                "from": email_rect,
                "uri": f"mailto:{manager_email}",
            })

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

# GitHub Configuration
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]  # Securely stored in Streamlit secrets
REPO_NAME = "theebuddylee/HealthReport"
FILE_PATH = "analytics.json"

def log_to_github(data):
    # Add a timestamp to the data
    data["timestamp"] = datetime.now().isoformat()

    try:
        # Authenticate with GitHub
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)

        # Fetch the current analytics.json file
        file = repo.get_contents(FILE_PATH)
        analytics_data = json.loads(file.decoded_content.decode())
    except Exception:
        # If the file doesn't exist or is empty, initialize as an empty list
        analytics_data = []

    # Append the new data
    analytics_data.append(data)

    # Commit the updated file to GitHub
    try:
        if 'file' in locals():
            # Update the existing file
            repo.update_file(FILE_PATH, "Update analytics.json", json.dumps(analytics_data, indent=4), file.sha)
        else:
            # Create a new file if it doesn't exist
            repo.create_file(FILE_PATH, "Create analytics.json", json.dumps(analytics_data, indent=4))
    except Exception as e:
        print(f"Error updating GitHub: {e}")

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
    try:
        log_to_github(data)
        #st.success("Selections logged to GitHub Analytics successfully!")
    except Exception as e:
        st.error(f"Failed to log selections to Analytics: {e}")

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
