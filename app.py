import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="CRIPP Jewelry Panel", layout="wide")

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    # Secrets kısmındaki 'gsheets' anahtarını kullanır
    creds = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scope)
    return gspread.authorize(creds)

client = get_gspread_client()
# E-tablo ismin "Etsy Price Sync" olarak ayarlı
sheet = client.open("Etsy Price Sync").get_worksheet(0)

# --- YARDIMCI FONKSİYONLAR ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        # Görseli küçülterek Sheets limitlerine takılmamasını sağlarız
        img.thumbnail((400, 400))
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode()
    return ""

def safe_float(value, default=0.0):
    try:
        if value is None or value == "": return default
        return float(str(value).replace(",", "."))
    except:
        return default

# --- VERİ ÇEKME ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

# Boş satırları temizle
if not df.empty:
    df = df[df['Ürün'].astype(str).str.strip() != ""]

# --- SIDEBAR (AYARLAR) ---
with st.sidebar:
    st.title("💎 Ayarlar")
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=43.76, step=0.01)
    
    st.markdown("### 🥈 Gümüş Parametreleri")
    gumus_ons_usd = st.number_input("Gümüş Gram Fiyatı ($)", value=1.05, step=0.01)
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50, step=0.01)
    
    st.markdown("### 🟡 Altın (14K) Parametreleri")
    altin_has_gram_usd = st.number_input("Has Altın Gram Fiyatı ($)", value=85.00, step=0.1)
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.00, step=0.1)
    
    st.markdown("---")
    kargo_tl = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)

# --- ANA PANEL ---
st.title("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

with t1:
    search = st.text_input("🔍 Ürün ismi ile ara...")
    
    if not df.empty:
        # Arama filtresi
        f_df = df[df['Ürün'].str.contains(search, case=False, na=False)] if search else df
        
        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            # Google Sheet satır numarası (Header + index)
            row_idx = int(row['index']) + 2
            
            # Verileri güvenli çek
            gr = safe_float(row.get('Gr'))
            kar = safe_float(row.get('Hedef Kar'))
            kaplama = safe_float(row.get('KaplamaTL'))
            lazer = safe_float(row.get('LazerTL'))
            mine = safe_float(row.get('MineTL'))
            img_data = row.get('GörselData', '')

            # --- HESAPLAMA ---
            komisyon_orani = 0.17 + (indirim_yuzde / 100)
            
            # Gümüş Fiyat
            g_maliyet_usd = gr * (gumus_ons_usd + iscilik_gumus)
            g_toplam_tl = (g_maliyet_usd * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_toplam_tl + kar) / (1 - komisyon_orani)
            
            # Altın Fiyat (14K)
            a_gr_tahmin = gr * 1.35
            a_maliyet_usd = a_gr_tahmin * ((altin_has_gram_usd * 0.585) + iscilik_altin)
            a_toplam_tl = (a_maliyet_usd * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_toplam_tl + (kar * 1.5)) / (1 - komisyon_orani)

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="border:1px solid #f0f2f6; border-radius:15px; padding:15px; background:white; text-align:center; margin-bottom:10px;">
                    <img src="data:image/jpeg;base64,{img_data}" style="width:100%; height:180px; object-fit:contain; border-radius:10px;">
                    <h4 style="margin:10px 0; font-size:14px; height:40px; overflow:hidden;">{row['Ürün']}</h4>
                    <div style="background:#f8f9fa; padding:8px; border-radius:8px; margin-bottom:5px;">
                        <small>🥈 Gümüş</small><br><b style="color:#2ecc71; font-size:18px;">{fiyat_gumus:,.0f} ₺</b>
                    </div>
                    <div style="background:#fff9e6; padding:8px; border-radius:8px;">
                        <small>🟡 14K Altın</small><br><b style="color:#f39c12; font-size:18px;">{fiyat_altin:,.0f} ₺</b>
                    </div>
                    <p style="font-size:10px; color:gray; margin-top:5px;">⚖️ {gr}gr | 🎯 {kar}₺ Kar | 🎨 {mine}₺ Mine</p>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("✏️ Düzenle", key=f"edit_{idx}"):
                    st.session_state[f"active_edit"] = idx
                
                if c2.button("🗑️ Sil", key=f"del_{idx}"):
                    sheet.delete_rows(row_idx)
                    st.success("Ürün Silindi!")
                    time.sleep(1)
                    st.rerun()

                # Düzenleme Formu
                if st.session_state.get("active_edit") == idx:
                    with st.form(f"form_edit_{idx}"):
                        new_ad = st.text_input("Ürün Adı", value=row['Ürün'])
                        new_gr = st.number_input("Gram", value=gr)
                        new_kar = st.number_input("Hedef Kar", value=kar)
                        new_mine = st.number_input("Mine (TL)", value=mine)
                        
                        if st.form_submit_button("💾 Güncelle"):
                            # A'dan I'ya kadar olan hücreleri güncelle (9 sütun)
                            # Ürün, Maden, Gr, Hedef Kar, GörselData, Kategori, KaplamaTL, LazerTL, MineTL
                            updated_row = [new_ad, row['Maden'], new_gr, new_kar, img_data, row['Kategori'], kaplama, lazer, new_mine]
                            sheet.update(f"A{row_idx}:I{row_idx}", [updated_row])
                            st.session_state["active_edit"] = None
                            st.rerun()

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_urun_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            u_ad = st.text_input("Ürün Adı")
            u_gr = st.number_input("Gümüş Ağırlığı (Gr)", value=0.0)
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe"])
        with col_b:
            u_kar = st.number_input("Hedef Kar (TL)", value=3000)
            u_mine = st.number_input("Mine Bedeli (TL)", value=0)
            u_kaplama = st.number_input("Kaplama Bedeli (TL)", value=0)
        
        u_file = st.file_uploader("Görsel Yükle", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("➕ Listeye Ekle"):
            if u_ad:
                img_b64 = image_to_base64(u_file)
                # Güvenli ekleme: A sütunundaki son dolu satırı bul
                current_rows = sheet.col_values(1)
                next_row = len(current_rows) + 1
                
                # Yeni veri satırı (I sütununa kadar - MineTL dahil)
                new_data = [u_ad, "Gümüş", u_gr, u_kar, img_b64, u_kat, u_kaplama, 0, u_mine]
                
                sheet.update(f"A{next_row}:I{next_row}", [new_data])
                st.success(f"{u_ad} başarıyla eklendi!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Ürün adı boş bırakılamaz!")
