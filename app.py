import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import datetime

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="CRIPP Jewelry Dashboard", layout="wide", page_icon="💎")

# --- GOOGLE SHEETS BAĞLANTISI ---
def get_gsheet_client():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1
    except Exception as e:
        return None

# --- GÖRSEL İŞLEME ---
def image_to_base64(image_file):
    if image_file is not None:
        try:
            img = Image.open(image_file)
            if img.mode != "RGB": img = img.convert("RGB")
            img.thumbnail((150, 150)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- PİYASA VERİLERİ ---
@st.cache_data(ttl=120)
def piyasa_verileri():
    try:
        dolar = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        altin = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        gumus = yf.Ticker("SI=F").history(period="1d")['Close'].iloc[-1]
        saat = datetime.datetime.now().strftime("%H:%M:%S")
        return dolar, altin, gumus, saat
    except: 
        return 43.27, 2650.0, 31.0, "Bilinmiyor"

dolar_kuru, ons_altin, ons_gumus, son_guncelleme = piyasa_verileri()
sheet = get_gsheet_client()

if sheet:
    try:
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
    except:
        df = pd.DataFrame()
else:
    df = pd.DataFrame()

# --- SIDEBAR ---
with st.sidebar:
    try:
        logo_img = Image.open("Adsız tasarım (22).png")
        st.image(logo_img, use_container_width=True)
    except:
        st.title("💎 CRIPP Jewelry")
    
    st.divider()
    st.success(f"🕒 **Son Kontrol:** {son_guncelleme}")
    st.metric(label="💵 Canlı Dolar Kuru", value=f"{dolar_kuru:.2f} ₺")
    kur = float(dolar_kuru) 
    
    st.divider()
    gr_iscilik = st.number_input("🛠️ Genel İşçilik ($/gr)", value=1.50, format="%.2f")
    kargo = st.number_input("🚚 Kargo Maliyeti (TL)", value=650.0)
    indirim_oran = st.number_input("🏷️ Etsy İndirim (%)", value=15.0)
    etsy_komisyon = 0.17 
    
    st.divider()
    view_mode = st.radio("Görünüm Seçimi", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.title("💎 Etsy Akıllı Fiyat & Stok Paneli")
tab1, tab2 = st.tabs(["📊 Ürün Yönetimi", "➕ Yeni Ürün Ekle"])

with tab2:
    with st.form("ekle_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            u_ad = st.text_input("Ürün Adı")
            u_kat = st.selectbox("Kategori", ["Kolye", "Yüzük", "Küpe", "Bileklik", "Diğer"])
            u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            u_gr = st.text_input("Gramaj (Örn: 3.5)", value="0.0")
        with col2:
            u_kap = st.number_input("Kaplama (TL)", value=0.0)
            u_laz = st.number_input("Lazer (TL)", value=0.0)
            u_zin = st.number_input("Zincir (TL)", value=0.0)
            u_kar = st.number_input("Hedef Net Kar (TL)", value=2500.0)
            u_img = st.file_uploader("Görsel Yükle", type=["jpg", "png"])
            
        if st.form_submit_button("Sisteme Kaydet"):
            if u_ad and sheet:
                safe_gr = u_gr.replace(',', '.')
                img_data = image_to_base64(u_img)
                # Sıralama: Ürün, Maden, Gr, Kar, Görsel, Kategori, Kaplama, Lazer, Zincir
                sheet.append_row([u_ad, u_maden, safe_gr, u_kar, img_data, u_kat, u_kap, u_laz, u_zin])
                st.success(f"{u_ad} başarıyla eklendi!")
                st.rerun()

with tab1:
    if not df.empty:
        # --- BUTON ŞEKLİNDE KATEGORİ FİLTRESİ ---
        st.write("### 📁 Kategoriler")
        mevcut_kategoriler = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
        
        # Session state ile seçili kategoriyi tutalım
        if 'selected_kat' not in st.session_state:
            st.session_state.selected_kat = "Hepsi"

        kat_cols = st.columns(len(mevcut_kategoriler))
        for i, kat in enumerate(mevcut_kategoriler):
            # Seçili butonu farklı renkte gösterelim
            btn_type = "primary" if st.session_state.selected_kat == kat else "secondary"
            if kat_cols[i].button(kat, key=f"kat_btn_{kat}", use_container_width=True, type=btn_type):
                st.session_state.selected_kat = kat
                st.rerun()
        
        st.divider()
        search = st.text_input("🔍 İsimle ara...", "").lower()

        # Filtreleme Uygula
        mask = df['Ürün'].astype(str).str.lower().str.contains(search)
        if st.session_state.selected_kat != "Hepsi":
            mask = mask & (df['Kategori'] == st.session_state.selected_kat)
        
        filtered_df = df[mask]

        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in filtered_df.reset_index().iterrows():
                actual_row_idx = int(row['index']) + 2 
                m_ad = row.get('Ürün', 'Adsız')
                m_tur = row.get('Maden', 'Gümüş')
                m_kat = row.get('Kategori', 'Genel')
                m_gram = float(str(row.get('Gr', 0)).replace(',', '.')) if row.get('Gr') else 0.0
                m_hedef = float(row.get('Hedef Kar', 0)) if row.get('Hedef Kar') else 0.0
                m_img = row.get('GörselData', '')
                m_kap = float(row.get('KaplamaTL', 0)) if row.get('KaplamaTL') else 0.0
                m_laz = float(row.get('LazerTL', 0)) if row.get('LazerTL') else 0.0
                m_zin = float(row.get('ZincirTL', 0)) if row.get('ZincirTL') else 0.0

                # --- HESAPLAMA ---
                ons = ons_altin if m_tur == "Altın" else ons_gumus
                maden_tl = (ons / 31.1035) * m_gram * kur
                iscilik_tl = m_gram * gr_iscilik * kur
                toplam_maliyet = maden_tl + iscilik_tl + m_kap + m_laz + m_zin + kargo
                satis_fiyati = (toplam_maliyet + m_hedef) / (1 - (etsy_komisyon + indirim_oran/100))
                
                with cols[idx % 4]:
                    # Kategoriye göre badge rengi
                    kat_color = "#00332B" if m_kat == "Kolye" else "#1e3a8a" if m_kat == "Yüzük" else "#5b21b6"
                    
                    st.markdown(f"""
                    <div style="background-color:white; padding:12px; border-radius:15px; border:1px solid #eee; text-align:center; margin-bottom:10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size:10px; color:white; background:{kat_color}; width:fit-content; padding:2px 8px; border-radius:10px; margin-bottom:5px;">{m_kat}</div>
                        <img src="data:image/jpeg;base64,{m_img}" style="width:100%; height:140px; object-fit:contain; border-radius:8px;">
                        <p style="font-weight:bold; margin:8px 0 2px 0; color:#2d3436; font-size:14px; height:40px; overflow:hidden;">{m_ad}</p>
                        <h2 style="color:#d63031; margin:0;">{round(satis_fiyati, 2)} ₺</h2>
                        <p style="font-size:10px; color:#636e72;">Gr: {m_gram} | Kar: {m_hedef}₺</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("✏️", key=f"e_{actual_row_idx}"):
                            st.session_state[f"edit_{actual_row_idx}"] = True
                    with b2:
                        if st.button("🗑️", key=f"d_{actual_row_idx}"):
                            sheet.delete_rows(actual_row_idx)
                            st.rerun()

                    if st.session_state.get(f"edit_{actual_row_idx}", False):
                        with st.form(key=f"f_{actual_row_idx}"):
                            e_name = st.text_input("İsim", value=m_ad)
                            e_gr = st.text_input("Gramaj", value=str(m_gram))
                            e_kar = st.number_input("Hedef Kar", value=float(m_hedef))
                            e_kap = st.number_input("Kaplama TL", value=m_kap)
                            e_laz = st.number_input("Lazer TL", value=m_laz)
                            e_zin = st.number_input("Zincir TL", value=m_zin)
                            if st.form_submit_button("Kaydet"):
                                vals = [e_name, m_tur, e_gr.replace(',','.'), e_kar, m_img, m_kat, e_kap, e_laz, e_zin]
                                for i, val in enumerate(vals, 1):
                                    sheet.update_cell(actual_row_idx, i, val)
                                st.session_state[f"edit_{actual_row_idx}"] = False
                                st.rerun()
        else:
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Veri bulunamadı. Lütfen ürün ekleyin.")
