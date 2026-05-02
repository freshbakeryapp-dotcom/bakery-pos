import streamlit as st
import sqlite3
from datetime import datetime
import pandas as pd

st.title("📅 Local Events")

conn = sqlite3.connect("bakery.db")
conn.row_factory = sqlite3.Row

tab1, tab2 = st.tabs(["📋 Upcoming Events", "➕ Add Event"])

with tab1:
    from src.events import get_upcoming_events, delete_event
    
    upcoming = get_upcoming_events(30)
    
    if upcoming:
        st.write(f"**{len(upcoming)} events in the next 30 days**")
        
        for ev in upcoming:
            impact_color = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(ev['expected_impact'], "🟡")
            
            with st.container():
                cols = st.columns([1, 8, 1])
                cols[0].markdown(f"### {impact_color}")
                cols[1].markdown(f"**{ev['event_type'].replace('_', ' ').title()}** — {ev['date']}")
                desc = ev['description'] if ev['description'] else 'No description'
                cols[1].caption(f"{desc} | Impact: {ev['expected_impact'].title()}")
                if cols[2].button("🗑️", key=f"del_{ev['id']}"):
                    delete_event(ev['id'])
                    st.rerun()
    else:
        st.info("No upcoming events. Add one to help the AI forecast better.")

with tab2:
    st.subheader("Add New Event")
    st.caption("Tell the AI about local happenings that might affect foot traffic.")
    
    with st.form("add_event_form", clear_on_submit=True):
        cols = st.columns(2)
        ev_date = cols[0].date_input("Date", key="ev_date_page")
        ev_type = cols[1].selectbox(
            "Event Type",
            ["nearby_event", "construction", "school_activity", "promotion", "holiday_local", "other"],
            format_func=lambda x: x.replace("_", " ").title()
        )
        
        ev_impact = st.select_slider(
            "Expected Impact",
            options=["low", "medium", "high"],
            value="medium",
            format_func=lambda x: {"low": "🟢 Low (±5%)", "medium": "🟡 Medium (±15%)", "high": "🔴 High (±30%)"}[x]
        )
        
        ev_desc = st.text_area("Description (optional)", placeholder="e.g., School sports day — expect 200+ parents")
        
        submitted = st.form_submit_button("➕ Add Event", type="primary", use_container_width=True)
        
        if submitted:
            from src.events import add_event
            add_event("Store", ev_date.strftime("%Y-%m-%d"), ev_type, ev_desc, ev_impact)
            st.success(f"✅ Event added for {ev_date}!")
            st.balloons()
            st.rerun()

conn.close()