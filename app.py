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
    except: return None

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
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
else:
    df = pd.DataFrame()

# --- SIDEBAR (LOGO VE AYARLAR) ---
with st.sidebar:
    try:
        logo_img = Image.open("logo.png")
        st.image(logo_img, use_container_width=True)
    except:
        st.title("💎 CRIPP Jewelry")
    
    st.divider()
    st.success(f"🕒 **Son Kontrol:** {son_guncelleme}")
    st.metric(label="💵 Canlı Dolar Kuru", value=f"{dolar_kuru:.2f} ₺")
    kur = float(dolar_kuru) 
    
    st.divider()
    # İSTEDİĞİN VARSAYILAN AYARLAR
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
            u_kaplama_tl = st.number_input("Kaplama Maliyeti (TL)", value=0.0)
            u_lazer_tl = st.number_input("Lazer Maliyeti (TL)", value=0.0)
            u_kar = st.number_input("Hedef Net Kar (TL)", value=2500.0)
            u_img = st.file_uploader("Görsel Yükle", type=["jpg", "png"])
            
        if st.form_submit_button("Sisteme Kaydet"):
            if u_ad and sheet:
                safe_gr = u_gr.replace(',', '.')
                img_data = image_to_base64(u_img)
                # Sütun Sırası: Ürün, Maden, Gr, Hedef Kar, GörselData, Kategori, KaplamaTL, LazerTL
                sheet.append_row([u_ad, u_maden, safe_gr, u_kar, img_data, u_kat, u_kaplama_tl, u_lazer_tl])
                st.success(f"{u_ad} başarıyla eklendi!")
                st.rerun()

with tab1:
    if not df.empty:
        c1, c2 = st.columns([3, 1])
        with c1:
            search = st.text_input("🔍 İsimle ara...", "").lower()
        with c2:
            kat_liste = ["Hepsi"] + list(df['Kategori'].unique()) if 'Kategori' in df.columns else ["Hepsi"]
            kat_filtre = st.selectbox("📁 Kategori", kat_liste)

        mask = df['Ürün'].astype(str).str.lower().str.contains(search)
        if kat_filtre != "Hepsi":
            mask = mask & (df['Kategori'] == kat_filtre)
        
        filtered_df = df[mask]

        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in filtered_df.reset_index().iterrows():
                actual_row_idx = int(row['index']) + 2 
                m_ad = row.get('Ürün', 'Adsız')
                m_tur = row.get('Maden', 'Gümüş')
                m_kat = row.get('Kategori', 'Genel')
                try: m_gram = float(str(row.get('Gr', 0)).replace(',', '.'))
                except: m_gram = 0.0
                try: m_hedef = float(str(row.get('Hedef Kar', 0)).replace(',', '.'))
                except: m_hedef = 0.0
                m_img = row.get('GörselData', '')
                
                # TL Maliyet Kalemleri
                try: m_kaplama_tl = float(row.get('KaplamaTL', 0))
                except: m_kaplama_tl = 0.0
                try: m_lazer_tl = float(row.get('LazerTL', 0))
                except: m_lazer_tl = 0.0

                # --- HESAPLAMA MOTORU (TL ÜZERİNDEN) ---
                ons = ons_altin if m_tur == "Altın" else ons_gumus
                maden_maliyet_tl = (ons / 31.1035) * m_gram * kur
                iscilik_maliyet_tl = m_gram * gr_iscilik * kur
                
                # Toplam Maliyet: Maden(TL) + İşçilik(TL) + Kaplama(TL) + Lazer(TL) + Kargo(TL)
                toplam_maliyet = maden_maliyet_tl + iscilik_maliyet_tl + m_kaplama_tl + m_lazer_tl + kargo
                satis_fiyati = (toplam_maliyet + m_hedef) / (1 - (etsy_komisyon + indirim_oran/100))
                
                with cols[idx % 4]:
                    st.markdown(f"""
                    <div style="background-color:white; padding:12px; border-radius:15px; border:1px solid #eee; text-align:center; margin-bottom:10px; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">
                        <div style="font-size:10px; color:white; background:#00332B; width:fit-content; padding:2px 8px; border-radius:10px; margin-bottom:5px;">{m_kat}</div>
                        <img src="data:image/jpeg;base64,{m_img}" style="width:100%; height:140px; object-fit:contain; border-radius:8px; background:#fcfcfc;">
                        <p style="font-weight:bold; margin:8px 0 2px 0; color:#2d3436; font-size:14px; height:40px; overflow:hidden;">{m_ad}</p>
                        <h2 style="color:#d63031; margin:0;">{round(satis_fiyati, 2)} ₺</h2>
                        <div style="display:flex; justify-content:space-around; margin-top:5px; border-top:1px solid #f1f1f1; padding-top:5px;">
                            <span style="font-size:10px; color:#636e72;"><b>Gr:</b> {m_gram}</span>
                            <span style="font-size:10px; color:#636e72;"><b>Ek:</b> {m_kaplama_tl + m_lazer_tl}₺</span>
                            <span style="font-size:10px; color:#636e72;"><b>Net:</b> {round(m_hedef,0)}₺</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button(f"✏️ Düzenle", key=f"edit_btn_{actual_row_idx}"):
                            st.session_state[f"edit_mode_{actual_row_idx}"] = True
                    with b2:
                        if st.button(f"🗑️ Kaldır", key=f"del_{actual_row_idx}"):
                            sheet.delete_rows(actual_row_idx)
                            st.rerun()

                    if st.session_state.get(f"edit_mode_{actual_row_idx}", False):
                        with st.form(key=f"edit_form_{actual_row_idx}"):
                            st.write(f"✏️ {m_ad} Güncelle")
                            e_name = st.text_input("Ürün İsmi", value=m_ad)
                            e_kat = st.selectbox("Kategori", ["Kolye", "Yüzük", "Küpe", "Bileklik", "Diğer"], 
                                               index=["Kolye", "Yüzük", "Küpe", "Bileklik", "Diğer"].index(m_kat) if m_kat in ["Kolye", "Yüzük", "Küpe", "Bileklik", "Diğer"] else 0)
                            e_maden = st.selectbox("Maden", ["Gümüş", "Altın"], index=0 if m_tur == "Gümüş" else 1)
                            
                            c_e1, c_e2 = st.columns(2)
                            with c_e1:
                                e_gr = st.text_input("Gramaj", value=str(m_gram))
                                e_kap = st.number_input("Kaplama (TL)", value=m_kaplama_tl)
                            with c_e2:
                                e_laz = st.number_input("Lazer (TL)", value=m_lazer_tl)
                                e_kar = st.number_input("Hedef Kar (TL)", value=float(m_hedef))
                            
                            f1, f2 = st.columns(2)
                            if f1.form_submit_button("✅ Kaydet"):
                                sheet.update_cell(actual_row_idx, 1, e_name)
                                sheet.update_cell(actual_row_idx, 2, e_maden)
                                sheet.update_cell(actual_row_idx, 3, e_gr.replace(',', '.'))
                                sheet.update_cell(actual_row_idx, 4, e_kar)
                                sheet.update_cell(actual_row_idx, 6, e_kat)
                                sheet.update_cell(actual_row_idx, 7, e_kap)
                                sheet.update_cell(actual_row_idx, 8, e_laz)
                                st.session_state[f"edit_mode_{actual_row_idx}"] = False
                                st.success("Güncellendi!")
                                st.rerun()
                            if f2.form_submit_button("❌ İptal"):
                                st.session_state[f"edit_mode_{actual_row_idx}"] = False
                                st.rerun()
        else:
            st.dataframe(filtered_df, use_container_width=True)
    else:
        st.info("Henüz veri yok.")
