import streamlit as st
import yfinance as yf
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Etsy Profesyonel Fiyat Paneli", layout="wide", page_icon="💎")

# --- PROFESYONEL TASARIM (CSS) ---
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    [data-testid="stSidebar"] {
        background-color: #2c3e50 !important;
    }
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1 {
        color: #ecf0f1 !important;
    }
    div[data-testid="stExpander"], .stDataFrame {
        background-color: white !important;
        border-radius: 12px !important;
        border: 1px solid #d1d8e0 !important;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        padding: 10px;
    }
    h1, h2, h3 {
        color: #2c3e50 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    input, select {
        color: #2c3e50 !important;
        border: 1px solid #bdc3c7 !important;
        border-radius: 8px !important;
    }
    div.stButton > button {
        background-color: #3498db !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 2rem !important;
        transition: all 0.3s ease;
        font-weight: bold;
    }
    div.stButton > button:hover {
        background-color: #2980b9 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- VERİ ÇEKME ---
@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except:
        return 3
