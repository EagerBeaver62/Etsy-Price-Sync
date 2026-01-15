import streamlit as st
import yfinance as yf
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- ALONE GÖRSELİ RENK PALETİ VE TASARIM ---
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #E2E2E0; 
    }}
    [data-testid="stSidebar"] {{
        background-color: #0E2931 !important;
    }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1 {{
        color: #E2E2E0 !important;
    }}
    /* Kart ve Sekme Tasarımı */
    div[data-testid="stExpander"], .stDataFrame, .stTabs {{
        background-color: white !important;
        border-radius: 12px !important;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
    }}
    /* Sekme Başlıkları */
    button[data-baseweb="tab"] {{
        font-size: 18px !important;
        font-weight: bold !important;
        color: #0E2931 !important;
    }}
    button[aria-selected="true"] {{
        color: #861211 !important;
        border-bottom-color: #861211 !important;
    }}
    h1, h2, h3 {{
        color: #0E2931 !important;
        font-family: 'Playfair Display', serif;
    }}
    /* Buton Tasarımı */
    div.stButton > button {{
        background-color: #861211 !important;
        color: white !important;
        border-radius: 5px !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
    }}
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
    st.session_state.urunler = []

# --- SIDEBAR: GENEL AYARLAR ---
with st.sidebar:
    st.title("Yönetim Paneli")
    st.markdown("---")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru), step=0.01)
    gr_iscilik_usd = st.number_input("🛠️ Gram Başı İşçilik ($)", value=1.0, step=0.1)
    kargo = st.number_input("🚚 Kargo Ücreti (TL)", value=400.0)
    indirim = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0) / 100
    
    # Standart Kesinti Oranı (KDV Dahil): %16.92
    toplam_komisyon_orani = 0.1692

# --- ANA EKRAN VE SEKMELER ---
st.title("💎 Etsy Akıllı Yönetim Paneli")

# Sekmeleri oluşturuyoruz
tab1, tab2 = st.tabs(["➕ Ürün Ekleme", "📊 Fiyat Çizelgesi ve Portföy"])

# --- SEKME 1: ÜRÜN EKLEME ---
with tab1:
    st.subheader("Yeni Ürün Tanımla")
    with st.container():
        c1, c2, c3 = st.columns(3)
        u_ad = c1.text_input("Ürün Adı / SKU")
        u_maden = c2.selectbox("Maden Türü", ["Gümüş", "Altın"])
        u_gr = c2.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
        u_kar = c3.number_input("Hedef Kar (TL)", value=500.0)
        
        st.write("")
        if st.button("Ürünü Portföye Ekle"):
            if u_ad:
                st.session_state.urunler.append({
                    "Ürün": u_ad, "Maden": u_maden, "Gr": u_gr, "Hedef Kar": u_kar
                })
                st.success(f"{u_ad} başarıyla eklendi! 'Fiyat Çizelgesi' sekmesinden kontrol edebilirsiniz.")
            else:
                st.error("Lütfen ürün adı giriniz.")

# --- SEKME 2: FİYAT LİSTESİ ---
with tab2:
    if st.session_state.urunler:
        df = pd.DataFrame(st.session_state.urunler)
        
        def hesapla(row):
            # 1. Maden Maliyeti
            ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
            maden_tl = (ons / 31.1035) * row['Gr'] * kur
            # 2. İşçilik
            iscilik_tl = row['Gr'] * gr_iscilik_usd * kur
            # 3. Toplam Maliyet
            maliyet = maden_tl + iscilik_tl + kargo
            # 4. Sabitler (Listeleme 0.20$ + İşlem 3 TL + KDVleri)
            sabit_ucretler = (0.20 * kur) + 3.60 
            # 5. Satış Fiyatı
            payda = 1 - (toplam_komisyon_orani + indirim)
            fiyat = (maliyet + row['Hedef Kar'] + sabit_ucretler) / payda
            return round(fiyat, 2)

        df['GÜNCEL FİYAT (TL)'] = df.apply(hesapla, axis=1)
        df['DOLAR KARŞILIĞI ($)'] = (df['GÜNCEL FİYAT (TL)'] / kur).round(2)
        
        st.subheader("Ürünlerinizin Güncel Satış Fiyatları")
        st.write(f"ℹ️ *Fiyatlar anlık kurlara göre hesaplanmaktadır. (Kur: {kur:.2f} ₺)*")
        
        # Tabloyu göster
        st.dataframe(df, use_container_width=True)
        
        st.write("---")
        if st.button("🗑️ Tüm Portföyü Temizle"):
            st.session_state.urunler = []
            st.rerun()
    else:
        st.info("Henüz ürün eklemediniz. Lütfen 'Ürün Ekleme' sekmesine gidiniz.")
