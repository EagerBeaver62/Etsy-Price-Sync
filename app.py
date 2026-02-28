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

# --- YARDIMCI FONKSİYONLAR (GÜNCELLENDİ) ---
def image_to_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            # Resmi aç ve RGB moduna çevir (Şeffaf PNG'lerdeki JPEG hatasını çözer)
            img = Image.open(uploaded_file).convert("RGB")
            
            # Boyutu optimize et (Hücre limitleri için max 400px)
            img.thumbnail((400, 400)) 
            
            buffered = BytesIO()
            # Optimize edilerek kaydet
            img.save(buffered, format="JPEG", quality=75, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception as e:
            st.error(f"Görsel işlenirken hata oluştu: {e}")
            return ""
    return ""

def safe_float(value, default=0.0):
    try:
        if value is None or value == "": return default
        return float(str(value).replace(",", "."))
    except:
        return default

# --- VERİLERİ ÇEK ---
data = sheet.get_all_records()
df = pd.DataFrame(data)

if not df.empty:
    df = df[df['Ürün'].astype(str).str.strip() != ""]

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Fiyat Ayarları")
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=43.76, step=0.01)
    
    st.markdown("### 🥈 Gümüş Ayarları")
    gumus_gram_usd = st.number_input("Gümüş Gram ($)", value=1.05, format="%.3f")
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50)
    
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

            # --- HESAPLAMA ---
            komisyon = 0.17 + (indirim_yuzde / 100)
            g_maliyet_tl = ((gr * (gumus_gram_usd + iscilik_gumus)) * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_maliyet_tl + kar) / (1 - komisyon)
            
            a_maliyet_tl = ((gr * 1.35 * ((altin_has_gram_usd * 0.585) + iscilik_altin)) * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_maliyet_tl + (kar * 1.5)) / (1 - komisyon)

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="border:1px solid #e6e9ef; border-radius:15px; padding:15px; background:white; text-align:center; margin-bottom:20px;">
                    <img src="data:image/jpeg;base64,{img_data}" style="width:100%; height:180px; object-fit:contain; border-radius:10px;">
                    <h4 style="margin:10px 0; font-size:14px; height:40px;">{row['Ürün']}</h4>
                    <div style="background:#f1f8f6; padding:8px; border-radius:8px; margin-bottom:5px;">
                        <span style="color:#2ecc71; font-weight:bold; font-size:18px;">{fiyat_gumus:,.0f} ₺</span><br><small>🥈 Gümüş</small>
                    </div>
                    <div style="background:#fffcf0; padding:8px; border-radius:8px;">
                        <span style="color:#f39c12; font-weight:bold; font-size:18px;">{fiyat_altin:,.0f} ₺</span><br><small>🟡 14K Altın</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                if c1.button("✏️", key=f"ed_{idx}"):
                    st.session_state[f"edit_{idx}"] = True
                if c2.button("🗑️", key=f"del_{idx}"):
                    sheet.delete_rows(row_idx)
                    st.rerun()
                
                if st.session_state.get(f"edit_{idx}"):
                    with st.form(f"form_{idx}"):
                        new_ad = st.text_input("Ad", value=row['Ürün'])
                        new_gr = st.number_input("Gram", value=gr)
                        new_kar = st.number_input("Kar", value=kar)
                        new_mine = st.number_input("Mine", value=mine)
                        if st.form_submit_button("Güncelle"):
                            updated_vals = [new_ad, row['Maden'], new_gr, new_kar, img_data, row['Kategori'], kaplama, lazer, new_mine]
                            sheet.update(f"A{row_idx}:I{row_idx}", [updated_vals])
                            st.session_state[f"edit_{idx}"] = False
                            st.rerun()

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_urun", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı")
            u_gr = st.number_input("Gümüş Gram", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=3000)
        with c2:
            u_mine = st.number_input("Mine Bedeli (TL)", value=0)
            u_kap = st.number_input("Kaplama Bedeli (TL)", value=0)
            u_img = st.file_uploader("Görsel (JPG/PNG)", type=['jpg','png','jpeg'])
        
        if st.form_submit_button("➕ Listeye Ekle"):
            if u_ad and u_img:
                img_b64 = image_to_base64(u_img)
                all_names = sheet.col_values(1)
                next_row = len(all_names) + 1
                yeni_row = [u_ad, "Gümüş", u_gr, u_kar, img_b64, "Yüzük", u_kap, 0, u_mine]
                sheet.update(f"A{next_row}:I{next_row}", [yeni_row])
                st.success("Eklendi!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Ad ve Görsel zorunludur!")
