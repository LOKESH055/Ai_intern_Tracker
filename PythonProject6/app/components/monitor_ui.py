# app/components/monitor_ui.py
import streamlit as st
from app.services.monitor import (
    start_monitoring,
    stop_monitoring,
    stop_all_monitoring,
    get_active_monitors,
    run_monitor_check,
    is_monitoring
)


def render_monitor_sidebar():
    """
    Render monitoring controls in the sidebar.
    Called from main.py inside the sidebar block.
    """
    monitors = get_active_monitors()

    st.markdown("---")
    st.markdown("### 🔔 Monitoring")

    if monitors:
        st.success(f"🟢 Active: {len(monitors)} monitor(s)")
        for job_id, info in monitors.items():
            st.markdown(
                f"**{info['query']}**"
                + (f" · {info['location']}" if info['location'] else "")
            )
            st.caption(f"Next check: {info['next_run']}")
            if st.button("⏹ Stop", key=f"stop_{job_id}", use_container_width=True):
                stop_monitoring(job_id)
                st.rerun()
    else:
        st.info("No active monitors")

    # Notifications badge
    notifications = st.session_state.get("monitor_notifications", [])
    if notifications:
        st.markdown("---")
        st.warning(f"🔔 {len(notifications)} new alert(s)!")
        if st.button("View Alerts", use_container_width=True):
            st.session_state["show_alerts"] = True


def render_monitor_controls(query: str = "", location: str = ""):
    """
    Render monitoring toggle inside the chat UI after a search.
    Shows automatically after internship results are fetched.
    """
    if not query:
        return

    already_monitoring = is_monitoring(query)

    with st.container():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col1:
            if already_monitoring:
                st.success(
                    f"🟢 **Monitoring active** for `{query}`"
                    + (f" in `{location}`" if location else "")
                    + " — checking every 6 hours"
                )
            else:
                st.info(
                    f"💡 Want to be notified when new **{query}** listings appear?"
                )

        with col2:
            if already_monitoring:
                job_id = f"monitor_{query.replace(' ', '_')}"
                if st.button("⏹ Stop Monitoring", use_container_width=True):
                    stop_monitoring(job_id)
                    st.rerun()
            else:
                if st.button("🔔 Start Monitoring", use_container_width=True, type="primary"):
                    job_id = start_monitoring(
                        query=query,
                        location=location,
                        interval_hours=6
                    )
                    st.success(f"✅ Monitoring started! You'll be emailed when new listings appear.")
                    st.rerun()


def render_notifications():
    """Render in-app notification alerts."""
    notifications = st.session_state.get("monitor_notifications", [])
    show = st.session_state.get("show_alerts", False)

    if not notifications:
        return

    if show:
        st.markdown("---")
        st.markdown("### 🔔 New Internship Alerts")

        for notif in reversed(notifications):
            with st.expander(
                f"🆕 {notif['count']} new job(s) for '{notif['query']}' "
                f"at {notif['time']}",
                expanded=True
            ):
                for job in notif["jobs"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{job['title']}** at {job['company']}")
                        location = "🌐 Remote" if job.get("is_remote") else job.get("location", "—")
                        st.caption(location)
                    with col2:
                        if job.get("apply_link"):
                            st.markdown(f"[Apply →]({job['apply_link']})")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Mark all as read"):
                st.session_state["monitor_notifications"] = []
                st.session_state["show_alerts"] = False
                st.rerun()
        with col2:
            if st.button("Close"):
                st.session_state["show_alerts"] = False
                st.rerun()