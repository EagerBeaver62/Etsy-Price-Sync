import streamlit as st
import yfinance as yf
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Etsy Profesyonel Fiyat Paneli", layout="wide", page_icon="💎")

# --- ALONE GÖRSELİ RENK PALETİ VE TASARIM ---
st.markdown(f"""
    <style>
    .stApp {{
        background-color: #E2E2E0; /* Arka Plan: Açık Gri/Beyaz */
    }}
    [data-testid="stSidebar"] {{
        background-color: #0E2931 !important; /* Sidebar: Koyu Petrol */
    }}
    [data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label, [data-testid="stSidebar"] h1 {{
        color: #E2E2E0 !important;
    }}
    /* Kart Yapıları */
    div[data-testid="stExpander"], .stDataFrame {{
        background-color: white !important;
        border-radius: 12px !important;
        border-left: 5px solid #2B7574 !important; /* Petrol Yeşili Vurgu */
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
    }}
    h1, h2, h3 {{
        color: #0E2931 !important;
        font-family: 'Playfair Display', serif;
    }}
    /* Buton Tasarımı - Kırmızı Vurgu */
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

# --- SIDEBAR: AYARLAR ---
with st.sidebar:
    st.title("Admin Paneli")
    st.markdown("---")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru), step=0.01)
    
    st.subheader("🛠️ İşçilik Ayarı")
    gr_iscilik_usd = st.number_input("Gram Başı İşçilik ($)", value=1.0, step=0.1)
    
    st.subheader("📈 Standart Kesintiler")
    # %20 KDV dahil standart oranlar
    trans_fee = 6.5 * 1.2  # %7.8
    proc_fee = 6.5 * 1.2   # %7.8
    reg_fee = 1.1 * 1.2    # %1.32
    toplam_komisyon_orani = (trans_fee + proc_fee + reg_fee) / 100
    
    st.info(f"Yasal Kesinti Yükü: %{toplam_komisyon_orani*100:.2f}")
    
    kargo = st.number_input("🚚 Kargo Ücreti (TL)", value=400.0)
    indirim = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0) / 100

# --- ANA EKRAN ---
st.title("Etsy Profesyonel Fiyatlandırma")
st.write(f"Anlık Ons: **Altın:** ${ons_altin:.2f} | **Gümüş:** ${ons_gumus:.2f}")

with st.expander("➕ Yeni Ürün Ekle", expanded=True):
    c1, c2, c3 = st.columns(3)
    u_ad = c1.text_input("Ürün Adı / SKU")
    u_maden = c2.selectbox("Maden Türü", ["Gümüş", "Altın"])
    u_gr = c2.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
    u_kar = c3.number_input("Net Kar Hedefi (TL)", value=500.0)
    
    if st.button("Listeye Kaydet"):
        if u_ad:
            st.session_state.urunler.append({
                "Ürün": u_ad, "Maden": u_maden, "Gr": u_gr, "Hedef Kar": u_kar
            })
            st.rerun()

# --- HESAPLAMA ---
if st.session_state.urunler:
    df = pd.DataFrame(st.session_state.urunler)
    
    def hesapla(row):
        # 1. Maden Maliyeti
        ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
        maden_tl = (ons / 31.1035) * row['Gr'] * kur
        
        # 2. İşçilik Maliyeti (Sadece Gram x Belirlenen $)
        iscilik_tl = row['Gr'] * gr_iscilik_usd * kur
        
        # 3. Toplam Maliyet
        maliyet = maden_tl + iscilik_tl + kargo
        
        # 4. Sabit Ücretler (3 TL İşlem + 0.20$ Listeleme + KDV)
        sabit_ucretler = (0.20 * kur) + 3.60 
        
        # 5. Satış Fiyatı Formülü
        payda = 1 - (toplam_komisyon_orani + indirim)
        fiyat = (maliyet + row['Hedef Kar'] + sabit_ucretler) / payda
        return round(fiyat, 2)

    df['SATIŞ FİYATI (TL)'] = df.apply(hesapla, axis=1)
    df['SATIŞ FİYATI ($)'] = (df['SATIŞ FİYATI (TL)'] / kur).round(2)
    
    st.subheader("📊 Fiyat Çizelgesi")
    st.dataframe(df, use_container_width=True)

    if st.button("🗑️ Listeyi Sıfırla"):
        st.session_state.urunler = []
        st.rerun()
else:
    st.info("Ürün ekleyerek hesaplamaya başlayabilirsiniz.")
