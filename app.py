import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_gsheet_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Tablo ID'nizi buraya doğru girdiğinizden emin olun
        return client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
    except Exception as e:
        st.error(f"⚠️ Bağlantı Hatası: Secrets bilgilerini veya API iznini kontrol edin. Detay: {e}")
        return None

# --- YARDIMCI FONKSİYONLAR ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            # 1. Renk formatını standart hale getir (Hata önleyici)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 2. Boyutu çok daha küçük yap (Hücre sınırı için kritik)
            img.thumbnail((120, 120)) 
            
            # 3. Veriyi JPEG olarak sıkıştır (Base64 karakter sayısını %70 azaltır)
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=40, optimize=True)
            
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            st.error(f"Görsel işleme hatası: {e}")
            return ""
    return ""

@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except:
        return 35.0, 2650.0, 31.0

# --- TASARIM ---
st.markdown("""
    <style>
    .stApp { background-color: #F0F2F6; }
    .product-card {
        background-color: white; padding: 20px; border-radius: 15px;
        border: 1px solid #ddd; text-align: center; margin-bottom: 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    div.stButton > button { width: 100%; background-color: #861211 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- VERİLERİ HAZIRLA ---
dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()
sheet = get_gsheet_client()

# Sayfa her yüklendiğinde verileri Sheets'ten çek
if sheet:
    try:
        st.session_state.urunler = sheet.get_all_records()
    except Exception as e:
        st.error(f"Veri çekme hatası: {e}")
        st.session_state.urunler = []
else:
    st.session_state.urunler = []

# --- SIDEBAR ---
with st.sidebar:
    st.header("📊 Parametreler")
    kur = st.number_input("💵 Güncel Kur (USD/TRY)", value=float(dolar_kuru))
    gr_iscilik = st.number_input("🛠️ İşçilik ($/Gram)", value=1.5)
    kargo = st.number_input("🚚 Kargo Maliyeti (TL)", value=450.0)
    indirim = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0)
    komisyon = 0.17 # Etsy toplam kesinti yaklaşık

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat Paneli")
tab1, tab2 = st.tabs(["📋 Ürün Listesi", "➕ Yeni Ürün"])

with tab2:
    with st.form("yeni_urun_form", clear_on_submit=True):
        u_ad = st.text_input("Ürün Adı")
        u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
        u_gr = st.number_input("Gram", min_value=0.1, value=5.0)
        u_kar = st.number_input("Hedef Kar (TL)", value=2000.0)
        u_dosya = st.file_uploader("Görsel Yükle")
        submit = st.form_submit_button("Excel'e Kaydet")

        if submit and u_ad:
            if sheet:
                img_data = image_to_base64(u_dosya)
                # Excel başlıkları: Ürün, Maden, Gr, Hedef Kar, GörselData
                sheet.append_row([u_ad, u_maden, u_gr, u_kar, img_data])
                st.success(f"{u_ad} başarıyla Excel'e eklendi! Sayfayı yenileyin.")
                st.rerun()

with tab1:
    if st.session_state.urunler:
        cols = st.columns(4)
        for idx, row in enumerate(st.session_state.urunler):
            try:
                # Veri doğrulama
                m_ad = row.get('Ürün', 'Bilinmeyen')
                m_tur = row.get('Maden', 'Gümüş')
                m_gram = float(row.get('Gr', 0))
                m_hedef = float(row.get('Hedef Kar', 0))
                
                # Hesaplama
                ons = ons_altin if m_tur == "Altın" else ons_gumus
                maliyet = ((ons/31.1035) * m_gram * kur) + (m_gram * gr_iscilik * kur) + kargo
                fiyat_tl = (maliyet + m_hedef) / (1 - (komisyon + indirim/100))
                
                img_src = f"data:image/png;base64,{row['GörselData']}" if row.get('GörselData') else ""
                
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_src}" style="width:100%; height:130px; object-fit:contain; margin-bottom:10px;">
                        <div style="font-weight:bold; height:40px;">{m_ad}</div>
                        <div style="color:#861211; font-size:22px; font-weight:bold;">{round(fiyat_tl, 2)} ₺</div>
                        <div style="color:gray;">$ {round(fiyat_tl/kur, 2)}</div>
                    </div>
                    """, unsafe_allow_html=True)
            except:
                continue
    else:
        st.warning("Görüntülenecek ürün bulunamadı. Lütfen Excel tablonuzu veya bağlantınızı kontrol edin.")
