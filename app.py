import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime
import requests
import json
import time

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry", layout="wide", page_icon="💎")

# --- YARDIMCI FONKSİYONLAR ---
def safe_float(value):
    try:
        if value is None or str(value).strip() == "": return 0.0
        return float(str(value).replace(',', '.').replace('₺', '').replace('$', '').strip())
    except: return 0.0

def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode != "RGB": img = img.convert("RGB")
            img.thumbnail((200, 200)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=80)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- VERİ ÇEKME (HAREM ALTIN) ---
@st.cache_data(ttl=60)
def get_market_data():
    url = "https://www.haremaltin.com/dashboard/ajax/pol"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.post(url, headers=headers, timeout=5)
        d = r.json().get('data', {})
        return {
            'gumus_usd': safe_float(d.get('GUMUSUSD', {}).get('satis')),
            'altin_tl': safe_float(d.get('ALTIN', {}).get('satis')),
            'dolar_tl': safe_float(d.get('USDTRY', {}).get('satis')),
            'altin_ons': safe_float(d.get('ALTINONS', {}).get('satis')),
            'status': 'success'
        }
    except:
        return {'gumus_usd': 31.5, 'altin_tl': 3000, 'dolar_tl': 34.5, 'altin_ons': 2650, 'status': 'fail'}

m_data = get_market_data()

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Tablo Yapısı: Ürün(A), Maden(B), Gr(C), Kar(D), Görsel(E), Kategori(F), Kaplama(G), Lazer(H), Mine(I)
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        return pd.DataFrame(sh.get_all_records()), sh
    except: return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Ayarlar")
    dolar_kuru = st.number_input("💵 Dolar Kuru (TL)", value=m_data['dolar_tl'])
    
    st.subheader("🥈 Gümüş")
    gumus_ons_usd = st.number_input("Gümüş Ons ($)", value=m_data['gumus_usd'])
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50)
    
    st.subheader("🥇 Altın (14K)")
    altin_ons_usd = st.number_input("Altın Ons ($)", value=m_data['altin_ons'])
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.0)
    
    st.divider()
    kargo_tl = st.number_input("🚚 Kargo (TL)", value=650.0)
    indirim = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)

# --- ANA PANEL ---
st.header("Etsy Akıllı Fiyat Paneli")
t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

with t1:
    if not df.empty:
        # Arama ve Filtre
        search = st.text_input("🔍 Ürün ismi ile ara...")
        f_df = df[df['Ürün'].str.contains(search, case=False)] if search else df
        
        cols = st.columns(4)
        for idx, row in f_df.reset_index().iterrows():
            row_idx = int(row.get('index', 0)) + 2 # Google Sheet satır numarası
            
            # Verileri Al
            gr = safe_float(row.get('Gr', 0))
            kar = safe_float(row.get('Hedef Kar', 0))
            kaplama = safe_float(row.get('KaplamaTL', 0))
            lazer = safe_float(row.get('LazerTL', 0))
            mine = safe_float(row.get('MineTL', 0)) # Yeni Alan
            
            # HESAPLAMALAR
            komisyon_orani = 0.17 + (indirim/100)
            
            # Gümüş Fiyatı
            g_maliyet_tl = ((gr * (gumus_ons_usd + iscilik_gumus)) * dolar_kuru) + kaplama + lazer + mine + kargo_tl
            fiyat_gumus = (g_maliyet_tl + kar) / (1 - komisyon_orani)
            
            # Altın Fiyatı (14K) - Yoğunluk farkı 1.35x
            altin_gr = gr * 1.35
            a_maliyet_tl = ((altin_gr * ((altin_ons_usd/31.1*0.585) + iscilik_altin)) * dolar_kuru) + lazer + mine + kargo_tl
            fiyat_altin = (a_maliyet_tl + (kar * 1.5)) / (1 - komisyon_orani)

            with cols[idx % 4]:
                img_data = row.get('GörselData', '')
                st.markdown(f"""
                <div style="background:white; padding:10px; border-radius:10px; border:1px solid #ddd; text-align:center;">
                    <img src="data:image/jpeg;base64,{img_data}" style="width:100%; height:150px; object-fit:contain;">
                    <h6 style="margin:10px 0;">{row['Ürün']}</h6>
                    <div style="background:#f9f9f9; padding:5px; border-radius:5px; margin-bottom:5px;">
                        <small>🥈 Gümüş</small><br><b>{fiyat_gumus:,.0f} ₺</b>
                    </div>
                    <div style="background:#fff4e6; padding:5px; border-radius:5px;">
                        <small>🟡 14K Altın</small><br><b>{fiyat_altin:,.0f} ₺</b>
                    </div>
                    <div style="font-size:10px; color:gray; margin-top:5px;">
                        {gr}gr | Kar: {kar}₺ | Mine: {mine}₺
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # DÜZENLEME VE SİLME
                c_edit, c_del = st.columns(2)
                if c_edit.button("✏️", key=f"edit_{idx}"):
                    st.session_state[f"active_edit"] = idx
                
                if c_del.button("🗑️", key=f"del_{idx}"):
                    sheet.delete_rows(row_idx)
                    st.rerun()

                # Düzenleme Formu (Tüm alanlar değiştirilebilir)
                if st.session_state.get("active_edit") == idx:
                    with st.form(f"form_{idx}"):
                        new_ad = st.text_input("Ürün Adı", value=row['Ürün'])
                        new_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik"], index=0)
                        new_gr = st.number_input("Gram", value=gr)
                        new_kar = st.number_input("Kar", value=kar)
                        new_kap = st.number_input("Kaplama (TL)", value=kaplama)
                        new_laz = st.number_input("Lazer (TL)", value=lazer)
                        new_mine = st.number_input("Mine Bedeli (TL)", value=mine)
                        
                        if st.form_submit_button("💾 Güncelle"):
                            # Tablo yapısına göre güncelleme (A'dan I'ya)
                            sheet.update(f"A{row_idx}:I{row_idx}", [[
                                new_ad, row['Maden'], new_gr, new_kar, img_data, new_kat, new_kap, new_laz, new_mine
                            ]])
                            st.session_state["active_edit"] = None
                            st.rerun()

with t2:
    st.subheader("Yeni Ürün Kaydı")
    with st.form("yeni_urun"):
        u_ad = st.text_input("Ürün Adı")
        u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik", "Diğer"])
        u_gr = st.number_input("Gümüş Ağırlığı (gr)", value=0.0, step=0.1)
        u_kar = st.number_input("Hedef Kar (TL)", value=3000)
        u_mine = st.number_input("Mine Bedeli (TL)", value=0)
        u_kap = st.number_input("Kaplama (TL)", value=0)
        u_laz = st.number_input("Lazer (TL)", value=0)
        u_img = st.file_uploader("Ürün Görseli", type=['jpg', 'png'])
        
        if st.form_submit_button("Listeye Ekle"):
            img_b64 = image_to_base64(u_img)
            sheet.append_row([u_ad, "Gümüş", u_gr, u_kar, img_b64, u_kat, u_kap, u_laz, u_mine])
            st.success("Ürün başarıyla eklendi!")
            time.sleep(1)
            st.rerun()
