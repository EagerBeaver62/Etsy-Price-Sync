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
            st.error(f"Görsel işlenirken hata: {e}")
            return ""
    return ""

# GÜNCELLENEN FONKSİYYON: Virgül ve Nokta karmaşasını çözer
def safe_float(value, default=0.0):
    try:
        if value is None or value == "": return default
        # Virgülü noktaya çevirerek sayıya dönüştür
        val_str = str(value).replace(",", ".")
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
            # step=0.01 ekleyerek ondalıklı girişi zorunlu kıldık
            new_gr = st.number_input("Gram", value=safe_float(row_data.get('Gr')), step=0.01, format="%.2f")
            new_kar = st.number_input("Hedef Kar (TL)", value=safe_float(row_data.get('Hedef Kar')), step=10.0)
            new_mine = st.number_input("Mine Bedeli (TL)", value=safe_float(row_data.get('MineTL')), step=10.0)
        with c2:
            new_kaplama = st.number_input("Kaplama Bedeli (TL)", value=safe_float(row_data.get('KaplamaTL')), step=10.0)
            new_lazer = st.number_input("Lazer Bedeli (TL)", value=safe_float(row_data.get('LazerTL')), step=10.0)
            new_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe"], 
                                 index=["Yüzük", "Kolye", "Bileklik", "Küpe"].index(row_data.get('Kategori', 'Yüzük')))
        
        if st.form_submit_button("✅ Değişiklikleri Kaydet"):
            updated_row = [
                new_ad, row_data['Maden'], new_gr, new_kar, 
                row_data['GörselData'], new_kat, new_kaplama, new_lazer, new_mine
            ]
            sheet.update(f"A{row_idx}:I{row_idx}", [updated_row])
            st.success("Ürün güncellendi!")
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
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=44.07, step=0.01, format="%.2f")
    
    st.markdown("### 🥈 Gümüş Ayarları")
    gumus_gram_tl = st.number_input("Gümüş Has Gram (TL)", value=125.60, step=0.10, format="%.2f") 
    iscilik_gumus_usd = st.number_input("Gümüş İşçilik ($/gr)", value=1.50, step=0.10, format="%.2f")
    
    st.markdown("### 🟡 14K Altın Ayarları")
    altin_has_gram_usd = st.number_input("Has Altın Gram ($)", value=85.00, step=1.0)
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.00, step=1.0)
    
    st.markdown("---")
    kargo_tl = st.number_input("🚚 Kargo (TL)", value=650.0, step=10.0)
    indirim_yuzde = st.number_input("🏷️ Etsy İndirim (%)", value=15.0, step=1.0)

# --- ANA EKRAN ---
st.title("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

with t1:
    search = st.text_input("🔍 Ürün ismi ile ara...", placeholder="Yüzük, Kolye vb.")
    
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

            # --- HESAPLAMA MOTORU ---
            komisyon = 0.17 + (indirim_yuzde / 100)
            
            g_maliyet_tl = (gr * gumus_gram_tl) + (gr * iscilik_gumus_usd * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_maliyet_tl + kar) / (1 - komisyon)
            
            a_maliyet_tl = ((gr * 1.35 * ((altin_has_gram_usd * 0.585) + iscilik_altin)) * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_maliyet_tl + (kar * 1.5)) / (1 - komisyon)

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="border:1px solid #e6e9ef; border-radius:15px; padding:15px; background:white; text-align:center; margin-bottom:10px;">
                    <img src="data:image/jpeg;base64,{img_data}" style="width:100%; height:180px; object-fit:contain; border-radius:10px;">
                    <h4 style="margin:10px 0; font-size:14px; height:40px;">{row['Ürün']}</h4>
                    <div style="background:#f1f8f6; padding:8px; border-radius:8px; margin-bottom:5px;">
                        <span style="color:#2ecc71; font-weight:bold; font-size:18px;">{fiyat_gumus:,.0f} ₺</span><br><small>🥈 Gümüş</small>
                    </div>
                    <div style="background:#fffcf0; padding:8px; border-radius:8px;">
                        <span style="color:#f39c12; font-weight:bold; font-size:18px;">{fiyat_altin:,.0f} ₺</span><br><small>🟡 14K Altın</small>
                    </div>
                    <div style="font-size:11px; color:#7f8c8d; margin-top:5px;">⚖️ {gr}gr | 🎯 {kar:,.0f}₺ Kar</div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("✏️ Düzenle", key=f"edit_btn_{idx}", use_container_width=True):
                    edit_product_modal(row, row_idx)
                
                if c2.button("🗑️ Sil", key=f"del_btn_{idx}", use_container_width=True):
                    sheet.delete_rows(row_idx)
                    st.rerun()

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_urun_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı")
            u_gr = st.number_input("Gram", value=0.0, step=0.01, format="%.2f")
            u_kar = st.number_input("Hedef Kar (TL)", value=3000, step=100)
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Bileklik", "Küpe"])
        with c2:
            u_mine = st.number_input("Mine Bedeli (TL)", value=0, step=10)
            u_kap = st.number_input("Kaplama Bedeli (TL)", value=0, step=10)
            u_lazer = st.number_input("Lazer Bedeli (TL)", value=0, step=10)
            u_img = st.file_uploader("Ürün Görseli (JPG/PNG)", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("➕ Ürünü Sisteme Kaydet"):
            if u_ad and u_img:
                img_b64 = image_to_base64(u_img)
                all_names = sheet.col_values(1)
                next_row = len(all_names) + 1
                
                yeni_row = [u_ad, "Gümüş", u_gr, u_kar, img_b64, u_kat, u_kap, u_lazer, u_mine]
                sheet.update(f"A{next_row}:I{next_row}", [yeni_row])
                
                st.success(f"{u_ad} başarıyla eklendi!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Lütfen Ürün Adı ve Görsel ekleyin!")
