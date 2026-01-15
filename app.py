import streamlit as st
import yfinance as yf
import pandas as pd
import os
import base64
from io import BytesIO
from PIL import Image

# 1. Sayfa Ayarları
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- GÖRSEL İŞLEME ---
def image_to_base64(image_file):
    if image_file is not None:
        img = Image.open(image_file)
        img.thumbnail((300, 300))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode()
    return None

# --- VERİ SAKLAMA (KALICILIK) ---
DB_FILE = "urun_veritabani.csv"

def verileri_yukle():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE).to_dict('records')
    return []

def verileri_kaydet(urunler):
    df = pd.DataFrame(urunler)
    df.to_csv(DB_FILE, index=False)

# --- TASARIM (ALONE RENK PALETİ) ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #E2E2E0; }}
    [data-testid="stSidebar"] {{ background-color: #0E2931 !important; }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1 {{ color: #E2E2E0 !important; }}
    .fee-badge {{
        background-color: #2B7574; color: white; padding: 15px; border-radius: 10px;
        border-left: 5px solid #861211; box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-top: 20px; font-size: 0.9rem;
    }}
    div[data-testid="stExpander"], .stDataFrame, .stTabs {{
        background-color: white !important; border-radius: 12px !important;
        padding: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
    }}
    .product-card {{
        background-color: white; padding: 15px; border-radius: 12px;
        border: 1px solid #eee; text-align: center; margin-bottom: 20px;
    }}
    div.stButton > button {{ background-color: #861211 !important; color: white !important; font-weight: bold !important; width: 100%; }}
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
        return 34.8, 2650.0, 31.0

dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()

if 'urunler' not in st.session_state:
    st.session_state.urunler = verileri_yukle()

# --- SIDEBAR: YÖNETİM PANELİ ---
with st.sidebar:
    st.title("Yönetim Paneli")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru), step=0.01)
    gr_iscilik_usd = st.number_input("🛠️ Gram Başı İşçilik ($)", value=1.0, step=0.1)
    
    # BÖLGE VE KARGO AYARI
    bolge = st.selectbox("Teslimat Bölgesi", ["Amerika", "Avrupa (Belçika vb.)"])
    if bolge == "Amerika":
        kargo_maliyeti = st.number_input("🚚 Kargo Ücreti (TL)", value=400.0)
    else:
        kargo_maliyeti = st.number_input("🚚 Kargo Ücreti (TL)", value=850.0)
        
    indirim_oran = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0)
    
    toplam_komisyon_orani = 0.1692 # Faturandaki standart KDV dahil kesinti %16.92

    st.markdown(f"""
        <div class="fee-badge">
            <b>🛡️ Etsy Kesintileri (Net)</b><br>
            • Komisyonlar + KDV: %{toplam_komisyon_orani*100:.2f}<br>
            • İndirimin: %{indirim_oran}<br>
            <b>TOPLAM YÜK: %{toplam_komisyon_orani*100 + indirim_oran:.2f}</b><br>
            <small>*+ 0.20$ Listeleme & 3.60₺ İşlem</small>
        </div>
    """, unsafe_allow_html=True)

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Yönetim Paneli")
tab1, tab2 = st.tabs(["➕ Ürün Ekleme", "📊 Fiyat Çizelgesi"])

with tab1:
    st.subheader("Yeni Ürün Tanımla")
    c1, c2 = st.columns([1, 1])
    with c1:
        u_ad = st.text_input("Ürün Adı / SKU")
        u_maden = st.selectbox("Maden Türü", ["Gümüş", "Altın"])
        u_gr = st.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
        u_kar = st.number_input("Net Kar Hedefi (TL)", value=2500.0)
    with c2:
        uploaded_file = st.file_uploader("Ürün Görseli Seç", type=['jpg', 'png', 'jpeg'])
        if uploaded_file:
            st.image(uploaded_file, width=150)

    if st.button("Ürünü Portföye Ekle"):
        if u_ad:
            img_base64 = image_to_base64(uploaded_file)
            st.session_state.urunler.append({
                "Ürün": u_ad, "Maden": u_maden, "Gr": u_gr, 
                "Hedef Kar": u_kar, "GörselData": img_base64
            })
            verileri_kaydet(st.session_state.urunler)
            st.success(f"{u_ad} kaydedildi!")
        else:
            st.error("Ürün adı giriniz.")

with tab2:
    if st.session_state.urunler:
        df = pd.DataFrame(st.session_state.urunler)
        
        def hesapla(row):
            ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
            maden_tl = (ons / 31.1035) * row['Gr'] * kur
            iscilik_tl = row['Gr'] * gr_iscilik_usd * kur
            maliyet_toplam = maden_tl + iscilik_tl + kargo_maliyeti
            
            sabitler = (0.20 * kur) + 3.60 
            payda = 1 - (toplam_komisyon_orani + (indirim_oran/100))
            fiyat = (maliyet_toplam + row['Hedef Kar'] + sabitler) / payda
            return round(fiyat, 2)

        st.subheader(f"Portföy Analizi ({bolge})")
        cols = st.columns(4)
        
        for idx, row in df.iterrows():
            fiyat_tl = hesapla(row)
            fiyat_usd = round(fiyat_tl / kur, 2)
            img_src = f"data:image/png;base64,{row['GörselData']}" if pd.notna(row['GörselData']) else "https://img.icons8.com/fluency/96/diamond.png"
            
            with cols[idx % 4]:
                st.markdown(f"""
                <div class="product-card">
                    <img src="{img_src}" style="width:100%; height:150px; object-fit:cover; border-radius:8px;">
                    <h4 style="margin:10px 0 5px 0;">{row['Ürün']}</h4>
                    <p style="color:#861211; font-weight:bold; margin:0; font-size:1.1rem;">{fiyat_tl} ₺</p>
                    <p style="color:#2B7574; margin:0;">$ {fiyat_usd}</p>
                    <hr style="margin:8px 0;">
                    <small>Hedef Kar: {row['Hedef Kar']} ₺</small><br>
                    <small>Kargo: {kargo_maliyeti} ₺</small>
                </div>
                """, unsafe_allow_html=True)
        
        if st.button("🗑️ Portföyü Temizle"):
            st.session_state.urunler = []
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            st.rerun()
    else:
        st.info("Ürün eklemediniz.")
