# app/components/profile_ui.py
import streamlit as st
from app.services.cloudant_client import save_user_profile, get_user_profile


SKILLS_LIST = [
    "Python", "SQL", "Machine Learning", "Deep Learning", "NLP",
    "Data Analysis", "TensorFlow", "PyTorch", "Scikit-learn", "Pandas",
    "NumPy", "Matplotlib", "Power BI", "Tableau", "Excel",
    "Java", "JavaScript", "React", "Node.js", "HTML/CSS",
    "C++", "C#", "Flutter", "Android", "iOS",
    "AWS", "Azure", "IBM Cloud", "Docker", "Kubernetes",
    "Git", "Linux", "REST APIs", "MongoDB", "PostgreSQL",
    "Communication", "Leadership", "Problem Solving", "Teamwork"
]

ROLE_OPTIONS = [
    "Data Science", "Machine Learning", "Software Engineering",
    "Web Development", "Android/iOS Development", "DevOps/Cloud",
    "Cybersecurity", "Data Analytics", "AI Research",
    "Product Management", "Marketing", "Finance", "UI/UX Design"
]

EDUCATION_OPTIONS = [
    "High School", "Diploma", "Bachelor's (1st Year)",
    "Bachelor's (2nd Year)", "Bachelor's (3rd Year)",
    "Bachelor's (Final Year)", "Master's", "PhD"
]

EXPERIENCE_OPTIONS = ["Beginner (No experience)", "Some projects",
                       "1 internship", "2+ internships", "Part-time work"]

LOCATION_OPTIONS = [
    "Any", "Remote Only", "India", "Bangalore", "Mumbai",
    "Delhi", "Hyderabad", "Chennai", "Pune", "USA", "UK", "Canada"
]


def render_profile_page():
    st.markdown("""
        <h2 style='color: #4A90D9;'>👤 My Profile</h2>
        <p style='color: #888;'>Your profile is used to personalize job rankings,
        send email alerts, and auto-fill applications.</p>
        <hr>
    """, unsafe_allow_html=True)

    # Load existing profile
    with st.spinner("Loading your profile..."):
        try:
            existing = get_user_profile()
        except Exception:
            existing = {}

    if existing:
        st.success("✅ Profile loaded from IBM Cloudant")
    else:
        st.info("👋 First time here? Fill in your profile to get personalized results.")

    st.markdown("---")

    # ── Personal Info ────────────────────────────────────────
    st.markdown("### 👤 Personal Information")
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input(
            "Full Name",
            value=existing.get("name", ""),
            placeholder="e.g. Naresh Kumar"
        )
        email = st.text_input(
            "Email Address (for job alerts)",
            value=existing.get("email", ""),
            placeholder="youremail@gmail.com"
        )

    with col2:
        phone = st.text_input(
            "Phone Number (optional)",
            value=existing.get("phone", ""),
            placeholder="+91 98765 43210"
        )
        linkedin = st.text_input(
            "LinkedIn URL (optional)",
            value=existing.get("linkedin", ""),
            placeholder="linkedin.com/in/yourname"
        )

    github = st.text_input(
        "GitHub URL (optional)",
        value=existing.get("github", ""),
        placeholder="github.com/yourusername"
    )

    st.markdown("---")

    # ── Education ────────────────────────────────────────────
    st.markdown("### 🎓 Education")
    col1, col2 = st.columns(2)

    with col1:
        education = st.selectbox(
            "Current Education Level",
            EDUCATION_OPTIONS,
            index=EDUCATION_OPTIONS.index(existing.get("education", "Bachelor's (Final Year)"))
            if existing.get("education") in EDUCATION_OPTIONS else 0
        )
        college = st.text_input(
            "College / University",
            value=existing.get("college", ""),
            placeholder="e.g. Anna University"
        )

    with col2:
        degree = st.text_input(
            "Degree / Major",
            value=existing.get("degree", ""),
            placeholder="e.g. B.Tech Computer Science"
        )
        graduation_year = st.selectbox(
            "Expected Graduation Year",
            [str(y) for y in range(2024, 2030)],
            index=0
        )

    cgpa = st.text_input(
        "CGPA / Percentage (optional)",
        value=existing.get("cgpa", ""),
        placeholder="e.g. 8.5 / 10 or 85%"
    )

    st.markdown("---")

    # ── Skills ───────────────────────────────────────────────
    st.markdown("### 🛠 Skills")

    existing_skills = existing.get("skills", [])
    selected_skills = st.multiselect(
        "Select your skills",
        options=SKILLS_LIST,
        default=[s for s in existing_skills if s in SKILLS_LIST],
        help="Select all skills you're comfortable with"
    )

    custom_skills = st.text_input(
        "Add custom skills (comma separated)",
        value=existing.get("custom_skills", ""),
        placeholder="e.g. LangChain, Streamlit, FastAPI"
    )

    experience_level = st.selectbox(
        "Experience Level",
        EXPERIENCE_OPTIONS,
        index=EXPERIENCE_OPTIONS.index(existing.get("experience_level", "Beginner (No experience)"))
        if existing.get("experience_level") in EXPERIENCE_OPTIONS else 0
    )

    st.markdown("---")

    # ── Job Preferences ──────────────────────────────────────
    st.markdown("### 🎯 Job Preferences")
    col1, col2 = st.columns(2)

    with col1:
        preferred_roles = st.multiselect(
            "Preferred Roles",
            options=ROLE_OPTIONS,
            default=[r for r in existing.get("preferred_roles", []) if r in ROLE_OPTIONS]
        )
        location_pref = st.selectbox(
            "Location Preference",
            LOCATION_OPTIONS,
            index=LOCATION_OPTIONS.index(existing.get("location_pref", "Any"))
            if existing.get("location_pref") in LOCATION_OPTIONS else 0
        )

    with col2:
        stipend_expectation = st.text_input(
            "Minimum Stipend Expectation (optional)",
            value=existing.get("stipend_expectation", ""),
            placeholder="e.g. $20/hr or ₹15,000/month"
        )
        availability = st.selectbox(
            "Availability",
            ["Immediate", "1 month", "2 months", "3 months", "After graduation"],
            index=0
        )

    about_me = st.text_area(
        "About Me (used in cover letters)",
        value=existing.get("about_me", ""),
        placeholder="Write 2-3 sentences about yourself, your goals, and what you're looking for...",
        height=100
    )

    st.markdown("---")

    # ── ATS Score from Resume ────────────────────────────────
    if "resume_analysis" in st.session_state:
        ats = st.session_state["resume_analysis"].get("ats_score", 0)
        match = st.session_state["resume_analysis"].get("match_percentage", 0)
        st.markdown("### 📄 Resume Stats (from last analysis)")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ATS Score", f"{ats}/100")
        with col2:
            st.metric("Role Match", f"{match}%")

    # ── Save Button ──────────────────────────────────────────
    st.markdown("---")
    if st.button("💾 Save Profile", type="primary", use_container_width=True):
        if not name:
            st.error("Please enter your name.")
            return
        if not email:
            st.error("Please enter your email address.")
            return

        # Combine selected + custom skills
        all_skills = selected_skills.copy()
        if custom_skills:
            extras = [s.strip() for s in custom_skills.split(",") if s.strip()]
            all_skills.extend(extras)

        profile = {
            "_id": "default_user",
            "name": name,
            "email": email,
            "phone": phone,
            "linkedin": linkedin,
            "github": github,
            "education": education,
            "college": college,
            "degree": degree,
            "graduation_year": graduation_year,
            "cgpa": cgpa,
            "skills": all_skills,
            "custom_skills": custom_skills,
            "experience_level": experience_level,
            "preferred_roles": preferred_roles,
            "location_pref": location_pref,
            "stipend_expectation": stipend_expectation,
            "availability": availability,
            "about_me": about_me,
        }

        if "resume_analysis" in st.session_state:
            profile["ats_score"] = st.session_state["resume_analysis"].get("ats_score", 0)
            profile["missing_skills"] = st.session_state["resume_analysis"].get("missing_skills", [])

        try:
            with st.spinner("Saving to IBM Cloudant..."):
                save_user_profile(profile)
            st.success("✅ Profile saved successfully!")
            st.session_state["user_profile"] = profile
            st.balloons()
        except Exception as e:
            st.error(f"Failed to save profile: {e}")