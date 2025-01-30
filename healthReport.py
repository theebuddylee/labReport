import streamlit as st
from fpdf import FPDF
import fitz  # PyMuPDF
from PIL import Image
import json
import os
from datetime import datetime
import pytz
from github import Github

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
        .stMultiSelect option:hover {
            background-color: #06B6D4;
            color: #fff;
        }
    </style>
    """,
    unsafe_allow_html=True
)

#Control Session State variables
if "current_plan_tests" not in st.session_state:
    st.session_state.current_plan_tests = []
if "current_plan_medications" not in st.session_state:
    st.session_state.current_plan_medications = []
if "current_plan_supplements" not in st.session_state:
    st.session_state.current_plan_supplements = []

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
        "email": "Amber@1stoptimal.com",
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

# Membership data with updated descriptions, indications, and monthly prices
memberships = [
    {"name": "Coaching Partnership",
     "description": "Take control of your wellness with personalized hormone care and weight loss designed specifically to easily integrate into your coach's training and nutrition plan. This program includes everything you need for balanced health: comprehensive lab testing, tailored treatments, and expert medical oversight through initial and follow-up visits. With shipping, supplies, and lab interpretations all included, achieving an optimal program has never been easier or more convenient.",
     "indication": "1st Optimal’s Coaching Partnership Program makes it easy to integrate personalized hormone care and weight loss solutions into your training and nutrition plan, with seamless support through our user-friendly patient portal app.",
     "price": "Starting at 129/month"},
    {"name": "Peptide, Sex and Hair Care Membership",
     "description": "1st Optimal’s Peptide, Sex and Hair Care Membership, offers a personalized approach to enhancing vitality, longevity, and overall wellness. By integrating cutting-edge peptide treatments with expert asynchronous medical oversight and a user-friendly patient portal, we make optimizing your health simple and convenient. With tailored care plans for gut health, sexual wellness, hair care and much more. Shipping and supplies included.",
     "indication": "Unlock your body's full potential with cutting-edge peptide, sex, and hair care therapies designed to enhance vitality and performance effortlessly.",
     "price": "99/six months"},
    {"name": "Guided Hormone Care Membership",
     "description": "1st Optimal’s Guided Hormone Care program provides personalized treatments for hormonal balance, seamlessly integrated into your lifestyle with guided medical oversight and convenient telemedicine visits through our intuitive patient portal app. With comprehensive lab testing, asynchronous care, and all shipping and supplies included, managing your health has never been easier.",
     "indication": "Hormone care tailored to your lab results for hormonal balance.",
     "price": "99/month"},
    {"name": "Weight Loss Care Membership",
     "description": "Achieve sustainable weight loss with access to effective GLP-1 agonist treatments, GLP-1 supporting supplements, and comprehensive care. This membership includes personalized hormone treatments, lab testing, medical consultations, and all supplies, with shipping fees covered, offering a holistic approach to weight loss and wellness tailored to your needs.",
     "indication": "Targeted for individuals aiming for sustainable weight loss.",
     "price": "139/month"},
    {"name": "Men's Hormone Care Membership",
     "description": "Choose 1: Testosterone Cypionate or Enclomiphine",
     "indication": "Men's enhanced hormone care with choice of specific treatments for personalized hormone balance. This includes shipping, supplies, lab interpretations, medical visits, Testosterone Treatment, lab reviews, and your initial follow-up labs.",
     "price": "159/month"},
    {"name": "Women's Hormone Care Membership",
     "description": "Take control of your wellness with personalized hormone care designed specifically for women. This program includes everything you need for balanced health: comprehensive lab testing, tailored treatments like testosterone replacement, shipping fees covered, and expert medical oversight through initial and follow-up visits. With shipping, supplies, and lab interpretations all included, achieving optimal hormone balance has never been easier or more convenient.",
     "indication": "Women's enhanced hormone care with choice of specific treatments for personalized hormone balance. This includes shipping, supplies, lab interpretations, medical visits, lab reviews, Testosterone replacement, and your initial follow-up labs.",
     "price": "119/month"},
     {"name": "Men's TRT & Weight Loss Membership",
      "description": "The Men’s Weight Loss & Hormone Care Membership is designed to support sustainable weight loss while optimizing hormone health for peak performance and vitality. This comprehensive plan combines guided medical oversight with advanced hormone optimization and metabolic care. Members benefit from personalized treatment plans, telehealth consultations, and ongoing coaching to ensure consistent progress and lasting results.\n\nThis membership includes guided medical oversight fees, unlimited asynchronous care, lab and a free follow-up lab panel and interpretation of results, access to ongoing coaching, and our patient portal app. Exclusive member perks include premium member pricing (Average 40% less than MSRP), priority booking, hassle-free prescription refills, and complimentary e-books focused on weight loss and hormone health. Additional benefits include free shipping, free medical supplies, follow-up lab work, and testosterone or test-boost therapy when clinically indicated, all with no hidden fees.",
      "indication": "Ideal for men seeking to improve body composition, boost energy levels, and achieve hormone balance while ensuring long-term weight management. This membership is suitable for individuals experiencing symptoms related to low testosterone, metabolic imbalances, or difficulties with sustainable weight loss. Regular lab testing, comprehensive coaching, and personalized treatment adjustments ensure a safe, effective, and results-driven approach to overall health and performance enhancement.",
      "price": "169/month"},
     {"name": "Women's TRT & Weight Loss Membership",
      "description": "The Women’s Weight Loss & Hormone Care Membership is a holistic plan designed to promote healthy weight loss and hormone balance. This membership includes personalized treatment plans, guided medical oversight, and continuous support to help members achieve their health goals with confidence and ease.\n\nMembers receive telehealth medical consultations with no additional fees, unlimited asynchronous care, lab interpretations and a follow-up lab panel for hormone care and a follow-up lab panel for weight loss, ongoing coaching, and access to the patient portal app for comprehensive care. Exclusive benefits include premium member pricing, priority booking, hassle-free prescription refills, and complimentary e-books focused on weight loss and hormone health. The membership also includes free shipping, free medical supplies, follow-up lab work, and test-boosting or replacement therapy if clinically necessary, with no hidden fees.",
      "indication": "Ideal for women seeking to improve weight management, boost energy, and achieve balanced hormone levels for optimal health and vitality. This membership is tailored for women experiencing symptoms such as fatigue, difficulty losing weight, or hormone-related imbalances. With ongoing medical oversight, personalized coaching, and comprehensive lab reviews, this program ensures a safe, effective, and personalized approach to weight loss and hormone care.",
      "price": "149/month"}
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
     "indication": "Free and Total Testosterone, Estradiol, Testosterone, PSA, CBC, Metabolic Panel."},
    {"name": "Female Basic Hormone Health Panel",
     "description": "Testosterone,Estradiol, Standard,Sex Hormone Binding Globulin (SHBG), Dehydroepiandrosterone Sulfate (DHEA-S), Progesterone, Luteinizing Hormone (LH), Follicle-Stimulating Hormone (FSH), TSH, Lipid Panel, Complete Blood Count (with Differential), Metabolic Panel, HbA1c",
     "indication": "Get a clear snapshot of your essential hormone levels to uncover hidden imbalances impacting your energy, performance, and overall health."},
    {"name": "Female Hormone Health Panel",
     "description": "Take control of your hormonal health with our comprehensive Women's Hormone Panel. This test evaluates key hormones that influence energy, mood, menstrual cycles, and overall well-being. Gain insights into imbalances affecting fertility, PMS, or irregular cycles and start your journey toward optimal health today!",
     "indication": "Total Testosterone*, Free Testosterone*, Estradiol, Standard, SHBG, DHEA-S, Progesterone, LH, FSH, TSH, Free T3, Free T4, IGF-1, Lipid Panel, Ferritin, Iron, CBC, Metabolic Panel, HbA1c, Fasting Insulin, Vitamin D, GGT."},
    {"name": "Female Comprehensive Hormone Health Panel",
     "description": "Take control of your hormonal health with our comprehensive Women's Hormone Panel. This test evaluates key hormones that influence energy, mood, menstrual cycles, and overall well-being.",
     "indication": "Total Testosterone (LC/MS) [uncapped], Free Testosterone (Equilibrium Ultrafiltration) [uncapped], Estradiol (LC/MS), SHBG, Progesterone, Prolactin, Cortisol, LH, FSH, DHEA-S, TSH, Free T3, Free T4, IGF-1, Lipid Panel, ApoB, Lipoprotein (a), Ferritin, HbA1c, CBC, Metabolic Panel, Fasting Insulin, GGT, Vitamin D, Iron Panel, hsCRP."},
    {"name": "Female Hormone Treatment Follow-up Panel",
     "description": "FSH & LH\nHemoglobin A1c\nCBC with Differential/Platelet\nProgesterone\nTestosterone\nEstradiol\nProlactin\nTSH\nComprehensive Metabolic Panel (14)\nSex Hormone Binding Globulin\nLipid Panel",
     "indication": "This lab panel is designed to monitor key hormone and metabolic markers critical to female health. It provides insights into reproductive hormones, metabolic function, and overall health optimization."},
    {"name": "GI-MAP® + Zonulin",
     "description": "The GI-MAP® (Gastrointestinal Microbial Assay Plus) + Zonulin test is a comprehensive stool analysis designed to provide detailed insights into your gut health. It evaluates the presence of key bacteria, viruses, parasites, and fungi in your gastrointestinal system while also measuring levels of zonulin, a marker for intestinal permeability ('leaky gut').",
     "indication": "This advanced test helps uncover imbalances, inflammation, and disruptions in gut function that may contribute to digestive issues, immune challenges, and systemic health concerns. Ideal for individuals seeking personalized guidance for optimizing gut health and overall wellness."},
    {"name": "GI-MAP® (GI Microbial Assay Plus)",
     "description": "The GI-MAP® is a state-of-the-art stool analysis test that provides a detailed assessment of your gut microbiome. It identifies bacteria, viruses, parasites, fungi, and other pathogens that may be impacting your digestive health. This test also evaluates markers of inflammation, digestion, and immune function, offering valuable insights into overall gut health.",
     "indication": "Whether you're addressing digestive discomfort, chronic health issues, or optimizing wellness, the GI-MAP® delivers actionable data to create personalized strategies for improving gut function and systemic health."},
    {"name": "Women's Weight Loss Follow-up Lab Panel",
     "description": "The Women’s Weight Loss Follow-Up Lab Panel is a comprehensive blood test designed to monitor key biomarkers approximately 3 months into your weight loss program. As part of your weight loss membership, this panel provides valuable insights into your metabolic health, hormone levels, cardiovascular function, and overall progress, ensuring that your treatment plan remains tailored to your needs. Regular follow-up testing helps track improvements, identify potential concerns, and adjust your strategy for sustainable and long-lasting results.",
     "indication": "The Women’s Weight Loss Follow-Up Lab Panel is recommended for women 3 months into their weight loss journey to assess overall progress and optimize their treatment plan. This panel evaluates key markers, including CBC with Differential/Platelet to monitor blood health, Comprehensive Metabolic Panel to assess metabolic function, Hemoglobin A1c to track long-term glucose control, Insulin to measure insulin sensitivity, Lipid Panel to evaluate cardiovascular health, DHEA to assess adrenal function and hormone balance, and Thyroid Panel with TSH to ensure proper thyroid function. The lab draw fee is included for convenience."},
    {"name": "Men's Weight Loss Follow-up Lab Panel",
     "description": "The Men’s Weight Loss Follow-Up Lab Panel is a comprehensive blood test designed to monitor key biomarkers at the 3-month mark of your weight loss journey. Included as part of your weight loss membership, this panel provides crucial insights into your metabolic health, hormone balance, cardiovascular risk, and overall progress to ensure your treatment plan is optimized for long-term success. Regular follow-up testing helps track improvements, detect potential issues early, and adjust interventions for sustained fat loss and overall wellness.",
     "indication": "The Men’s Weight Loss Follow-Up Lab Panel is designed for men approximately 3 months into their weight loss program to track progress, optimize treatment, and ensure long-term success. This panel evaluates key markers, including CBC with Differential/Platelet to monitor blood health, Comprehensive Metabolic Panel to assess metabolic function, Hemoglobin A1c to track long-term glucose control, Testosterone to monitor hormone levels, Insulin to measure insulin sensitivity, Lipid Panel to evaluate cardiovascular health, and Thyroid Panel with TSH to assess thyroid function, with a draw fee included for convenience. Regular monitoring of these markers helps ensure a personalized, safe, and sustainable weight loss journey."}
]

# Medications
medications = [
    {"name": "Anastrozole",
     "description": "A medication used to manage estrogen levels in men undergoing testosterone replacement therapy (TRT). It works as an aromatase inhibitor, blocking the conversion of testosterone to estrogen, thereby maintaining optimal hormonal balance.",
     "indication": "Designed to maintain hormonal balance by managing estrogen levels. By reducing excess estrogen, Anastrozole helps improve energy, mood, and muscle definition while minimizing side effects like water retention or fatigue."},
    {"name": "BPC-157",
     "description": "1st Optimal’s BPC-157 Therapy offers cutting-edge treatment designed to support healing, recovery, and overall wellness.",
     "indication": "BPC-157 therapy promotes tissue repair, reduces inflammation, and enhances recovery from injuries or physical strain."},
    {"name": "DHEA",
     "description": "A hormone produced by the adrenal glands. It serves as a precursor to sex hormones like testosterone and estrogen and counterbalances cortisol, the stress hormone.",
     "indication": "Restores hormonal balance, boosts energy, mood, and sexual health. Enhance stress resilience, immunity, and overall well-being, an essential for longevity and performance optimization."},
    {"name": "Enanthate",
     "description": "Enanthate is a long-acting ester of testosterone commonly used in hormone replacement therapy (HRT) for men with low testosterone levels. It supports the maintenance of normal male physiological functions, including muscle mass, energy levels, libido, and mood. By providing a steady release of testosterone, enanthate helps restore hormonal balance, improving overall vitality and well-being.",
     "indication": "This treatment is typically administered via intramuscular injection and is tailored to individual needs under the supervision of a healthcare provider."},
    {"name": "Enclomiphene",
     "description": "A selective estrogen receptor modulator (SERM) used to increase testosterone production in men by stimulating the natural production of luteinizing hormone (LH) and follicle-stimulating hormone (FSH).",
     "indication": "A powerful testosterone booster that enhances natural production while supporting fertility. Unlike traditional options, Enclomiphene helps maintain testicular function and sperm count, ensuring optimized hormone levels without compromising reproductive health."},
    {"name": "Estrogen Replacement",
     "description": "Estrogen Therapies offer a tailored approach to supporting hormonal balance, enhancing vitality, and improving overall well-being.",
     "indication": "Estrogen therapy helps alleviate symptoms of hormonal imbalances and promotes optimal health for a better quality of life."},
    {"name": "Ezetimibe",
     "description": "Ezetimibe is a cholesterol-lowering medication that significantly reduces LDL-C while boosting HDL-C, offering additional protective benefits for heart health, non-alcoholic fatty liver disease, and stroke prevention. It also helps lower inflammation by reducing CRP levels, supporting overall cardiovascular wellness.",
     "indication": "Lowers bad cholesterol (LDL-C), raises good cholesterol (HDL-C), and supports heart and liver health while reducing inflammation."},
    {"name": "GHK-Cu Peptide Treatment",
     "description": "GHK-Cu Peptide is a powerful tripeptide bonded with copper ions, known for its ability to stimulate collagen production, support tissue repair, and combat signs of aging. Backed by decades of scientific research, GHK-Cu is safe for all skin types and a key component in anti-aging and regenerative treatments.",
     "indication": "Clinically researched, it improves skin elasticity, reduces wrinkles, balances pigmentation, and promotes hair follicle repair for thicker, healthier hair. Additionally, it accelerates wound healing, reduces inflammation, and strengthens antioxidant defenses, making it ideal for post-procedure recovery and calming irritated skin."},
    {"name": "Glutathione",
     "description": "Glutathione is a powerful antioxidant naturally produced in the body that plays a crucial role in detoxification, immune function, and cellular repair. It neutralizes harmful free radicals, reduces oxidative stress, and supports liver health, making it essential for overall wellness and anti-aging.",
     "indication": "Glutathione helps brighten skin tone, reduce inflammation, and enhance recovery from physical stress. Widely studied for its benefits, it is a cornerstone of cellular defense and optimal health."},
    {"name": "Hexarelin",
     "description": "Hexarelin is a peptide designed to stimulate the release of growth hormone, promoting muscle growth, fat reduction, and faster recovery. With its potent regenerative effects, Hexarelin is a versatile peptide for those seeking improved physical performance and resilience.",
     "indication": "Hexarelin strengthens connective tissues, supports joint health, and may improve cardiovascular function by promoting cardiac repair and protection. Known for its ability to enhance strength and energy, Hexarelin is commonly used for anti-aging, athletic performance, and injury recovery."},
    {"name": "Ketamine",
     "description": "1st Optimal’s Ketamine Therapy provides innovative treatment designed to support mental health and enhance overall well-being.",
     "indication": "Ketamine therapy offers a safe and effective way to address mood disorders, reduce stress, and promote emotional resilience."},
    {"name": "Levothyroxin",
     "description": "A synthetic form of thyroid hormone used to treat hypothyroidism. It helps restore proper metabolism, energy levels, and overall thyroid function.",
     "indication": "Boost energy, metabolism, and overall wellness with Levothyroxine—the gold standard in thyroid hormone replacement therapy."},
    {"name": "Metformin",
     "description": "Metformin is a widely used oral medication primarily prescribed for managing type 2 diabetes. It works by improving insulin sensitivity, reducing glucose production in the liver, and enhancing glucose uptake by the body’s cells, effectively lowering blood sugar levels.",
     "indication": "Metformin has been studied for its potential benefits in weight management, cardiovascular health, and even anti-aging applications. Its long-standing safety profile and effectiveness make it a cornerstone treatment for metabolic health under the guidance of a healthcare provider."},
    {"name": "Nandrlone Decanoate",
     "description": "Nandrolone Decanoate Therapy provides an advanced approach to joint recovery and enhanced well-being during your TRT phase.",
     "indication": "Nandrolone Decanoate therapy helps promote joint healing, alleviate discomfort from chronic inflammation, and enhance recovery from physical strain or injury. It works synergistically with testosterone replacement therapy to improve mobility, reduce pain, and support long-term joint health."},
    {"name": "Oxandrolone",
     "description": "Oxandrolone Therapy offers a powerful solution for enhancing recovery, strength, and lean muscle preservation during your TRT journey. Delivered with guided medical oversight, convenient telemedicine visits, and streamlined access through our patient portal app, this therapy is tailored for individuals seeking optimal performance and resilience.",
     "indication": "Oxandrolone therapy is known for its ability to promote tissue repair, increase strength, and preserve lean muscle mass, even during caloric deficits or recovery phases. Its mild profile and targeted benefits make it an ideal addition to testosterone replacement therapy, helping you recover faster, maintain muscle integrity."},
    {"name": "Pregnenolone",
     "description": "Pregnenolone Therapy offers a natural approach to supporting cognitive function, hormonal balance, and overall well-being.",
     "indication": "Pregnenolone therapy helps improve memory, reduce stress, and promote hormonal harmony for optimal health."},
    {"name": "Pregnyl",
     "description": "Pregnyl Therapy provides a targeted solution to support hormonal balance, enhance reproductive health, and improve overall vitality.",
     "indication": "Pregnyl therapy helps stimulate hormone production and optimize your health with ease and convenience."},
    {"name": "Progesterone",
     "description": "Progesterone Therapy provides a personalized solution to support hormonal balance, improve mood, and enhance overall well-being.",
     "indication": "Progesterone therapy helps regulate cycles, reduce stress, and promote optimal hormonal health."},
    {"name": "Retatrutide",
     "description": "A next-generation multi-receptor agonist used in clinical trials for weight management and metabolic improvements.",
     "indication": "The next-generation triple-action peptide therapy. By targeting GLP-1, GIP, and glucagon receptors, Retatrutide supports enhanced appetite control, improved metabolic health, and sustainable fat loss."},
    {"name": "Semaglutide",
     "description": "A GLP-1 receptor agonist used for weight loss and blood sugar management.",
     "indication": "The proven GLP-1 receptor agonist. Backed by science, Semaglutide enhances appetite control, stabilizes blood sugar, and promotes sustainable fat loss."},
    {"name": "Sermorelin",
     "description": "A synthetic peptide that stimulates the natural release of growth hormone from the pituitary gland.",
     "indication": "Boost your growth hormone levels naturally with Sermorelin, a peptide therapy designed to enhance fat loss, improve muscle tone, and support recovery."},
    {"name": "Tadalafil",
     "description": "A long-acting PDE5 inhibitor used to treat erectile dysfunction and improve urinary symptoms associated with benign prostatic hyperplasia (BPH).",
     "indication": "Long-lasting support for improved performance and blood flow, helping you feel and perform at your best."},
    {"name": "TB-400",
     "description": "1st Optimal’s TB-400 Therapy provides advanced treatment designed to enhance recovery, promote healing, and support overall physical performance.",
     "indication": "TB-400 therapy helps reduce inflammation, accelerate tissue repair, and improve endurance, making it an ideal choice for those seeking optimal recovery and resilience."},
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
     "indication": "The dual-action GLP-1 and GIP receptor agonist. Tirzepatide targets multiple pathways to enhance appetite control, improve insulin sensitivity, and promote effective fat loss."},
    {"name": "Vasoactive Intestinal Peptide",
     "description": "Vasoactive Intestinal Peptide (VIP) is a powerful neuropeptide that plays a key role in regulating inflammation, immune response, and vascular health. VIP therapy is commonly used to support optimal lung function, improve circulation, and enhance cognitive performance. It may also benefit individuals with chronic inflammatory conditions by helping to restore balance and improve overall well-being.",
     "indication": "Whether you're seeking support for immune regulation or optimizing recovery, VIP therapy offers a targeted approach to help you feel your best."}
]

# Supplements
supplements = [
    {"name": "Aged Garlic Extract Formula",
     "description": "Kyolic Aged Garlic Extract Formula 104 supports cardiovascular health by helping to maintain healthy cholesterol levels and overall heart function. This formula combines aged garlic extract with naturally sourced lecithin for a potent, odorless supplement designed for daily wellness.",
     "indication": "Supports healthy cholesterol levels and promotes overall heart health with the power of aged garlic extract and lecithin."},
    {"name": "Berberine",
     "description": "A natural compound derived from plants that supports blood sugar regulation and metabolic health.",
     "indication": "Nature’s powerful metabolic optimizer. Known for its ability to support healthy blood sugar levels, improve insulin sensitivity, and promote fat metabolism."},
    {"name": "Cholesterol Complete",
     "description": "Cholesterol Complete by Biospec Nutritionals features a blend of red yeast rice, guggulipid, hawthorn, and policosanol to support healthy cholesterol levels. This comprehensive formula leverages traditional heart-healthy ingredients to promote favorable blood lipid profiles.",
     "indication": "Ideal for individuals looking to manage cholesterol levels and maintain cardiovascular health through a natural, evidence-based approach."},
    {"name": "Cholesterol Support",
     "description": "Cholesterol Support by AnazaoHealth combines a phytosterol complex with policosanol and artichoke leaf extract to help maintain healthy cholesterol levels. Phytosterols reduce cholesterol absorption in the intestines, while policosanol and artichoke extract support cholesterol metabolism and synthesis regulation.",
     "indication": "Designed for individuals aiming to manage cholesterol levels and support cardiovascular health naturally. Recommended for those seeking to maintain healthy blood lipid profiles."},
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
    {"name": "Glucosamine Chondroitin Sulfate",
     "description": "Glucosamine Chondroitin combines glucosamine sulfate and clinically trialed Csbioactive® chondroitin sulfate, to promote healthy joint function.",
     "indication": "Glucosamine and chondroitin are the building blocks of cartilage and may help promote normal cartilage development. They may also help support healthy aging."},
    {"name": "Homocysteine Nutrients",
     "description": "Homocysteine Nutrients is a dietary supplement designed to support healthy homocysteine metabolism and optimal methylation. It combines bioactive B vitamins, such as L-methylfolate and methylcobalamin, with trimethylglycine (TMG) to promote cardiovascular and neurological health. This formula helps convert homocysteine to methionine, maintaining normal levels for improved function.",
     "indication": "High Homocysteine blood plasma levels, also supports cardiovascular and cognitive health by promoting the efficient metabolism of homocysteine, a key factor in reducing health risks."},
    {"name": "Homocysteine Supreme",
     "description": "Formulated to support the efficient metabolism of homocysteine, an amino acid linked to cardiovascular and neurological health. It combines bioactive forms of folate (5-methyltetrahydrofolate), vitamin B6 (pyridoxal-5’-phosphate), vitamin B12 (methylcobalamin), and other synergistic nutrients to promote optimal homocysteine pathways.",
     "indication": "By maintaining healthy homocysteine levels, this supplement aids in the production of essential compounds like taurine, cysteine, norepinephrine, and dopamine, which are vital for detoxification, immune function, joint and cartilage health, and overall brain and cardiovascular wellness."},
    {"name": "Joint Health Bundle",
      "description": "A supplement pack that supports joint health and mobility, featuring ingredients like glucosamine, chondroitin, and MSM.",
      "indication": "Relieve joint pain and support musculoskeletal health with our comprehensive Joint Support Bundle."},
    {"name": "JuJitsu Joint Health Bundle",
     "description": "The 1st Optimal Jiu-Jitsu Joint Health Bundle combines Glucosamine Chondroitin, Curcumin Phytosome, and Boswellia Extract to support joint strength, flexibility, and recovery. This powerful trio helps protect cartilage, reduce inflammation, and improve mobility—perfect for BJJ athletes looking to stay resilient during intense training sessions and recover faster.",
     "indication": "Recommended for BJJ and martial arts athletes experiencing joint discomfort, stiffness, or inflammation, as well as active individuals recovering from joint injuries or seeking to maintain long-term joint health during high-impact training."},
    {"name": "L-Theanine",
     "description": "L-Theanine is a naturally occurring amino acid found in green and black tea leaves. It promotes relaxation without causing drowsiness, making it ideal for stress relief and mental focus. Known for its calming effects, it may also enhance cognitive performance, reduce anxiety, and improve sleep quality.",
     "indication": "Recommended for individuals seeking to reduce stress, enhance focus, or improve sleep patterns. It is particularly useful for managing everyday anxiety and promoting a sense of calm while maintaining alertness."},
    {"name": "Magnesium",
     "description": "An essential mineral that supports muscle function, energy production, nerve health, and sleep quality.",
     "indication": "Stress depletes magnesium levels, impairing relaxation, sleep, and muscle function. Magnesium helps regulate the nervous system, reduce cortisol, and promote a calm, balanced mood."},
    {"name": "Multi-Vitamin Premier",
     "description": "A high-quality multivitamin providing essential vitamins, minerals, and antioxidants.",
     "indication": "A high-quality multivitamin to fill nutritional gaps and support overall health and vitality."},
    {"name": "Nattovena 4,000 FU/cap",
     "description": "Nattovena is a potent dietary supplement containing 4,000 fibrinolytic units (FU) of nattokinase per capsule, designed to support cardiovascular health by promoting normal blood viscosity and aiding in the breakdown of excess fibrin. Derived from the traditional Japanese fermented soybean dish natto, nattokinase is a fibrin-dissolving enzyme that helps maintain healthy circulation.",
     "indication": "Used as a natural aid for managing 'thick blood,' or conditions associated with increased blood viscosity."},
    {"name": "Omega-3",
     "description": "A fatty acid supplement derived from fish oil, providing EPA and DHA for heart health, brain function, and anti-inflammatory support.",
     "indication": "Omega-3s help reduce systemic inflammation, protect cardiovascular health, and improve joint mobility."},
    {"name": "Psyllium Husk",
     "description": "Psyllium Husk is a natural, soluble fiber supplement that promotes healthy digestion, regularity, and supports heart health by helping to maintain healthy cholesterol levels.",
     "indication": "Promotes digestive health and regularity while supporting heart health with gentle, natural fiber."},
    {"name": "Selenium",
     "description": " Selenium is essential for thyroid function as it helps convert inactive thyroid hormone (T4) into its active form (T3) and protects the thyroid gland from oxidative damage through its role in antioxidant enzymes like glutathione peroxidase. A deficiency in selenium can impair thyroid hormone metabolism and increase the risk of thyroid disorders, including hypothyroidism and Hashimoto’s thyroiditis.",
     "indication": "Selenium is indicated for individuals seeking to support healthy immune function, protect normal cell activity from oxidative stress, and promote overall cardiovascular and cellular health."},
    {"name": "Thyroid Support Bundle",
     "description": "A comprehensive supplement package designed to support thyroid function.",
     "indication": "Optimize your thyroid function with our Thyroid Support Bundle, featuring Selenium, D3 Liquid, and more."},
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

# Function to write More Information Sections on first and last page onto merged PDF
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
            (f"{manager_phone}", 73, 8.84 * 72),
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
        email_text = f"{manager_email}"
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

# Section Generate Function
def add_section(title, items, data_source, pdf, show_price=False):
    if not items:
        return

    # Header for each section
    pdf.set_fill_color(6, 182, 212)
    pdf.set_text_color(242, 242, 242)
    pdf.set_font("Exo2", "B", 22)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)
    pdf.ln(5)

    # Content for each item
    pdf.set_text_color(115, 115, 115)
    for item in items:
        # Handle both strings and dictionaries
        if isinstance(item, dict):
            item_data = item
        else:
            item_data = next(
                (x for x in data_source if x['name'].strip().lower() == item.strip().lower()),
                None
            )

        if not item_data:
            #st.write(f"DEBUG: No match found for item '{item}' in section '{title}'.")
            continue

        # Render item content
        pdf.set_font("Exo2", "B", 20)
        pdf.cell(0, 8, f"{item_data['name']}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        pdf.set_font("Exo2", "BI", 16)
        pdf.cell(0, 6, "Description:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Exo2", "", 12)
        pdf.multi_cell(0, 6, f"{item_data.get('description', 'N/A')}")

        pdf.ln(3)
        pdf.set_font("Exo2", "BI", 16)
        pdf.cell(0, 6, "Indication:", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Exo2", "", 12)
        pdf.multi_cell(0, 6, f"{item_data.get('indication', 'No indication provided.')}")

        if show_price:
            pdf.ln(3)
            pdf.set_font("Exo2", "BI", 16)
            pdf.cell(0, 6, "Price:", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Exo2", "", 12)
            pdf.multi_cell(0, 6, f"{item_data.get('price', 'TBD')}")
        pdf.ln(5)

# PDF generation function
def generate_pdf(selected_membership, final_tests, final_medications, final_supplements):
    try:
        generated_pdf_path = "generated_content.pdf"
        merged_pdf_path = "final_treatment_plan.pdf"
        updated_pdf_path = "updated_treatment_plan.pdf"

        # Initialize PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # Add Exo 2 font
        pdf.add_font("Exo2", "", "Exo2-Regular.ttf")
        pdf.add_font("Exo2", "B", "Exo2-Bold.ttf")
        pdf.add_font("Exo2", "I", "Exo2-Italic.ttf")
        pdf.add_font("Exo2", "BI", "Exo2-BoldItalic.ttf")

        # Create Title
        pdf.set_text_color(6, 182, 212)
        pdf.set_font("Exo2", "B", 36)
        pdf.cell(0, 10, "1st Optimal Treatment Plan", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)

        # Add sections to the PDF
        add_section("Membership", selected_membership, memberships, pdf, show_price=True)
        add_section("Diagnostic Testing", final_tests, diagnostic_tests, pdf)
        add_section("Medications", final_medications, medications, pdf)
        add_section("Supplements", final_supplements, supplements, pdf)

        # Save PDF and merge
        pdf.output(generated_pdf_path)
        merge_pdfs(template_pdf_path, generated_pdf_path, merged_pdf_path)

        # Add additional information to the final PDF
        return overwrite_more_information(merged_pdf_path, updated_pdf_path, member_name, selected_manager)
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

# Membership dropdown
selected_membership = st.multiselect("Membership", [item['name'] for item in memberships], max_selections=1)

# Dropdowns for Tests, Medications, and Supplements
def add_custom_entry(category, base_items, session_state_key):
    # Display dropdown with all items (full dictionaries) plus "Other"
    selected_items = st.multiselect(
        f"Select {category}", [item['name'] for item in base_items] + ["Other"], max_selections=10
    )

    # Handle "Other" for adding custom entries
    if "Other" in selected_items:
        st.subheader(f"Add a Custom {category[:-1]}")
        custom_name = st.text_input(f"{category[:-1]} Name")
        custom_description = st.text_area(f"{category[:-1]} Description")
        custom_indication = st.text_area(f"{category[:-1]} Indication")
        if st.button(f"Add {category[:-1]}"):
            if custom_name and custom_description and custom_indication:
                st.success(f"Custom {category[:-1]} '{custom_name}' added!")
                st.session_state[session_state_key].append({
                    "name": custom_name,
                    "description": custom_description,
                    "indication": custom_indication,
                })
            else:
                st.error("Please fill all fields to add the custom entry.")

    # Combine selected predefined items and custom entries
    final_items = st.session_state[session_state_key] + [
        item for item in base_items if item['name'] in selected_items
    ]

    return final_items

final_tests = add_custom_entry("Tests", diagnostic_tests, "current_plan_tests")
final_medications = add_custom_entry("Medications", medications, "current_plan_medications")
final_supplements = add_custom_entry("Supplements", supplements, "current_plan_supplements")


# Debugging
#st.write("DEBUG: Final Tests:", final_tests)
#st.write("DEBUG: Final Medications:", final_medications)
#st.write("DEBUG: Final Supplements:", final_supplements)

# PDF Generation
if st.button("Generate PDF"):
    # Debugging: Display the selections
    #st.write("DEBUG: Selected Membership:", selected_membership)
    #st.write("DEBUG: Final Tests:", final_tests)
    #st.write("DEBUG: Final Medications:", final_medications)
    #st.write("DEBUG: Final Supplements:", final_supplements)

    # Attempt to generate the PDF
    pdf_path = generate_pdf(selected_membership, final_tests, final_medications, final_supplements)

    # Log analytics data to GitHub
    analytics_data = {
        "member_name": member_name,
        "manager": selected_manager,
        "membership": selected_membership,
        "tests": final_tests,
        "medications": final_medications,
        "supplements": final_supplements,
    }
    try:
        log_to_github(analytics_data)
        #st.success("Selections logged to GitHub Analytics successfully!")
    except Exception as e:
        st.error(f"Failed to log selections to Analytics: {e}")

    # Handle PDF generation result
    if pdf_path:
        st.success("PDF generated successfully!")
        with open(pdf_path, "rb") as pdf_file:
            st.download_button("Download Treatment Plan", data=pdf_file, file_name="1stOptimal_treatment_plan.pdf", mime="application/pdf")
    else:
        st.error("PDF generation failed.")
