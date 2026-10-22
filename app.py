"""Entry point: streamlit run app.py"""

import streamlit as st

from interp_demo.ui import common

st.set_page_config(page_title="Language Preference Demo", page_icon="🌐", layout="wide")

common.PAGES.update(
    enroll=st.Page("app_pages/enroll.py", title="1. Create patient profile", icon="📝", url_path="enroll", default=True),
    scan=st.Page("app_pages/scan.py", title="2. Staff scan", icon="📷", url_path="scan"),
    session=st.Page("app_pages/session.py", title="3. Interpretation session", icon="💬", url_path="session"),
)

common.init_state()
nav = st.navigation(list(common.PAGES.values()))
common.render_sidebar()
nav.run()
