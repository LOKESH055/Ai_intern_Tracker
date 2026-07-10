# main.py
import streamlit as st

st.set_page_config(
    page_title="Internship Discovery Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

from app.components.chat_ui import render_chat
from app.components.resume_ui import render_resume_page
from app.components.tracked_jobs_ui import render_tracked_jobs_page
from app.components.profile_ui import render_profile_page


@st.cache_resource
def setup_app():
    """Initialize databases and restore monitors once per app session."""
    try:
        from app.services.cloudant_client import initialize_databases
        initialize_databases()
    except Exception as e:
        print(f"DB init warning: {e}")

    try:
        from app.services.monitor import restore_monitors_from_db
        restored = restore_monitors_from_db()
        print(f"[Startup] Restored {len(restored)} monitor(s)")
    except Exception as e:
        print(f"Monitor restore warning: {e}")

    return True


def render_sidebar():
    from app.components.monitor_ui import render_monitor_sidebar
    with st.sidebar:
        st.markdown("## 🎯 Internship Assistant")
        st.markdown("---")

        # Show profile name if loaded
        profile = st.session_state.get("user_profile", {})
        if profile.get("name"):
            st.markdown(f"👤 **{profile['name']}**")
            st.markdown(f"📧 {profile.get('email','')}")
            st.markdown("---")

        st.markdown("### 📋 Navigation")
        page = st.radio(
            "Go to",
            ["💬 Chat", "👤 Profile", "📄 Resume Analysis", "📊 Tracked Jobs"],
            label_visibility="collapsed"
        )

        st.markdown("---")
        st.markdown("### ⚙️ Session")

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_jobs = []
            st.session_state.last_ranked = []
            st.rerun()

        if "resume_analysis" in st.session_state:
            ats = st.session_state["resume_analysis"].get("ats_score", 0)
            st.markdown("---")
            st.markdown(f"### 📄 Resume Loaded")
            st.markdown(f"ATS Score: **{ats}/100**")
            if st.button("🗑️ Clear Resume", use_container_width=True):
                del st.session_state["resume_analysis"]
                del st.session_state["resume_text"]
                st.rerun()

        # Monitoring section — reads from Cloudant, survives reruns
        render_monitor_sidebar()

        st.markdown("---")
        st.markdown("""
            <div style='font-size: 12px; color: #888;'>
                <b>Stack</b><br>
                🤖 IBM watsonx.ai<br>
                🦙 Llama 3.3 70B<br>
                ☁️ IBM Cloud Object Storage<br>
                🗄️ IBM Cloudant<br>
                🔍 RapidAPI JSearch<br>
                🐍 Python + Streamlit
            </div>
        """, unsafe_allow_html=True)

    return page


def main():
    # Initialize once per session
    setup_app()

    # Load profile into session on startup
    if "user_profile" not in st.session_state:
        try:
            from app.services.cloudant_client import get_user_profile
            profile = get_user_profile()
            if profile:
                st.session_state["user_profile"] = profile
        except Exception:
            pass

    page = render_sidebar()

    if page == "💬 Chat":
        render_chat()
    elif page == "👤 Profile":
        render_profile_page()
    elif page == "📄 Resume Analysis":
        render_resume_page()
    elif page == "📊 Tracked Jobs":
        render_tracked_jobs_page()


if __name__ == "__main__":
    main()