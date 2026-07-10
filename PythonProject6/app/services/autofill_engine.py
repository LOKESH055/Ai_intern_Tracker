# app/services/autofill_engine.py
import json
import re
from app.services.watsonx_client import get_watsonx_client
from app.services.cloudant_client import get_user_profile


COVER_LETTER_PROMPT = """You are an expert career coach writing a cover letter.

CANDIDATE PROFILE:
{profile}

TARGET JOB:
Title: {job_title}
Company: {company}
Location: {location}
Job Description: {job_description}

Write a professional, personalized cover letter for this internship application.

Requirements:
- 3 paragraphs, max 250 words
- Opening: mention the specific role and company, show enthusiasm
- Middle: connect candidate's skills and experience to the job requirements
- Closing: call to action, availability, contact info
- Tone: professional but genuine, not generic
- Use the candidate's actual skills and background

Return ONLY the cover letter text, no extra explanation."""


AUTOFILL_PROMPT = """Extract application form field values for this candidate applying to this job.

CANDIDATE PROFILE:
{profile}

TARGET JOB:
Title: {job_title}
Company: {company}

Return ONLY valid JSON:
{{
  "full_name": "",
  "email": "",
  "phone": "",
  "linkedin_url": "",
  "github_url": "",
  "university": "",
  "degree": "",
  "graduation_year": "",
  "cgpa": "",
  "years_of_experience": "0",
  "skills_summary": "comma separated top 5 skills relevant to this role",
  "why_this_company": "2 sentences specific to this company",
  "availability": "",
  "expected_stipend": "",
  "cover_letter_summary": "1 sentence summary of cover letter"
}}"""


def generate_cover_letter(job: dict, profile: dict = None) -> str:
    """Generate a personalized cover letter for a job."""
    client = get_watsonx_client()

    if not profile:
        profile = get_user_profile()

    if not profile:
        profile = {
            "name": "Candidate",
            "skills": ["Python", "Data Analysis"],
            "education": "Bachelor's",
            "about_me": "A motivated student seeking internship opportunities."
        }

    profile_text = _format_profile_for_prompt(profile)

    prompt = COVER_LETTER_PROMPT.format(
        profile=profile_text,
        job_title=job.get("title", "Internship"),
        company=job.get("company", "the company"),
        location=job.get("location", ""),
        job_description=job.get("description", "Not provided")[:500]
    )

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        return response.strip()
    except Exception as e:
        raise Exception(f"Cover letter generation failed: {str(e)}")


def generate_autofill_data(job: dict, profile: dict = None) -> dict:
    """Generate pre-filled application form data."""
    client = get_watsonx_client()

    if not profile:
        profile = get_user_profile()

    profile_text = _format_profile_for_prompt(profile)

    prompt = AUTOFILL_PROMPT.format(
        profile=profile_text,
        job_title=job.get("title", ""),
        company=job.get("company", "")
    )

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = re.sub(r',\s*}', '}', json_match.group(0))
            return json.loads(json_str)
        return {}
    except Exception as e:
        raise Exception(f"Auto-fill generation failed: {str(e)}")


def _format_profile_for_prompt(profile: dict) -> str:
    skills = profile.get("skills", [])
    if isinstance(skills, list):
        skills_str = ", ".join(skills[:15])
    else:
        skills_str = str(skills)

    return f"""
Name: {profile.get('name', 'Not provided')}
Email: {profile.get('email', 'Not provided')}
Phone: {profile.get('phone', 'Not provided')}
LinkedIn: {profile.get('linkedin', 'Not provided')}
GitHub: {profile.get('github', 'Not provided')}
Education: {profile.get('education', 'Not provided')}
College: {profile.get('college', 'Not provided')}
Degree: {profile.get('degree', 'Not provided')}
Graduation Year: {profile.get('graduation_year', 'Not provided')}
CGPA: {profile.get('cgpa', 'Not provided')}
Skills: {skills_str}
Experience Level: {profile.get('experience_level', 'Beginner')}
Preferred Roles: {', '.join(profile.get('preferred_roles', []))}
Location Preference: {profile.get('location_pref', 'Any')}
Availability: {profile.get('availability', 'Immediate')}
About Me: {profile.get('about_me', 'Not provided')}
""".strip()