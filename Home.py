from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="Comprehensive household resources",
    layout="wide",
    initial_sidebar_state="collapsed",
)

page = st.navigation(
    [
        st.Page("app_pages/home.py", title="Home", icon=":material/home:"),
        st.Page("app_pages/age_slicing.py", title="Age slicing", icon=":material/stacks:"),
        st.Page("app_pages/methodology.py", title="Methodology", icon=":material/menu_book:"),
    ],
    position="top",
)
page.run()
