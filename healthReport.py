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

# Full data for each category with descriptions and lab indication
diagnostic_tests = [
    {"name": "Men's Testosterone Therapy Starter Kit", "description": "", "indication": "Used to test Low-T for non-T users"},
    {"name": "Male Basic Hormone Health Panel", "description": "", "indication": "Great for Starter Membership Panel"},
    {"name": "Men's Hormone Health Panel", "description": "", "indication": "Great panel covering all bases"},
    {"name": "Male Comprehensive Hormone Panel", "description": "", "indication": "Great for health enthusiast"},
    {"name": "Male Follow-up Panel", "description": "", "indication": "Adjustable based on treatment, Included (free) in TRT membership"},
]

# Updated medications data with Descriptions and Indications
medications = [
    {"name": "Anastrozole", "description": "An aromatase inhibitor that reduces estrogen production, often used in hormone therapy to prevent estrogen-related side effects.", "indication": "Recommended for individuals on testosterone therapy who may experience elevated estrogen levels."},
    {"name": "DHEA", "description": "A hormone that helps improve adrenal health and hormone balance.", "indication": "Suggested when DHEA-S levels are low in lab results."},
    {"name": "Enclomiphene", "description": "A selective estrogen receptor modulator (SERM) that stimulates natural testosterone production in men.", "indication": "Commonly used in individuals with low testosterone levels, particularly as an alternative to direct testosterone supplementation."},
    {"name": "Levothyroxin (Synthroid)", "description": "A synthetic thyroid hormone replacement used to treat hypothyroidism by normalizing thyroid hormone levels.", "indication": "Prescribed for individuals with low thyroid function or hypothyroidism."},
    {"name": "Retatrutide", "description": "A multi-receptor agonist for weight loss and metabolic health.", "indication": "Considered if metabolic markers indicate high risk for diabetes or obesity."},
    {"name": "Semaglutide", "description": "Medication for weight management by reducing appetite and regulating blood sugar.", "indication": "Commonly prescribed if fasting glucose or HbA1c levels are elevated."},
    {"name": "Sermorelin", "description": "A growth hormone secretagogue that stimulates the body’s natural production of growth hormone, aiding in recovery, muscle growth, and fat loss.", "indication": "Beneficial for individuals with low growth hormone levels or those seeking to improve body composition."},
    {"name": "Sildenafil", "description": "A phosphodiesterase type 5 (PDE5) inhibitor used to treat erectile dysfunction by increasing blood flow to the penis.", "indication": "Recommended for men experiencing erectile dysfunction."},
    {"name": "Tadalafil", "description": "A PDE5 inhibitor used to treat erectile dysfunction and benign prostatic hyperplasia by increasing blood flow.", "indication": "Commonly prescribed for erectile dysfunction and symptoms of an enlarged prostate."},
    {"name": "Tesamorelin", "description": "A growth hormone-releasing hormone analog that promotes the release of growth hormone, often used to reduce abdominal fat in adults.", "indication": "Recommended for reducing visceral fat, particularly in individuals with growth hormone deficiencies."},
    {"name": "Testosterone Capsule", "description": "Used to supplement low testosterone levels and improve energy, mood, and muscle mass.", "indication": "Recommended when testosterone levels are below normal range."},
    {"name": "Testosterone Cream", "description": "Used to supplement low testosterone levels and improve energy, mood, and muscle mass.", "indication": "Recommended when testosterone levels are below normal range."},
    {"name": "Testosterone Cypionate Injection", "description": "Used to supplement low testosterone levels and improve energy, mood, and muscle mass.", "indication": "Recommended when testosterone levels are below normal range."},
    {"name": "Trizepitide", "description": "Helps in weight management and blood sugar control through multiple pathways.", "indication": "Recommended for elevated blood sugar or insulin resistance."}
]

# Updated supplements with Description and Indication
supplements = [
    {
        "name": "Berberine (Thorne)",
        "description": "A natural compound shown to support healthy blood sugar levels, improve insulin sensitivity, and support gut health.",
        "indication": "Recommended for those managing blood sugar levels or seeking metabolic health support."
    },
    {
        "name": "Creatine (450g)",
        "description": "A supplement that enhances muscle strength, power, and recovery, commonly used in fitness and sports performance.",
        "indication": "Ideal for athletes or individuals looking to increase muscle mass and improve performance."
    },
    {
        "name": "Cortisol Calm",
        "description": "A formula designed to help reduce stress and support adrenal health, promoting relaxation and balanced cortisol levels.",
        "indication": "Ideal for managing stress and supporting the body's response to adrenal fatigue."
    },
    {
        "name": "Douglas Labs D3 Liquid Vitamin (2oz)",
        "description": "Liquid vitamin D3 for supporting bone health, immune function, and optimal vitamin D levels.",
        "indication": "Suggested for individuals with low vitamin D levels or those needing immune and bone support."
    },
    {
        "name": "GLP-1 Agonist Side Effect Support Bundle",
        "description": "A bundle designed to mitigate side effects associated with GLP-1 agonist medications, promoting digestive health and supporting metabolic function.",
        "indication": "Recommended for individuals using GLP-1 agonists to manage side effects like nausea and digestive discomfort."
    },
    {
        "name": "GLP-1 Probiotic Pro (30 caps)",
        "description": "A probiotic formula that supports gut health, particularly beneficial for those taking GLP-1 medications.",
        "indication": "Recommended for maintaining gut health and balancing the microbiome, especially for GLP-1 users."
    },
    {
        "name": "Hormonal Health – Thyroid Support Bundle",
        "description": "A targeted bundle supporting thyroid function, providing essential nutrients for hormone synthesis and regulation.",
        "indication": "Beneficial for those with low thyroid function or seeking to optimize hormonal health."
    },
    {
        "name": "Magnesium",
        "description": "Essential for muscle and nerve function, heart health, and bone strength.",
        "indication": "Recommended if magnesium levels are low in blood tests."
    },
    {
        "name": "Multi-Vitamin Premier (Thorne)",
        "description": "A high-quality multivitamin providing a comprehensive range of vitamins and minerals to support daily nutritional needs.",
        "indication": "Great for overall health and wellness, especially for individuals with nutrient deficiencies."
    },
    {
        "name": "Musculoskeletal Health – Joint Pain Bundle",
        "description": "Comprehensive support for joint health, containing key nutrients for reducing inflammation and improving joint mobility.",
        "indication": "Ideal for those experiencing joint pain or stiffness, or as part of a recovery regimen."
    },
    {
        "name": "Omega-3",
        "description": "An essential fatty acid that supports heart and brain health.",
        "indication": "Beneficial if lipid panel shows high triglycerides or low HDL."
    },
    {
        "name": "OmegaGenics EPA-DHA 1000 Fish Oil (60 caps)",
        "description": "High-potency fish oil providing omega-3 fatty acids for cardiovascular, brain, and joint health.",
        "indication": "Beneficial for heart health, cognitive function, and reducing inflammation."
    },
    {
        "name": "Tudca Body Bio",
        "description": "A supplement that supports liver health, bile flow, and cellular protection, particularly beneficial for detoxification.",
        "indication": "Recommended for liver support and for those undergoing detox or taking medications that affect liver function."
    },
    {
        "name": "Vitamin D",
        "description": "Supports bone health and immune function, especially if Vitamin D levels are low.",
        "indication": "Suggested if 25-hydroxy vitamin D levels are below optimal."
    },
]


lifestyle_recommendations = [
    "Follow CDC Exercise Guidelines: Engage in at least 150 minutes of moderate-intensity aerobic activity per week.",
    "Prioritize Sleep Quality and Quantity: Aim for 7–9 hours of quality sleep per night.",
    "Optimize Nutrient Intake: Follow a balanced diet with essential nutrients for hormone health.",
    "Incorporate Resistance Training: Perform strength training 2-3 times per week with compound movements.",
    "Manage Stress Levels: Incorporate daily stress management practices like mindfulness or breathing exercises.",
    "Limit Alcohol and Avoid Smoking: Limit alcohol intake and quit smoking for optimal hormone balance.",
    "Maintain a Healthy Weight: Aim for a BMI in the range of 18.5–24.9 to support hormone health.",
    "Stay Hydrated: Aim for 3.7 liters/day for men and 2.7 liters/day for women.",
    "Reduce Sugar and Processed Foods: Limit added sugars to less than 10% of daily calories.",
    "Get Regular Sun Exposure or Supplement Vitamin D: Aim for adequate sun exposure or supplement as needed.",
]
# Load and display the logo
logo_path = "1st-Optimal-Logo-Dark (500x500 px).png"  # Replace with your actual logo file path
st.image(logo_path, width=500)  # Adjust width as needed

# Streamlit UI setup
st.title("1st Optimal Treatment Plan Generator")
st.subheader("Select Products for Your Report")

# Selection Widgets
selected_membership = st.multiselect("Membership", [item['name'] for item in memberships], max_selections=1)
selected_tests = st.multiselect("Diagnostic Testing", [item['name'] for item in diagnostic_tests], max_selections=5)
selected_medications = st.multiselect("Medications", [item['name'] for item in medications], max_selections=5)
selected_supplements = st.multiselect("Supplements", [item['name'] for item in supplements], max_selections=10)

# Show popup for the Guided Hormone Care (PLUS) Membership description
if "Guided Hormone Care (PLUS) Membership - Member (T4)" in selected_membership:
    st.info(memberships[-1]["description"])

# Function to merge PDFs
def merge_pdfs(template_path, generated_path, output_path):
    with fitz.open(template_path) as template_pdf:
        output_pdf = fitz.open()
        for page_num in range(2):  # Add first 2 pages from template
            output_pdf.insert_pdf(template_pdf, from_page=page_num, to_page=page_num)
        with fitz.open(generated_path) as generated_pdf:
            output_pdf.insert_pdf(generated_pdf)
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

        pdf.set_fill_color(230, 230, 250)
        pdf.set_font("DejaVu", "B", 14)
        pdf.cell(0, 10, "Lifestyle Recommendations", new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
        pdf.ln(5)
        pdf.set_font("DejaVu", "", 12)
        for recommendation in lifestyle_recommendations:
            pdf.multi_cell(0, 8, f"• {recommendation}")
            pdf.ln(2)

        pdf.output(generated_pdf_path)
        merge_pdfs(template_pdf_path, generated_pdf_path, output_pdf_path)

        return output_pdf_path
    except Exception as e:
        st.error(f"Error generating PDF: {e}")
        return None

# Button to generate PDF
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
