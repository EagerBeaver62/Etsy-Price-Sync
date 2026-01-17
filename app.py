import streamlit as st
import yfinance as yf
import pandas as pd
import os
import base64
from io import BytesIO
from PIL import Image

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- GOOGLE SHEETS AYARI ---
SHEET_ID = "1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# --- FONKSİYONLAR ---
def image_to_base64(image_file):
    if image_file is not None:
        img = Image.open(image_file)
        img.thumbnail((300, 300))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

def verileri_yukle():
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = [c.strip() for c in df.columns]
        return df.to_dict('records')
    except:
        if os.path.exists("urun_veritabani.csv"):
            return pd.read_csv("urun_veritabani.csv").to_dict('records')
        return []

# --- PİYASA VERİLERİ ---
@st.cache_data(ttl=3600)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar, altin, gumus
    except:
        return 34.8, 2650.0, 31.0

dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()

if 'urunler' not in st.session_state:
    st.session_state.urunler = verileri_yukle()

# --- SIDEBAR ---
with st.sidebar:
    st.title("Yönetim Paneli")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru), step=0.01)
    gr_iscilik_usd = st.number_input("🛠️ Gram Başı İşçilik ($)", value=1.0, step=0.1)
    bolge = st.selectbox("Teslimat Bölgesi", ["Amerika", "Avrupa"])
    kargo_maliyeti = 400.0 if bolge == "Amerika" else 850.0
    kargo_maliyeti = st.number_input("🚚 Kargo Ücreti (TL)", value=kargo_maliyeti)
    indirim_oran = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0)
    toplam_komisyon_orani = 0.1692 

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Yönetim Paneli")
tab1, tab2 = st.tabs(["📊 Fiyat Çizelgesi", "➕ Ürün Ekleme"])

with tab2:
    st.subheader("Yeni Ürün Tanımla")
    c1, c2 = st.columns([1, 1])
    with c1:
        u_ad = st.text_input("Ürün Adı / SKU")
        u_maden = st.selectbox("Maden Türü", ["Gümüş", "Altın"])
        u_gr = st.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
        u_kar = st.number_input("Net Kar Hedefi (TL)", value=2500.0)
    with c2:
        uploaded_file = st.file_uploader("Ürün Görseli Seç", type=['jpg', 'png', 'jpeg'])
    
    if st.button("Ürünü Listeye Ekle"):
        if u_ad:
            img_code = image_to_base64(uploaded_file)
            yeni = {"Ürün": u_ad, "Maden": u_maden, "Gr": u_gr, "Hedef Kar": u_kar, "GörselData": img_code}
            st.session_state.urunler.append(yeni)
            st.success("Ürün eklendi!")
            st.rerun()

with tab1:
    if st.session_state.urunler:
        cols = st.columns(4)
        for idx, row in enumerate(st.session_state.urunler):
            # Hesaplama
            ons = ons_altin if row.get('Maden') == "Altın" else ons_gumus
            fiyat = (( (ons/31.1035)*row.get('Gr',0)*kur ) + (row.get('Gr',0)*gr_iscilik_usd*kur) + kargo_maliyeti + row.get('Hedef Kar',0) + (0.2*kur+3.6)) / (1-(toplam_komisyon_orani+indirim_oran/100))
            
            img_src = f"data:image/png;base64,{row['GörselData']}" if row.get('GörselData') else "https://img.icons8.com/fluency/96/diamond.png"
            
            with cols[idx % 4]:
                st.markdown(f"""
                <div style="background-color: white; padding: 15px; border-radius: 12px; border: 1px solid #eee; text-align: center; margin-bottom: 10px;">
                    <img src="{img_src}" style="width:100%; height:150px; object-fit:cover; border-radius:8px;">
                    <h4 style="margin:10px 0;">{row['Ürün']}</h4>
                    <h3 style="color:#861211; margin:0;">{round(fiyat, 2)} ₺</h3>
                    <p style="color:#2B7574; margin:0;">$ {round(fiyat/kur, 2)}</p>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🗑️ Sil ({idx})", key=f"del_{idx}"):
                    st.session_state.urunler.pop(idx)
                    st.rerun()
    else:
        st.info("Henüz ürün yok.")
