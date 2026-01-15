import streamlit as st
import yfinance as yf
import pandas as pd
import os

# Sayfa Ayarları
st.set_page_config(page_title="Etsy Profesyonel Dashboard", layout="wide", page_icon="💎")

# --- TASARIM (CSS) ---
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
    /* Badge Tasarımı (Sidebar altındaki bilgi kartı) */
    .fee-badge {{
        background-color: #2B7574;
        color: white;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #861211;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        margin-top: 20px;
        font-size: 0.9rem;
    }}
    /* Tablo ve Kartlar */
    div[data-testid="stExpander"], .stDataFrame, .stTabs {{
        background-color: white !important;
        border-radius: 12px !important;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
    }}
    button[data-baseweb="tab"] {{
        font-size: 18px !important;
        font-weight: bold !important;
    }}
    button[aria-selected="true"] {{
        color: #861211 !important;
        border-bottom-color: #861211 !important;
    }}
    /* Kırmızı Buton */
    div.stButton > button {{
        background-color: #861211 !important;
        color: white !important;
        border-radius: 5px !important;
        font-weight: bold !important;
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

# --- SIDEBAR ---
with st.sidebar:
    st.title("Yönetim Paneli")
    st.markdown("---")
    kur = st.number_input("💵 USD/TRY Kuru", value=float(dolar_kuru), step=0.01)
    gr_iscilik_usd = st.number_input("🛠️ Gram Başı İşçilik ($)", value=1.0, step=0.1)
    kargo = st.number_input("🚚 Kargo Ücreti (TL)", value=400.0)
    indirim_oran = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0)
    
    # Standart Kesinti Sabiti
    toplam_komisyon_orani = 0.1692 # %16.92 (KDV Dahil Net Kesinti)

    # DİKKAT ÇEKİCİ BADGE (EN ALTTA)
    st.markdown(f"""
        <div class="fee-badge">
            <b>🛡️ Standart Etsy Kesintileri</b><br>
            <hr style="margin: 8px 0; border: 0.1px solid rgba(255,255,255,0.2);">
            • Transaction: %7.8 (KDVli)<br>
            • Processing: %7.8 (KDVli)<br>
            • Regulatory: %1.32 (KDVli)<br>
            <b>TOPLAM: %{toplam_komisyon_orani*100:.2f}</b><br>
            <small>*+ 0.20$ Listeleme & 3.60₺ İşlem</small>
        </div>
    """, unsafe_allow_html=True)

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Yönetim Paneli")
tab1, tab2 = st.tabs(["➕ Ürün Ekleme", "📊 Fiyat Çizelgesi"])

# --- TAB 1: ÜRÜN EKLEME ---
with tab1:
    st.subheader("Yeni Ürün Tanımla")
    c1, c2, c3 = st.columns(3)
    u_ad = c1.text_input("Ürün Adı / SKU")
    u_maden = c2.selectbox("Maden Türü", ["Gümüş", "Altın"])
    u_gr = c2.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
    u_kar = c3.number_input("Hedef Kar (TL)", value=500.0)
    
    if st.button("Ürünü Portföye Ekle"):
        if u_ad:
            st.session_state.urunler.append({
                "Ürün": u_ad, "Maden": u_maden, "Gr": u_gr, "Hedef Kar": u_kar
            })
            st.success(f"{u_ad} eklendi!")
        else:
            st.error("Ürün adı giriniz.")

# --- TAB 2: FİYAT LİSTESİ ---
with tab2:
    if st.session_state.urunler:
        df = pd.DataFrame(st.session_state.urunler)
        
        def hesapla(row):
            ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
            maden_tl = (ons / 31.1035) * row['Gr'] * kur
            iscilik_tl = row['Gr'] * gr_iscilik_usd * kur
            maliyet = maden_tl + iscilik_tl + kargo
            sabitler = (0.20 * kur) + 3.60 
            
            # Satış Fiyatı Formülü
            payda = 1 - (toplam_komisyon_orani + (indirim_oran/100))
            fiyat = (maliyet + row['Hedef Kar'] + sabitler) / payda
            
            # Toplam Kesinti Tutarı (TL bazlı gösterim için)
            kesinti_tutari = fiyat * (toplam_komisyon_orani + (indirim_oran/100)) + sabitler
            
            return pd.Series([round(fiyat, 2), round(kesinti_tutari, 2)])

        df[['GÜNCEL SATIŞ FİYATI (TL)', 'TOPLAM KESİNTİ (TL)']] = df.apply(hesapla, axis=1)
        df['DOLAR ($)'] = (df['GÜNCEL SATIŞ FİYATI (TL)'] / kur).round(2)
        
        # Tablo Sütun Düzenleme
        df = df[['Ürün', 'Maden', 'Gr', 'GÜNCEL SATIŞ FİYATI (TL)', 'DOLAR ($)', 'TOPLAM KESİNTİ (TL)', 'Hedef Kar']]
        
        st.subheader("Ürün Portföyü ve Fiyat Analizi")
        st.dataframe(df, use_container_width=True)
        
        st.info(f"💡 Hesaplamada uygulanan toplam kesinti oranı (İndirim Dahil): **%{toplam_komisyon_orani*100 + indirim_oran:.2f}**")
        
        if st.button("🗑️ Portföyü Temizle"):
            st.session_state.urunler = []
            st.rerun()
    else:
        st.info("Ürün eklemediniz.")
