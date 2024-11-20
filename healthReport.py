import streamlit as st
from fpdf import FPDF
import fitz  # PyMuPDF
from PIL import Image

# Path to the PDF template
template_pdf_path = "1st Optimal Treatment Plan.pdf"

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
     "indication": "Markers: SHBG, Free Testosterone, Total PSA, Total Testosterone, Estradiol."},
    {"name": "Male Basic Hormone Health Panel",
     "description": "Get a clear snapshot of your essential hormone levels to uncover hidden imbalances impacting your energy, performance, and overall health.",
     "indication": "Markers: Total Testosterone, Free Testosterone, Estradiol, SHBG, Prolactin, LH, FSH, PSA, Lipid Panel, HbA1c, CBC, Metabolic Panel."},
    {"name": "Male Hormone Health Panel",
     "description": "Dive deeper into your hormone profile to optimize strength, recovery, weight loss, and physical vitality tailored to your unique needs.",
     "indication": "Markers: Testosterone, SHBG, DHEA-S, PSA, TSH, Free T3, Free T4, IGF-1, Lipid Panel, HbA1c, CBC, Metabolic Panel, Fasting Insulin."},
    {"name": "Male Comprehensive Hormone Panel",
     "description": "A full-spectrum hormone analysis to ensure you're at your peak in energy, performance, weight management, and overall health.",
     "indication": "Markers: Total Testosterone (uncapped), SHBG, Cortisol, Progesterone, DHEA-S, PSA, Thyroid Panel, IGF-1, ApoB, Ferritin, HbA1c, Inflammatory Markers, and more."},
    {"name": "Male Follow-Up Panel",
     "description": "Track your progress and ensure your treatment is delivering optimal results in strength, performance, hormone, and weight management.",
     "indication": "Markers: Estradiol, SHBG, PSA, CBC, Metabolic Panel."},
    {"name": "Female Hormone Health Panel",
     "description": "Unlock insights into your hormones to enhance energy, weight loss, and physical well-being with a tailored approach to your health.",
     "indication": "Markers: Testosterone, Estradiol, SHBG, DHEA-S, Progesterone, Thyroid Panel, Lipid Panel, HbA1c, CBC, and more."},
    {"name": "Female Comprehensive Hormone Health Panel",
     "description": "A detailed hormone assessment to optimize performance, balance, and physical appearance for a healthier, more confident you.",
     "indication": "Markers: Testosterone (uncapped), Estradiol, SHBG, Progesterone, Cortisol, Thyroid Panel, ApoB, Ferritin, HbA1c, Inflammatory Markers, and more."}
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
     "indication": "Low energy and worry about bone health."}
]

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
        for page_num in range(total_pages - 6, total_pages):
            output_pdf.insert_pdf(template_pdf, from_page=page_num, to_page=page_num)

        output_pdf.save(output_path)

# PDF generation function
def generate_pdf(selected_membership, selected_tests, selected_medications, selected_supplements):
    try:
        generated_pdf_path = "generated_content.pdf"
        output_pdf_path = "final_treatment_plan.pdf"

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        pdf.add_font("DejaVu", "", "DejaVuSans.ttf")
        pdf.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf")
        pdf.add_font("DejaVu", "I", "DejaVuSans-Oblique.ttf")

        pdf.set_text_color(6, 182, 212)
        pdf.set_font("DejaVu", "B", 16)
        pdf.cell(0, 10, "1st Optimal Treatment Plan", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        def add_section(title, items, data_source, show_price=False):
            pdf.set_fill_color(230, 230, 250)
            pdf.set_text_color(6, 182, 212)
            pdf.set_font("DejaVu", "B", 14)
            pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
            pdf.ln(5)

            pdf.set_text_color(115, 115, 115)
            pdf.set_font("DejaVu", "", 12)
            for item_name in items:
                item = next((x for x in data_source if x['name'] == item_name), None)
                if item:
                    pdf.set_font("DejaVu", "B", 12)
                    pdf.cell(0, 8, f"{item['name']}", new_x="LMARGIN", new_y="NEXT")

                    pdf.set_font("DejaVu", "B", 10)
                    pdf.cell(0, 6, "Description:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("DejaVu", "", 10)
                    pdf.multi_cell(0, 6, f"  {item.get('description', 'No description available.')}")

                    pdf.ln(3)
                    pdf.set_font("DejaVu", "B", 10)
                    pdf.cell(0, 6, "Indication:", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_font("DejaVu", "", 10)
                    pdf.multi_cell(0, 6, f"  {item.get('indication', 'No indication provided.')}")
                    pdf.ln(3)

                    if show_price:
                        pdf.set_font("DejaVu", "B", 10)
                        pdf.cell(0, 6, "Price:", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("DejaVu", "", 10)
                        pdf.multi_cell(0, 6, f"  {item.get('price', 'TBD')}")
                        pdf.ln(3)
                        
                    pdf.cell(0, 1, "", new_x="LMARGIN", new_y="NEXT")
                    pdf.set_draw_color(180, 180, 180)
                    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                    pdf.ln(5)

        add_section("Membership", selected_membership, memberships, show_price=True)
        add_section("Diagnostic Testing", selected_tests, diagnostic_tests, show_price=False)
        add_section("Medications", selected_medications, medications, show_price=False)
        add_section("Supplements", selected_supplements, supplements, show_price=False)

        # Save generated content PDF
        pdf.output(generated_pdf_path)

        # Merge template, generated content, and additional pages
        merge_pdfs(template_pdf_path, generated_pdf_path, output_pdf_path)

        return output_pdf_path
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None
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
    if selected_membership or selected_tests or selected_medications or selected_supplements:
        pdf_path = generate_pdf(selected_membership, selected_tests, selected_medications, selected_supplements)
        if pdf_path:
            st.success("PDF generated successfully!")
            with open(pdf_path, "rb") as pdf_file:
                st.download_button("Download Treatment Plan", data=pdf_file, file_name="treatment_plan.pdf", mime="application/pdf")
        else:
            st.error("PDF generation failed.")
    else:
        st.warning("Please select at least one item from any category.")
