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
    }
    input, select {
        border-radius: 8px !important;
    }
    div.stButton > button {
        background-color: #3498db !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold;
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
        return 34.5, 2650.0, 31.5

dolar_kuru, ons_altin, ons_gumus = piyasa_verileri()

if 'urunler' not in st.session_state:
    st.session_state.urunler = []

# --- SOL PANEL (SIDEBAR) - AYARLAR ---
with st.sidebar:
    logo_dosyasi = "logo.png"
    if os.path.exists(logo_dosyasi):
         st.image(logo_dosyasi, use_column_width=True)
    else:
         st.image("https://img.icons8.com/fluency/96/diamond.png", width=80)
         
    st.title("Yönetim Paneli")
    st.markdown("---")
    
    # KENDİNİZ BELİRLEYEBİLECEĞİNİZ ALANLAR
    kur = st.number_input("💵 Dolar Kuru (TL)", value=float(dolar_kuru), step=0.01)
    
    # İSTEDİĞİNİZ GRAM BAŞI İŞÇİLİK AYARI BURADA:
    gr_iscilik_usd = st.number_input("🛠️ Gram Başı İşçilik ($)", value=1.0, step=0.1, help="Her 1 gram için eklenecek dolar bazlı işçilik")
    
    komisyon = st.number_input("📈 Etsy Kesintisi (%)", value=20.0) / 100
    indirim = st.number_input("🏷️ Mağaza İndirimi (%)", value=10.0) / 100
    kargo = st.number_input("🚚 Kargo Ücreti (TL)", value=400.0)
    listing_fee = 0.20 * kur

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyatlandırma Paneli")
st.markdown(f"""
    <div style='background-color: white; padding: 15px; border-radius: 10px; border: 1px solid #eee; color: #2c3e50;'>
        <b>Altın Ons:</b> ${ons_altin:.2f} | <b>Gümüş Ons:</b> ${ons_gumus:.2f} | <b>İşçilik Oranı:</b> {gr_iscilik_usd}$/gr
    </div>
    """, unsafe_allow_html=True)
st.write("")

# Ürün Ekleme Paneli
with st.expander("➕ Yeni Ürün Kaydet", expanded=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        u_ad = st.text_input("Ürün Adı")
        u_kat = st.selectbox("Kategori", ["Kolye", "Yüzük", "Küpe", "Bileklik", "Set"])
    with c2:
        u_maden = st.selectbox("Maden Türü", ["Gümüş", "Altın"])
        u_gr = st.number_input("Ağırlık (Gram)", min_value=0.1, step=0.1)
    with c3:
        u_ek_iscilik = st.number_input("Ekstra Sabit İşçilik (TL)", value=0.0, help="Varsa taş/kaplama gibi ekstra TL masraf")
        u_kar = st.number_input("Net Kar Hedefi (TL)", value=500.0)
    
    if st.button("Listeye Ekle"):
        if u_ad:
            st.session_state.urunler.append({
                "Ürün": u_ad, "Kategori": u_kat, "Maden": u_maden,
                "Gr": u_gr, "Ek İşçilik": u_ek_iscilik, "Hedef Kar": u_kar
            })
            st.rerun()

# --- TABLO VE HESAPLAMA ---
if st.session_state.urunler:
    df = pd.DataFrame(st.session_state.urunler)
    
    def hesapla(row):
        # Maden Maliyeti
        ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
        maden_tl = (ons / 31.1035) * row['Gr'] * kur
        
        # İşçilik: (Gram x Sol tarafta belirlediğin dolar) + Ekstra Sabit TL
        iscilik_tl = (row['Gr'] * gr_iscilik_usd * kur) + row['Ek İşçilik']
        
        # Toplam Maliyet
        maliyet = maden_tl + iscilik_tl + kargo
        
        # Satış Fiyatı
        payda = 1 - (komisyon + indirim)
        fiyat = (maliyet + row['Hedef Kar'] + listing_fee) / payda
        return round(fiyat, 2)

    df['GÜNCEL FİYAT (TL)'] = df.apply(hesapla, axis=1)
    df['DOLAR FİYATI ($)'] = (df['GÜNCEL FİYAT (TL)'] / kur).round(2)
    
    st.subheader("📊 Fiyat Listesi")
    st.dataframe(df, use_container_width=True)
    
    if st.button("🗑️ Listeyi Sıfırla"):
        st.session_state.urunler = []
        st.rerun()
else:
    st.info("Sol taraftan ayarları yapıp yukarıdan ürün ekleyerek başlayabilirsiniz.")
