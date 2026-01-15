import streamlit as st
import yfinance as yf

# Sayfa Genişliği ve Tasarımı
st.set_page_config(page_title="Etsy Fiyat Sihirbazı v2", layout="centered")

st.title("💎 Etsy Akıllı Fiyatlandırma Paneli")
st.markdown("Ürün maliyetlerinizi girin, Etsy satış fiyatınızı TL olarak görün.")

# --- 1. VERİ ÇEKME VE KUR AYARLARI ---
@st.cache_data(ttl=3600) # Veriyi saatte bir günceller, hızı artırır
def verileri_getir():
    try:
        dolar_verisi = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin_ons = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus_ons = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        return dolar_verisi, altin_ons, gumus_ons
    except:
        return 34.0, 2050.0, 23.0 # Hata durumunda varsayılan değerler

dolar_kuru, ons_altin, ons_gumus = verileri_getir()

# --- 2. YAN PANEL (SABİT MALİYETLER) ---
with st.sidebar:
    st.header("⚙️ Genel Ayarlar")
    guncel_kur = st.number_input("Dolar Kuru (TL)", value=float(dolar_kuru), step=0.01)
    
    st.subheader("Etsy Giderleri")
    etsy_komisyon = st.number_input("Etsy Kesintileri (%)", value=20.0) / 100
    magaza_indirimi = st.number_input("Mağaza İndirimi (%)", value=10.0) / 100
    listing_fee = 0.20 * guncel_kur # 0.20$ TL karşılığı
    
    st.info(f"Altın Ons: ${ons_altin:.2f}\nGümüş Ons: ${ons_gumus:.2f}")

# --- 3. ÜRÜN GİRDİLERİ ---
st.subheader("📦 Ürün Bilgileri")
col1, col2 = st.columns(2)

with col1:
    maden = st.selectbox("Maden Türü", ["Gümüş", "Altın"])
    agirlik = st.number_input("Ağırlık (Gram)", min_value=0.1, value=5.0)
    iscilik_tl = st.number_input("İşçilik + Diğer Maliyetler (TL)", value=250.0)

with col2:
    kargo_tl = st.number_input("Kargo Maliyeti (TL)", value=350.0)
    hedef_kar_tl = st.number_input("Elde Etmek İstediğin Kar (TL)", value=500.0)

# --- 4. HESAPLAMA MOTORU ---

# Maden Gram Fiyatı Hesaplama (TL)
secilen_ons = ons_altin if maden == "Altın" else ons_gumus
maden_gram_usd = secilen_ons / 31.1035
maden_gram_tl = maden_gram_usd * guncel_kur
toplam_hammadde_tl = maden_gram_tl * agirlik

# Toplam Üretim + Kargo Maliyeti
toplam_maliyet_tl = toplam_hammadde_tl + iscilik_tl + kargo_tl

# Formül: (Maliyet + Kar + Listing) / (1 - (Komisyon + İndirim))
# İndirim oranını da kesinti gibi düşünüyoruz çünkü indirimli fiyat üzerinden komisyon ödenir.
payda = 1 - (etsy_komisyon + magaza_indirimi)
if payda <= 0:
    st.error("Kesinti ve indirim oranları çok yüksek! Lütfen ayarları kontrol edin.")
    satis_fiyati_tl = 0
else:
    satis_fiyati_tl = (toplam_maliyet_tl + hedef_kar_tl + listing_fee) / payda

# --- 5. SONUÇLARIN GÖSTERİLMESİ ---
st.markdown("---")
res_col1, res_col2 = st.columns(2)

with res_col1:
    st.metric("Etikete Yazılacak Fiyat (TL)", f"{satis_fiyati_tl:.2f} ₺")
    st.caption(f"Dolar Karşılığı: ${(satis_fiyati_tl / guncel_kur):.2f}")

with res_col2:
    st.metric("Toplam Maliyetin", f"{toplam_maliyet_tl:.2f} ₺")
    st.write(f"Maden (TL): {toplam_hammadde_tl:.2f}")

# Detaylı Analiz Paneli
with st.expander("Detaylı Maliyet Analizini Gör"):
    st.write(f"- **Maden Gram Fiyatı:** {maden_gram_tl:.2f} ₺")
    st.write(f"- **Etsy Kesintisi (TL):** {(satis_fiyati_tl * etsy_komisyon):.2f} ₺")
    st.write(f"- **Müşteriye Yapılan İndirim (TL):** {(satis_fiyati_tl * magaza_indirimi):.2f} ₺")
    st.write(f"- **Net Cebine Kalacak Kar:** {hedef_kar_tl:.2f} ₺")
