import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import base64
from io import BytesIO
from PIL import Image

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- GOOGLE SHEETS BAĞLANTI FONKSİYONU ---
def get_gsheet_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        # Streamlit Secrets'tan gelen bilgileri kullanır
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Sizin Tablo ID'niz
        return client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return None

# --- YARDIMCI FONKSİYONLAR ---
def image_to_base64(image_file):
    if image_file is not None:
        img = Image.open(image_file)
        img.thumbnail((300, 300))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except:
        return 34.80, 2650.0, 31.0

# --- TASARIM (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #E2E2E0; }
    [data-testid="stSidebar"] { background-color: #0E2931 !important; }
    .product-card {
        background-color: white; padding: 15px; border-radius: 12px;
        border: 1px solid #eee; text-align: center; margin-bottom: 20px;
    }
    div.stButton > button { background-color: #861211 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİLERİ ÇEK ---
dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    data = sheet.get_all_records()
    st.session_state.urunler = data
else:
    st.session_state.urunler = []

# --- SIDEBAR ---
with st.sidebar:
    st.title("Yönetim Paneli")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru))
    gr_iscilik = st.number_input("🛠️ Gram İşçilik ($)", value=1.0)
    bolge = st.selectbox("Teslimat", ["Amerika", "Avrupa"])
    kargo = 400.0 if bolge == "Amerika" else 850.0
    indirim = st.number_input("🏷️ İndirim (%)", value=10.0)
    komisyon = 0.1692

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Yönetim Paneli")
tab1, tab2 = st.tabs(["📊 Fiyat Çizelgesi", "➕ Ürün Ekleme"])

with tab2:
    st.subheader("Yeni Ürün Ekle")
    u_ad = st.text_input("Ürün Adı")
    u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
    u_gr = st.number_input("Gram", value=5.0)
    u_kar = st.number_input("Hedef Kar (TL)", value=2000.0)
    uploaded_file = st.file_uploader("Görsel Seç")

    if st.button("Kaydet ve Excel'e Gönder"):
        if u_ad and sheet:
            img_b64 = image_to_base64(uploaded_file)
            # EXCEL'E YAZ
            sheet.append_row([u_ad, u_maden, u_gr, u_kar, img_b64])
            st.success("Excel güncellendi! Sayfayı yenileyin.")
            st.rerun()

with tab1:
    if st.session_state.urunler:
        cols = st.columns(4)
        for idx, row in enumerate(st.session_state.urunler):
            # Hesaplama Mantığı
            ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
            maliyet = ((ons/31.1035) * row['Gr'] * kur) + (row['Gr'] * gr_iscilik * kur) + kargo
            sabitler = (0.20 * kur) + 3.60
            fiyat = (maliyet + row['Hedef Kar'] + sabitler) / (1 - (komisyon + indirim/100))
            
            img_src = f"data:image/png;base64,{row['GörselData']}" if row.get('GörselData') else ""
            
            with cols[idx % 4]:
                st.markdown(f"""
                <div class="product-card">
                    <img src="{img_src}" style="width:100%; height:120px; object-fit:contain;">
                    <h4>{row['Ürün']}</h4>
                    <h2 style="color:#861211;">{round(fiyat, 2)} ₺</h2>
                    <p>$ {round(fiyat/kur, 2)}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Henüz ürün yok.")
