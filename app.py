import streamlit as st
import yfinance as yf
import pandas as pd

# Sayfa Ayarları
st.set_page_config(page_title="Etsy Jewelry Panel", layout="wide")

# --- CUSTOM CSS (Şık Tasarım ve Degradeler) ---
st.markdown("""
    <style>
    /* Ana Arka Plan */
    .stApp {
        background: linear-gradient(135deg, #1a1c2c 0%, #4a192c 100%);
        color: white;
    }
    
    /* Saydam Kart Efekti (Glassmorphism) */
    div[data-testid="stExpander"], div.stButton > button, .stDataFrame {
        background: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border-radius: 15px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }

    /* Başlık Renkleri */
    h1, h2, h3, p {
        color: #ffffff !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }

    /* Giriş Alanları Özelleştirme */
    .stNumberInput input, .stTextInput input, .stSelectbox div {
        background-color: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 10px !important;
    }

    /* Buton Tasarımı */
    div.stButton > button {
        background: linear-gradient(90deg, #ff4b2b 0%, #ff416c 100%) !important;
        border: none !important;
        font-weight: bold !important;
        padding: 0.5rem 2rem !important;
    }
    
    /* Sidebar (Yan Panel) Saydamlık */
    section[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(15px);
    }
    </style>
    """, unsafe_allow_html=True)

# --- PİYASA VERİLERİ (OTOMATİK) ---
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

# --- VERİTABANI SİMÜLASYONU ---
if 'urunler' not in st.session_state:
    st.session_state.urunler = []

# --- YAN PANEL ---
with st.sidebar:
    st.title("⚙️ Ayarlar")
    kur = st.number_input("Dolar Kuru (₺)", value=float(dolar_kuru))
    komisyon = st.number_input("Etsy Kesintisi (%)", value=20.0) / 100
    indirim = st.number_input("Kampanya İndirimi (%)", value=10.0) / 100
    kargo = st.number_input("Kargo Ücreti (₺)", value=400.0)
    listing_fee = 0.20 * kur
    
    st.markdown("---")
    st.write(f"✨ **Canlı Ons Altın:** ${ons_altin:.2f}")
    st.write(f"✨ **Canlı Ons Gümüş:** ${ons_gumus:.2f}")

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Ürün Portföyü")
st.write("Fiyatlar anlık maden kurlarına göre otomatik güncellenir.")

# Ürün Ekleme Kartı
with st.expander("➕ Sisteme Yeni Ürün Kaydet"):
    c1, c2, c3 = st.columns(3)
    u_ad = c1.text_input("Ürün Adı / Kodu")
    u_kat = c1.selectbox("Kategori", ["Kolye", "Yüzük", "Küpe", "Bileklik", "Set"])
    u_maden = c2.selectbox("Maden Türü", ["Gümüş", "Altın"])
    u_gr = c2.number_input("Maden Ağırlığı (Gr)", min_value=0.1, step=0.1)
    u_iscilik = c3.number_input("İşçilik Maliyeti (₺)", min_value=0.0)
    u_kar = c3.number_input("Net Kar Hedefin (₺)", min_value=0.0)
    
    if st.button("Ürünü Listeye Ekle"):
        if u_ad:
            yeni_urun = {
                "Ürün": u_ad, "Kategori": u_kat, "Maden": u_maden,
                "Gr": u_gr, "İşçilik": u_iscilik, "Hedef Kar": u_kar
            }
            st.session_state.urunler.append(yeni_urun)
            st.success(f"{u_ad} başarıyla kaydedildi!")
        else:
            st.warning("Lütfen bir ürün adı girin.")

# --- LİSTELEME VE HESAPLAMA ---
if st.session_state.urunler:
    df = pd.DataFrame(st.session_state.urunler)
    
    def fiyat_hesapla(row):
        ons = ons_altin if row['Maden'] == "Altın" else ons_gumus
        maden_maliyeti = (ons / 31.1035) * row['Gr'] * kur
        toplam_maliyet = maden_maliyeti + row['İşçilik'] + kargo
        payda = 1 - (komisyon + indirim)
        satis_tl = (toplam_maliyet + row['Hedef Kar'] + listing_fee) / payda
        return round(satis_tl, 2)

    df['Güncel Etsy Fiyatı (₺)'] = df.apply(fiyat_hesapla, axis=1)
    df['Dolar Karşılığı ($)'] = (df['Güncel Etsy Fiyatı (₺)'] / kur).round(2)
    
    st.subheader("📊 Fiyat Takip Çizelgesi")
    st.dataframe(df, use_container_width=True)
    
    # Veriyi İndirme Butonu
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Listeyi Excel (CSV) Olarak İndir", csv, "fiyat_listesi.csv", "text/csv")
    
    if st.button("🗑️ Tüm Listeyi Sıfırla"):
        st.session_state.urunler = []
        st.rerun()
else:
    st.info("Henüz ürün eklemediniz. Başlamak için yukarıdaki 'Yeni Ürün Kaydet' bölümünü kullanın.")
