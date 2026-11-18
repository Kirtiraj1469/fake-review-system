import streamlit as st
import os
import logging
import warnings

# Suppress all warnings and unnecessary logs
warnings.filterwarnings('ignore')
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('streamlit').setLevel(logging.ERROR)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Suppress TensorFlow logs if present

from home_page import home_page
from training import training
from testing import test_model
from mapreduce_page import mapreduce_page

# Page configuration
st.set_page_config(
    page_title="Fake Review Detection System",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern shadcn-inspired styling adapted to Streamlit
st.markdown("""
<style>
    :root { color-scheme: light; }
    .stApp { background: #f8fafc; color: #0f172a; }
    [data-testid="stSidebar"] { background: #fff; border-right: 1px solid #e2e8f0; }
    [data-testid="stSidebar"] h1 { color: #0f172a; font-size: 1.15rem; font-weight: 700; }
    .main .block-container { max-width: 1180px; padding: 2.5rem 2rem 4rem; }
    h1, h2, h3 { color: #0f172a; letter-spacing: -.025em; }
    [data-testid="stMetric"] { background: white; padding: 1.1rem; border: 1px solid #e2e8f0; border-radius: 12px; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color: #e2e8f0; border-radius: 12px; }
    .stButton button[kind="primary"] { background: #0f172a; border-color: #0f172a; border-radius: 8px; }
    .stButton button { border-radius: 8px; }
    [data-testid="stFileUploader"] section { border-radius: 10px; }
    #MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("🔍 Fake Review Detection")
st.sidebar.markdown("---")

# Add a navbar with buttons
nav = st.sidebar.radio(
    "Navigate",
    ["🛍️ Scrape Reviews", "🎓 Training", "🧪 Testing", "🗺️ MapReduce"],
    label_visibility='visible'
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='color: white; padding: 1rem;'>
<h4>📖 About</h4>
<p>This system uses machine learning to detect fake product reviews using:</p>
<ul>
<li>TF-IDF Vectorization</li>
<li>Sentiment Analysis</li>
<li>Multiple ML Models</li>
</ul>
</div>
""", unsafe_allow_html=True)

# Show content based on the selected button in the navbar
if nav == "🛍️ Scrape Reviews":
    home_page()
elif nav == "🎓 Training":
    training()
elif nav == "🧪 Testing":
    test_model()
elif nav == "🗺️ MapReduce":
    mapreduce_page()


