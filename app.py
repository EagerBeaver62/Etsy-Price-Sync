import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime
import requests
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide")

def safe_float(value):
    try:
        if value is None or str(value).strip() == "": return 0.0
        return float(str(value).replace(',', '.').replace('₺', '').replace('$', '').strip())
    except: return 0.0

def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            img.thumbnail((250, 250)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=85)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Sütun Düzeni: A:Ürün, B:Maden, C:Gr, D:Kar, E:Görsel, F:Kategori, G:Kaplama, H:Lazer, I:Mine
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        data = sh.get_all_records()
        return pd.DataFrame(data), sh
    except Exception as e:
        st.error(f"Bağlantı Hatası: {e}")
        return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR (AYARLAR) ---
with st.sidebar:
    st.title("💎 Ayarlar")
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=43.76, step=0.01)
    
    st.divider()
    st.subheader("🥈 Gümüş Parametreleri")
    # Kullanıcı dostu olması için Gram $/gr üzerinden gidiyoruz
    gumus_gram_usd = st.number_input("Gümüş Gram Fiyatı ($)", value=1.05, format="%.2f", help="Has gümüşün gram dolar fiyatı")
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50)
    
    st.divider()
    st.subheader("🥇 Altın (14K) Parametreleri")
    altin_has_gram_usd = st.number_input("Has Altın Gram Fiyatı ($)", value=85.0, format="%.2f", help="24 ayar has altının gram dolar fiyatı")
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.0)
    
    st.divider()
    kargo_tl = st.number_input("📦 Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)

# --- ANA EKRAN ---
st.title("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

with t1:
    search = st.text_input("🔍 Ürün ismi ile ara...")
    if not df.empty:
        f_df = df[df['Ürün'].str.contains(search, case=False)] if search else df
        
        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            # Google Sheet satırı (Header dahil olduğu için index+2)
            row_idx = int(row.get('index')) + 2
            
            # Değerleri al
            gr = safe_float(row.get('Gr', 0))
            kar = safe_float(row.get('Hedef Kar', 0))
            kaplama = safe_float(row.get('KaplamaTL', 0))
            lazer = safe_float(row.get('LazerTL', 0))
            mine = safe_float(row.get('MineTL', 0))
            
            # --- HESAPLAMA MOTORU ---
            komisyon = 0.17 + (indirim_yuzde / 100)
            
            # 1. Gümüş Fiyatı
            g_maliyet_usd = gr * (gumus_gram_usd + iscilik_gumus)
            g_toplam_tl = (g_maliyet_usd * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_toplam_tl + kar) / (1 - komisyon)
            
            # 2. 14K Altın Fiyatı
            # Önemli: Gümüşten Altına dökümde ağırlık ~1.35 kat artar.
            altin_gr_tahmin = gr * 1.35
            # 14 Ayar has altın oranı: 0.585
            a_maliyet_usd = altin_gr_tahmin * ((altin_has_gram_usd * 0.585) + iscilik_altin)
            a_toplam_tl = (a_maliyet_usd * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_toplam_tl + (kar * 1.5)) / (1 - komisyon)

            with cols[idx % 4]:
                st.markdown(f"""
                <div style="border:1px solid #eee; border-radius:15px; padding:15px; background:white; text-align:center; box-shadow: 2px 2px 10px rgba(0,0,0,0.05);">
                    <img src="data:image/jpeg;base64,{row['GörselData']}" style="width:100%; height:180px; object-fit:contain; border-radius:10px;">
                    <p style="font-weight:bold; margin-top:10px; font-size:14px; min-height:40px;">{row['Ürün']}</p>
                    <div style="background:#f8f9fa; padding:10px; border-radius:10px;">
                        <span style="color:#6c757d; font-size:12px;">🥈 Gümüş</span><br>
                        <span style="font-size:18px; font-weight:bold; color:#27ae60;">{fiyat_gumus:,.0f} ₺</span>
                    </div>
                    <div style="background:#fffcf0; padding:10px; border-radius:10px; margin-top:5px; border:1px solid #ffeaa7;">
                        <span style="color:#d35400; font-size:12px;">🟡 14K Altın</span><br>
                        <span style="font-size:18px; font-weight:bold; color:#e67e22;">{fiyat_altin:,.0f} ₺</span>
                    </div>
                    <div style="font-size:10px; color:gray; margin-top:10px;">
                        ⚖️ {gr}gr | 🎯 Kar: {kar}₺ | 🎨 Mine: {mine}₺
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Butonlar
                c1, c2 = st.columns(2)
                if c1.button("✏️ Düzenle", key=f"ed_{idx}"):
                    st.session_state[f"edit_mode_{idx}"] = True
                if c2.button("🗑️ Sil", key=f"del_{idx}"):
                    sheet.delete_rows(row_idx)
                    st.rerun()
                
                # --- DÜZENLEME FORMU ---
                if st.session_state.get(f"edit_mode_{idx}"):
                    with st.form(f"f_{idx}"):
                        new_ad = st.text_input("Ürün Adı", value=row['Ürün'])
                        new_gr = st.number_input("Gümüş Gram", value=gr)
                        new_kar = st.number_input("Kar (TL)", value=kar)
                        new_mine = st.number_input("Mine Bedeli (TL)", value=mine)
                        new_kap = st.number_input("Kaplama (TL)", value=kaplama)
                        new_laz = st.number_input("Lazer (TL)", value=lazer)
                        
                        if st.form_submit_button("💾 Değişiklikleri Kaydet"):
                            # Tüm satırı güncelle (A:I sütunları)
                            updates = [new_ad, row['Maden'], new_gr, new_kar, row['GörselData'], row['Kategori'], new_kap, new_laz, new_mine]
                            sheet.update(f"A{row_idx}:I{row_idx}", [updates])
                            st.session_state[f"edit_mode_{idx}"] = False
                            st.rerun()

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı")
            u_gr = st.number_input("Gram (Gümüş)", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=3000)
        with c2:
            u_mine = st.number_input("Mine Bedeli (TL)", value=0)
            u_kap = st.number_input("Kaplama (TL)", value=0)
            u_img = st.file_uploader("Ürün Görseli", type=['jpg','png'])
        
        if st.form_submit_button("Listeye Ekle"):
            img_b64 = image_to_base64(u_img)
            # A'dan I'ya kadar veriyi ekle
            sheet.append_row([u_ad, "Gümüş", u_gr, u_kar, img_b64, "Genel", u_kap, 0, u_mine])
            st.success("Ürün eklendi!")
            time.sleep(1)
            st.rerun()
