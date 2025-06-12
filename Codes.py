
#!/usr/bin/env python
# coding: utf-8

import streamlit as st
import os
import PyPDF2 as pdf
import docx2txt
from dotenv import load_dotenv
import json
import time
import re
import pandas as pd
from streamlit_extras.add_vertical_space import add_vertical_space

try:
    import google.generativeai as genai
except ModuleNotFoundError:
    st.error("Module 'google-generativeai' not found. Please install it using 'pip install google-generativeai'")
    st.stop()

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    st.error("Google API key not found. Please add it as 'GOOGLE_API_KEY' in your .env file.")
    st.stop()

# Configure the Gemini API
genai.configure(api_key=API_KEY)
MODEL_NAME = "models/gemini-1.5-flash"

# Background style
st.markdown("""
    <style>
    .stApp {
        background-color: #f0f0f0;
    }
    .main-title {
        background-color: #2196f3;
        color: white;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        color: white;
    }
    .info-box {
        background-color: #e3f2fd;
        border: 1px solid #2196f3;
        padding:10px;
        border-left:5px solid #2196f3;
        border-radius:5px;
        margin-bottom:10px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title"><h2>📄 ATS Resume Evaluator</h2></div>', unsafe_allow_html=True)

st.markdown("Use AI to evaluate resumes against job descriptions and extract useful profile information.")

# Functions
def get_gemini_response(input_text):
    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        response = model.generate_content(input_text)
        return response.text
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return json.dumps({"JD Match":"N/A", "MissingKeywords":[], "Profile Summary":"Error", "Candidate Name":"", "Role":"", "Current Company":"", "Duration":"", "Overall Experience":"", "LinkedIn":""})

def input_resume_text(uploaded_file):
    if uploaded_file.name.endswith(".pdf"):
        reader = pdf.PdfReader(uploaded_file)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    elif uploaded_file.name.endswith(".docx"):
        return docx2txt.process(uploaded_file)
    return ""

def extract_keywords_from_jd(jd_text):
    return list(set(re.findall(r'\b[a-zA-Z]{3,}\b', jd_text.lower())))

# UI Elements
st.header("Job Description")
jd_input = st.text_area("Paste the Job Description")

st.header("Upload Resumes")
uploaded_files = st.file_uploader("Upload Resume PDFs or DOCX", type=["pdf", "docx"], accept_multiple_files=True)
linkedin_url = st.text_input("LinkedIn Profile URL (optional)")

input_prompt = """
Act like an ATS. Evaluate this resume against the JD.
Return JSON:
{{"JD Match":"%","MissingKeywords":[],"Profile Summary":"","Candidate Name":"","Role":"","Current Company":"","Duration":"","Overall Experience":"","LinkedIn":"{linkedin}"}}
Resume: {text}
Job Description: {jd}
LinkedIn: {linkedin}
"""

results_data = []

if st.button("🚀 Evaluate Resumes"):
    if not uploaded_files or not jd_input.strip():
        st.error("Please provide both JD and at least one resume.")
    else:
        progress = st.progress(0)
        for idx, uploaded_file in enumerate(uploaded_files):
            resume_text = input_resume_text(uploaded_file).lower()
            st.subheader(f"📎 Resume: `{uploaded_file.name}`")

            prompt = input_prompt.format(text=resume_text[:4000], jd=jd_input[:1000], linkedin=linkedin_url)
            response = get_gemini_response(prompt)
            try:
                response_json = json.loads(response)
            except json.JSONDecodeError:
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    response_json = json.loads(match.group())
                else:
                    st.error("Failed to parse JSON.")
                    continue

            jd_match = response_json.get("JD Match", "N/A")
            missing_keywords = response_json.get("MissingKeywords", [])
            profile_summary = response_json.get("Profile Summary", "")
            candidate_name = response_json.get("Candidate Name", "")
            role = response_json.get("Role", "")
            current_company = response_json.get("Current Company", "")
            duration = response_json.get("Duration", "")
            overall_experience = response_json.get("Overall Experience", "")
            linkedin = response_json.get("LinkedIn", "")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("🎯 JD Match", jd_match)
            with col2:
                st.metric("📉 Missing Keywords", str(len(missing_keywords)))

            st.markdown(f"""
                <div class='info-box'>
                <b>Name:</b> {candidate_name}<br>
                <b>Role:</b> {role}<br>
                <b>Company:</b> {current_company}<br>
                <b>Duration:</b> {duration}<br>
                <b>Experience:</b> {overall_experience}<br>
                <b>LinkedIn:</b> <a href="{linkedin}" target="_blank">{linkedin}</a>
                </div>
            """, unsafe_allow_html=True)

            st.info(f"**Profile Summary:** {profile_summary}")
            if missing_keywords:
                st.warning(f"Missing Keywords: {', '.join(missing_keywords)}")

            # Save data
            results_data.append({
                "Resume File": uploaded_file.name,
                "JD Match": jd_match,
                "Candidate Name": candidate_name,
                "Role": role,
                "Current Company": current_company,
                "Duration": duration,
                "Overall Experience": overall_experience,
                "LinkedIn": linkedin,
                "Missing Keywords": ", ".join(missing_keywords),
                "Profile Summary": profile_summary
            })

            progress.progress((idx + 1) / len(uploaded_files))

        if results_data:
            df = pd.DataFrame(results_data)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download CSV Report", data=csv, file_name="ats_report.csv", mime="text/csv")

        st.success("✅ Evaluation complete.")
        st.balloons()

add_vertical_space(2)
st.markdown("---")
st.caption("📄 Powered by Google Gemini | Styled with ❤️ using Streamlit")

