import streamlit as st
import os
from datetime import datetime, timedelta, date
import pandas as pd
import io
import csv

# Import custom modules
from config import SERP_API_KEY
from news_utils import (
    get_news_by_keywords,
    sort_articles_by_source_and_date,
    filter_articles_by_media,
    read_media_list,
    save_initial_articles_to_csv,
    save_news_to_txt
)

# Page configuration
st.set_page_config(
    page_title="SOSV Curated News Search",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Modern UI Styling (Light Theme focus)
st.markdown("""
    <style>
    /* Global font size increase */
    html, body, [data-testid="stAppViewContainer"] {
        font-size: 1.2rem !important;
    }
    
    /* Sidebar width and background */
    section[data-testid="stSidebar"] {
        width: 450px !important;
        background-color: #001E42 !important; /* SOSV Dark Navy */
    }
    
    /* Force Sidebar Headers, Labels and Text to White & Left Align */
    section[data-testid="stSidebar"] [data-testid="stHeader"] h1,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown ul li {
        color: #FFFFFF !important;
        text-align: left !important;
        font-size: 1.25rem !important;
        margin-left: 0 !important;
        padding-left: 0 !important;
    }

    /* Remove padding/margin from all sidebar containers to ensure perfect left alignment */
    [data-testid="stSidebar"] .element-container,
    [data-testid="stSidebar"] .stVerticalBlock,
    [data-testid="stSidebar"] [data-testid="stForm"] {
        padding-left: 0 !important;
        margin-left: 0 !important;
    }

    /* Sidebar Expander Styling */
    section[data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(0, 30, 66, 0.8) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 8px !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] summary {
        background-color: transparent !important;
        color: #FFFFFF !important;
    }
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
        color: #FFFFFF !important;
        font-size: 1.1rem !important;
    }

    /* Primary Search Button - Huge Text & Normal Shape */
    [data-testid="stSidebar"] button[kind="secondaryFormSubmit"],
    [data-testid="stSidebar"] button[kind="primary"] {
        width: 100% !important;
        border: none !important;
        border-radius: 8px !important;
        height: 4.5rem !important;
        background: linear-gradient(90deg, #00F9FC 0%, #00FE76 100%) !important;
        color: #001E42 !important;
        cursor: pointer !important;
        margin-top: 0.5rem !important; /* Tighter margin */
    }
    /* Force perfectly sized text on any element inside the search button */
    [data-testid="stSidebar"] button[kind="secondaryFormSubmit"] * {
        font-size: 1.8rem !important; /* Slightly smaller as requested */
        color: #001E42 !important;
        font-weight: 900 !important;
        line-height: 1 !important;
    }

    /* Period Selection - Manual 4-Button Grid */
    .period-container .stButton button,
    section[data-testid="stSidebar"] input {
        background-color: #FFFFFF !important;
        color: #001E42 !important;
        border: 1px solid #DFE4EE !important;
        border-radius: 8px !important;
        height: 40px !important;
        line-height: normal !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        transition: none !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* Target Date Input Container */
    div[data-testid="stDateInput"], 
    div[data-testid="stDateInput"] > div {
        height: 40px !important;
        min-height: 40px !important;
    }

    /* Center text for buttons and date inputs */
    .period-container .stButton button,
    div[data-testid="stDateInput"] input {
        text-align: center !important;
        padding: 0 !important;
    }

    /* Keyword search box - Align Left */
    div[data-testid="stTextInput"] input {
        text-align: left !important;
        padding-left: 1rem !important;
        font-weight: 500 !important;
        justify-content: flex-start !important;
    }

    /* --- Button Interaction Logic --- */
    
    /* 1. Default (Unselected) State */
    .period-container .stButton button,
    .inactive-period button {
        background-color: #FFFFFF !important;
        color: #001E42 !important;
    }
    .period-container .stButton button p,
    .inactive-period button p {
        color: #001E42 !important;
    }

    /* 2. Selected (Active) State */
    .active-period button {
        background-color: #295FD2 !important;
        border-color: #295FD2 !important;
    }
    .active-period button p,
    .active-period button span,
    .active-period button * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* 3. Hover State (Applies to both selected and unselected) */
    .period-container .stButton button:hover,
    .active-period button:hover,
    [data-testid="stSidebar"] button[kind="secondary"]:hover {
        background-color: #1e3a8a !important;
        border-color: #1e3a8a !important;
    }
    .period-container .stButton button:hover p,
    .period-container .stButton button:hover span,
    .period-container .stButton button:hover *,
    .active-period button:hover p,
    .active-period button:hover span,
    [data-testid="stSidebar"] button[kind="secondary"]:hover * {
        color: #FFFFFF !important;
        -webkit-text-fill-color: #FFFFFF !important;
    }

    /* LAYOUT: Standardized gaps */
    [data-testid="stSidebar"] div.stVerticalBlock {
        gap: 8px !important; 
    }
    [data-testid="stSidebar"] [data-testid="column"] {
        padding: 0 4px !important;
    }
    
    /* Clean up form */
    [data-testid="stForm"] {
        border: none !important;
        padding: 0 !important;
        background-color: transparent !important;
        margin: 0 !important;
    }
    
    /* Space below search and expander */
    div[data-testid="stExpander"] {
        margin-top: 25px !important;
    }
    
    /* Title adjustment */
    .app-title {
        margin-top: -6rem !important;
        margin-bottom: 0px !important;
        font-size: 2.5rem !important;
    }
    .title-sep {
        border-top: 1px solid #DFE4EE;
        margin-bottom: 0.8rem !important;
    }
    div[data-testid="stDateInput"] label {
        display: none !important;
    }
    div[data-testid="stTextInput"] {
        margin-top: 20px !important;
        margin-bottom: 10px !important;
    }
    [data-testid="stSlider"] {
        margin-top: 10px !important;
        margin-bottom: 20px !important;
    }
    [data-testid="stSlider"] label p {
        font-weight: 400 !important;
        font-size: 1.1rem !important;
        margin-top: 0.5rem !important;
    }
    
    .main {
        background-color: #F8FAFC;
    }

    /* Article Card Styling - ULTRA COMPACT */
    .article-card {
        background-color: #ffffff;
        padding: 6px 12px !important;
        border-radius: 6px;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #295FD2 !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
    }
    .article-title {
        font-size: 1.1rem !important;
        font-weight: 700;
        color: #295FD2;
        text-decoration: none;
        display: inline-block;
        margin-bottom: 0px !important;
        line-height: 1.2 !important;
    }
    .article-title:hover {
        color: #1e3a8a;
        text-decoration: underline;
    }
    .article-meta {
        color: #64748b;
        font-size: 0.85rem !important;
        margin-top: 0px !important;
        line-height: 1.2 !important;
    }
    .success-msg {
        background-color: #ecfdf5;
        color: #065f46;
        padding: 0.5rem 1rem !important;
        border-radius: 6px;
        margin-bottom: 0.8rem !important;
        border: 1px solid #34d399;
        font-weight: 600;
        font-size: 0.95rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# App Title
st.markdown('<h1 class="app-title">SOSV Curated News Search</h1>', unsafe_allow_html=True)
st.markdown('<div class="title-sep"></div>', unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    # Removed "Search Configuration" header
    
    # Preset Logic
    today = date.today()
    
    # Initialize session state for period selection
    if 'selected_period' not in st.session_state:
        st.session_state.selected_period = "Past year"
    
    
    # Custom 2x2 Grid with per-row columns for tighter grouping
    st.markdown('<div class="period-container">', unsafe_allow_html=True)
    
    # Row 1: Week and Month
    r1_col1, r1_col2 = st.columns(2)
    with r1_col1:
        is_selected = (st.session_state.selected_period == "Past week")
        label = "✓ Past week" if is_selected else "Past week"
        cls = "active-period" if is_selected else "inactive-period"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button(label, key="btn_past_week", use_container_width=True):
            st.session_state.selected_period = "Past week"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r1_col2:
        is_selected = (st.session_state.selected_period == "Past month")
        label = "✓ Past month" if is_selected else "Past month"
        cls = "active-period" if is_selected else "inactive-period"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button(label, key="btn_past_month", use_container_width=True):
            st.session_state.selected_period = "Past month"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Row 2: Year and YTD
    r2_col1, r2_col2 = st.columns(2)
    with r2_col1:
        is_selected = (st.session_state.selected_period == "Past year")
        label = "✓ Past year" if is_selected else "Past year"
        cls = "active-period" if is_selected else "inactive-period"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button(label, key="btn_past_year", use_container_width=True):
            st.session_state.selected_period = "Past year"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with r2_col2:
        is_selected = (st.session_state.selected_period == "YTD")
        label = "✓ YTD" if is_selected else "YTD"
        cls = "active-period" if is_selected else "inactive-period"
        st.markdown(f'<div class="{cls}">', unsafe_allow_html=True)
        if st.button(label, key="btn_ytd", use_container_width=True):
            st.session_state.selected_period = "YTD"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
            
    selected_period = st.session_state.selected_period
    
    # Calculation happens every rerun
    default_start = today - timedelta(days=365)
    default_end = today
    
    if selected_period == "Past week":
        default_start = today - timedelta(days=today.weekday() + 7)
    elif selected_period == "Past month":
        first_of_this_month = today.replace(day=1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        default_start = last_of_prev_month.replace(day=1)
    elif selected_period == "Past year":
        default_start = date(today.year - 1, 1, 1)
    elif selected_period == "YTD":
        default_start = date(today.year, 1, 1)

    with st.form("search_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        s_date = col1.date_input("Start Date label hidden", value=default_start, label_visibility="collapsed")
        e_date = col2.date_input("End Date label hidden", value=default_end, label_visibility="collapsed")

        keywords = st.text_input("Keywords (comma separated)", placeholder="e.g. SOSV, Climate Tech")
        
        num_results = st.slider("Max results", 5, 100, 20)
        
        search_button = st.form_submit_button("Search", use_container_width=True)

    # Replace file link with an expander to show media list directly
    try:
        allowed_media = sorted(list(read_media_list("media.txt")))
        with st.sidebar.expander("View Media List"):
            for item in allowed_media:
                st.write(f"- {item}")
    except Exception:
        st.sidebar.error("Could not load media list.")

if search_button:
    if not keywords:
        st.error("Please enter at least one keyword.")
    else:
        with st.spinner("Searching for news articles..."):
            keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
            allowed_media = read_media_list("media.txt")
            all_filtered_results = []
            
            for kw in keywords_list:
                _, news_list = get_news_by_keywords(
                    SERP_API_KEY, 
                    kw, 
                    num_results=num_results, 
                    start_date_str=s_date, 
                    end_date_str=e_date
                )
                
                sorted_news = sort_articles_by_source_and_date(news_list)
                filtered_news = filter_articles_by_media(sorted_news, allowed_media)
                
                # Save results to disk
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_initial_articles_to_csv(filtered_news, kw, timestamp, suffix="_filtered")
                save_news_to_txt(filtered_news, kw, timestamp, suffix="_filtered")
                
                all_filtered_results.extend(filtered_news)
            
            # Show summary message at the top
            if all_filtered_results:
                st.markdown(f'<div class="success-msg">✅ Search complete. {len(all_filtered_results)} filtered articles found.</div>', unsafe_allow_html=True)
                
                # --- Download Buttons Section ---
                col_dl1, col_dl2 = st.columns(2)
                
                # Prepare CSV data
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["number", "source", "source_url", "date", "author", "title", "url"])
                for i, article in enumerate(all_filtered_results, 1):
                    writer.writerow([
                        i,
                        article.get('source', ''),
                        article.get('source_url', ''),
                        article.get('timestamp', ''),
                        article.get('author', ''),
                        article.get('title', ''),
                        article.get('url', '')
                    ])
                
                col_dl1.download_button(
                    label="📥 Download Results as CSV",
                    data=csv_buffer.getvalue(),
                    file_name=f"sosv_news_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # Prepare TXT data
                txt_buffer = io.StringIO()
                txt_buffer.write(f"SOSV NEWS SEARCH RESULTS\n")
                txt_buffer.write("=" * 50 + "\n\n")
                txt_buffer.write(f"Keywords: {keywords}\n")
                txt_buffer.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for i, article in enumerate(all_filtered_results, 1):
                    txt_buffer.write(f"Article {i}:\n")
                    txt_buffer.write(f"Title: {article['title']}\n")
                    txt_buffer.write(f"URL: {article['url']}\n")
                    txt_buffer.write(f"Source: {article['source']}\n")
                    txt_buffer.write(f"Author: {article['author']}\n")
                    txt_buffer.write(f"Date: {article['timestamp']}\n")
                    txt_buffer.write("-" * 40 + "\n\n")
                
                col_dl2.download_button(
                    label="📥 Download Results as TXT",
                    data=txt_buffer.getvalue(),
                    file_name=f"sosv_news_{timestamp}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
                
                # Render all results in a single block for zero container gaps
                results_html = ""
                for article in all_filtered_results:
                    results_html += f"""
                        <div class="article-card">
                            <a class="article-title" href="{article['url']}" target="_blank">{article['title']}</a>
                            <div class="article-meta">
                                {article['source']} • {article['author']} • {article['timestamp']}
                            </div>
                        </div>
                    """
                st.markdown(results_html, unsafe_allow_html=True)
            else:
                st.info("No articles found matching the criteria.")
