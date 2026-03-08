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
    try:
        creds = Credentials.from_service_account_info(st.secrets["gsheets"], scopes=scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error("Google Sheets bağlantı hatası! Lütfen Secrets kısmını kontrol edin.")
        st.stop()

client = get_gspread_client()
sheet = client.open("Etsy Price Sync").get_worksheet(0)

# --- YARDIMCI FONKSİYONLAR ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file).convert("RGB")
            img.thumbnail((400, 400)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=75, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            return ""
    return ""

def safe_float(value, default=0.0):
    """Hem virgülü hem noktayı hatasız sayıya çevirir"""
    try:
        if value is None or value == "": return default
        # Boşlukları temizle, virgülü noktaya çevir
        val_str = str(value).strip().replace(",", ".")
        return float(val_str)
    except:
        return default

# --- POP-UP DÜZENLEME MODALI ---
@st.dialog("Ürün Bilgilerini Düzenle")
def edit_product_modal(row_data, row_idx):
    with st.form(f"modal_form_{row_idx}"):
        new_ad = st.text_input("Ürün Adı", value=row_data['Ürün'])
        c1, c2 = st.columns(2)
        with c1:
            # KRİTİK DEĞİŞİKLİK: text_input kullanıldı, artı/eksi butonları olmayacak.
            new_gr_str = st.text_input("Gram (Örn: 5.7 veya 5,7)", value=str(row_data.get('Gr')).replace(".", ","))
            new_kar = st.number_input("Hedef Kar (TL)", value=safe_float(row_data.get('Hedef Kar')))
            new_mine = st.number_input("Mine Bedeli (TL)", value=safe_float(row_data.get('MineTL')))
        with c2:
            new_kaplama = st.number_input("Kaplama Bedeli (TL)", value=safe_float(row_data.get('KaplamaTL')))
            new_lazer = st.number_input("Lazer Bedeli (TL)", value=safe_float(row_data.get('LazerTL')))
            new_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe"], 
                                 index=["Yüzük", "Kolye", "Bileklik", "Küpe"].index(row_data.get('Kategori', 'Yüzük')))
        
        if st.form_submit_button("✅ Değişiklikleri Kaydet"):
            updated_gr = safe_float(new_gr_str)
            updated_row = [
                new_ad, row_data['Maden'], updated_gr, new_kar, 
                row_data['GörselData'], new_kat, new_kaplama, new_lazer, new_mine
            ]
            sheet.update(f"A{row_idx}:I{row_idx}", [updated_row])
            st.success(f"Kaydedildi! Yeni Gram: {updated_gr}")
            time.sleep(0.5)
            st.rerun()

# --- VERİLERİ ÇEK ---
data = sheet.get_all_records()
df = pd.DataFrame(data)
if not df.empty:
    df = df[df['Ürün'].astype(str).str.strip() != ""]

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Fiyat Ayarları")
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=44.07, step=0.01)
    st.markdown("### 🥈 Gümüş Ayarları")
    gumus_gram_tl = st.number_input("Gümüş Has Gram (TL)", value=125.60, step=0.10) 
    iscilik_gumus_usd = st.number_input("Gümüş İşçilik ($/gr)", value=1.50, step=0.10)
    st.markdown("### 🟡 14K Altın Ayarları")
    altin_has_gram_usd = st.number_input("Has Altın Gram ($)", value=85.00)
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.00)
    st.markdown("---")
    kargo_tl = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)

# --- ANA EKRAN ---
st.title("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

with t1:
    search = st.text_input("🔍 Ürün ara...")
    if not df.empty:
        f_df = df[df['Ürün'].str.contains(search, case=False, na=False)] if search else df
        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            row_idx = int(row['index']) + 2
            gr = safe_float(row.get('Gr'))
            kar = safe_float(row.get('Hedef Kar'))
            kaplama = safe_float(row.get('KaplamaTL'))
            lazer = safe_float(row.get('LazerTL'))
            mine = safe_float(row.get('MineTL'))
            img_data = row.get('GörselData', '')

            komisyon = 0.17 + (indirim_yuzde / 100)
            g_maliyet = (gr * gumus_gram_tl) + (gr * iscilik_gumus_usd * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_maliyet + kar) / (1 - komisyon)
            
            a_maliyet = ((gr * 1.35 * ((altin_has_gram_usd * 0.585) + iscilik_altin)) * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_maliyet + (kar * 1.5)) / (1 - komisyon)

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="border:1px solid #eee; border-radius:15px; padding:15px; background:white; text-align:center; margin-bottom:10px;">
                    <img src="data:image/jpeg;base64,{img_data}" style="width:100%; height:180px; object-fit:contain;">
                    <h4 style="font-size:14px;">{row['Ürün']}</h4>
                    <div style="background:#f1f8f6; padding:5px; border-radius:8px;"><b>{fiyat_gumus:,.0f} ₺</b><br><small>Gümüş</small></div>
                    <div style="font-size:11px; color:gray; margin-top:5px;">⚖️ {gr} gr</div>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                if c1.button("✏️ Düzenle", key=f"ed_{idx}"): edit_product_modal(row, row_idx)
                if c2.button("🗑️ Sil", key=f"de_{idx}"): 
                    sheet.delete_rows(row_idx)
                    st.rerun()

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_urun"):
        u_ad = st.text_input("Ürün Adı")
        u_gr_str = st.text_input("Gram (Örn: 5.7)") # Yeni üründe de metin kutusu
        u_kar = st.number_input("Hedef Kar (TL)", value=3000)
        u_img = st.file_uploader("Görsel Seç", type=['jpg','png','jpeg'])
        if st.form_submit_button("Sisteme Kaydet"):
            if u_ad and u_img:
                u_gr = safe_float(u_gr_str)
                img_b64 = image_to_base64(u_img)
                sheet.append_row([u_ad, "Gümüş", u_gr, u_kar, img_b64, "Yüzük", 0, 0, 0])
                st.success("Kaydedildi!")
                time.sleep(1)
                st.rerun()
