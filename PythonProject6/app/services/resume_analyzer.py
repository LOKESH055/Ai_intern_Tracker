# app/services/resume_analyzer.py
import fitz  # PyMuPDF
import json
import re
from app.services.watsonx_client import get_watsonx_client


RESUME_ANALYSIS_PROMPT = """You are an expert ATS (Applicant Tracking System) analyst and career coach.

Analyze this resume against the target internship role and return a detailed JSON evaluation.

RESUME TEXT:
{resume_text}

TARGET ROLE / INTERNSHIP CONTEXT:
{job_context}

Return ONLY a valid JSON object in this exact format:
{{
  "ats_score": 72,
  "match_percentage": 65,
  "summary": "2-3 sentence overall assessment of the resume.",
  "strengths": [
    "Strength 1",
    "Strength 2",
    "Strength 3"
  ],
  "missing_skills": [
    "Skill 1 required by the role but missing from resume",
    "Skill 2"
  ],
  "missing_keywords": [
    "keyword1",
    "keyword2",
    "keyword3"
  ],
  "improvement_suggestions": [
    "Specific suggestion 1",
    "Specific suggestion 2",
    "Specific suggestion 3"
  ],
  "project_suggestions": [
    "Build a project that demonstrates X skill",
    "Create a portfolio piece showing Y"
  ],
  "formatting_suggestions": [
    "Formatting tip 1",
    "Formatting tip 2"
  ],
  "experience_level": "beginner",
  "top_matching_roles": [
    "Role 1 this resume is best suited for",
    "Role 2"
  ]
}}

Scoring guide:
- ats_score (0-100): How well the resume passes ATS filters (keywords, formatting, structure)
- match_percentage (0-100): How well this resume matches the target role specifically

Be specific and actionable. Reference actual content from the resume in your feedback."""


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF using PyMuPDF first.
    Falls back to OCR (Tesseract) if no text is found (image-based PDFs).
    """
    import fitz
    import re

    # ── Attempt 1: Direct text extraction ───────────────────
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if len(text) > 100:   # enough real text found
            return text
    except Exception:
        pass

    # ── Attempt 2: OCR fallback ──────────────────────────────
    try:
        import pytesseract
        from PIL import Image
        import io

        # Point to Tesseract executable on Windows
        pytesseract.pytesseract.tesseract_cmd = (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        )

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = ""

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Render page to image at 2x zoom for better OCR accuracy
            mat = fitz.Matrix(2, 2)
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))
            page_text = pytesseract.image_to_string(img)
            full_text += page_text + "\n"

        doc.close()
        full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()

        if not full_text:
            raise ValueError("OCR produced no text. Check if the PDF is readable.")

        return full_text

    except ImportError:
        raise Exception(
            "OCR libraries not installed. Run: pip install pytesseract pillow"
        )
    except Exception as e:
        raise Exception(f"Both text extraction and OCR failed: {str(e)}")

def analyze_resume(
    resume_text: str,
    job_context: str = ""
) -> dict:
    """
    Analyze resume using watsonx and return structured results.

    Args:
        resume_text: Extracted text from the resume PDF
        job_context: Description of target role/internships (optional)

    Returns:
        Dict with ATS score, gaps, suggestions etc.
    """
    client = get_watsonx_client()

    if not job_context:
        job_context = (
            "General Data Science / Software Engineering internship. "
            "Common requirements: Python, SQL, machine learning basics, "
            "data analysis, communication skills."
        )

    # Truncate resume text if too long (model context limit)
    max_chars = 3000
    if len(resume_text) > max_chars:
        resume_text = resume_text[:max_chars] + "\n... [truncated for analysis]"

    prompt = RESUME_ANALYSIS_PROMPT.format(
        resume_text=resume_text,
        job_context=job_context
    )

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        return _parse_analysis_response(response)
    except Exception as e:
        raise Exception(f"Resume analysis failed: {str(e)}")


def _parse_analysis_response(response: str) -> dict:
    """Parse JSON response from watsonx."""
    # Extract JSON object
    json_match = re.search(r'\{.*\}', response, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON found in analysis response")

    json_str = json_match.group(0)
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)

    return json.loads(json_str)


def build_job_context_from_listings(jobs: list[dict]) -> str:
    """Build a job context string from fetched internship listings."""
    if not jobs:
        return ""

    lines = ["Target internship roles:"]
    for job in jobs[:5]:  # use top 5 for context
        skills = ", ".join(job.get("required_skills", [])[:5])
        lines.append(
            f"- {job['title']} at {job['company']}"
            + (f" | Skills: {skills}" if skills else "")
        )
    return "\n".join(lines)