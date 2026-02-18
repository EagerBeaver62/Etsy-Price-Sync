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

# --- KÜTÜPHANE KONTROLLERİ ---
try:
    import yfinance as yf
except ImportError:
    st.error("Lütfen requirements.txt dosyasına 'yfinance' ekleyin.")
    st.stop()

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
            img.thumbnail((150, 150)) 
            buffered = BytesIO()
            img.save(buffered, format="JPEG", quality=60)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        except: return ""
    return ""

# --- HAREM ALTIN VERİ ÇEKME ---
@st.cache_data(ttl=60)
def get_harem_data():
    url = "https://www.haremaltin.com/dashboard/ajax/pol"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "https://www.haremaltin.com/"
    }
    
    try:
        response = requests.post(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            data_dict = data.get('data', {})
            
            gumus_usd_raw = data_dict.get('GUMUSUSD', {}).get('satis', 0)
            altin_tl_raw = data_dict.get('ALTIN', {}).get('satis', 0)
            dolar_tl_raw = data_dict.get('USDTRY', {}).get('satis', 0)
            ons_raw = data_dict.get('ALTINONS', {}).get('satis', 0)

            return {
                'gumus_usd': safe_float(gumus_usd_raw),
                'altin_tl': safe_float(altin_tl_raw),
                'dolar_tl': safe_float(dolar_tl_raw),
                'altin_ons': safe_float(ons_raw),
                'status': 'success',
                'time': datetime.datetime.now().strftime("%H:%M")
            }
    except Exception as e:
        return {'status': 'error', 'msg': str(e)}
    
    return {'status': 'error', 'msg': 'Veri alınamadı'}

market_data = get_harem_data()

# Yedek Veri
if market_data['status'] == 'error':
    try:
        d = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        market_data = {
            'gumus_usd': 0.0,
            'altin_tl': (a/31.1035)*d,
            'dolar_tl': d,
            'altin_ons': a,
            'status': 'backup',
            'time': datetime.datetime.now().strftime("%H:%M")
        }
    except:
        market_data = {'gumus_usd':0, 'altin_tl':0, 'dolar_tl':0, 'altin_ons':0, 'status':'fail', 'time':'--:--'}

dolar_kuru = market_data['dolar_tl']
altin_ons = market_data['altin_ons']
saat = market_data['time']

# --- GOOGLE SHEETS ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        return pd.DataFrame(sh.get_all_records()), sh
    except: return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR (SOL PANEL) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"Veri: {market_data['status'].upper()} | {saat}")
    st.divider()
    
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    
    # ALTIN GÖSTERGESİ
    has_altin_usd_gr = altin_ons / 31.1035
    st.metric("🟡 Has Altın (Ons Bazlı)", f"${has_altin_usd_gr:.2f} / gr")
    st.divider()

    # GÜMÜŞ AYARLARI
    st.subheader("🥈 Gümüş Ayarları")
    raw_gumus = market_data['gumus_usd']
    if raw_gumus > 500: # KG fiyatı geldiyse
        auto_gumus_gram_usd = raw_gumus / 1000
    else:
        auto_gumus_gram_usd = raw_gumus

    mode = st.radio("Gümüş Kaynağı", ["Otomatik", "Manuel"], horizontal=True)
    
    if mode == "Otomatik" and market_data['status'] == 'success':
        gumus_baz_usd = auto_gumus_gram_usd
        st.info(f"Gümüş: ${gumus_baz_usd:.3f}")
    else:
        varsayilan = 3.15 if auto_gumus_gram_usd == 0 else auto_gumus_gram_usd
        gumus_baz_usd = st.number_input("Manuel Gümüş ($/Gr)", value=float(varsayilan), step=0.01, format="%.3f")
    
    st.divider()
    
    # MALİYETLER
    st.write("🔧 **İşçilik & Giderler**")
    iscilik_gumus = st.number_input("Gümüş İşçilik ($/gr)", value=1.50, step=0.10)
    iscilik_altin = st.number_input("Altın İşçilik ($/gr)", value=10.00, step=0.50, help="Altın ürünler için gram başı işçilik")
    
    kargo_tl = st.number_input("Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("Etsy İndirim (%)", value=15.0)
    
    st.divider()
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.header("💎 Etsy Akıllı Fiyat Paneli")

t1, t2 = st.tabs(["📊 Ürün Listesi", "➕ Yeni Ürün Ekle"])

# --- TAB 1: ÜRÜN LİSTELEME ---
with t1:
    if not df.empty:
        all_kats = ["Hepsi"] + sorted(list(df['Kategori'].unique()))
        try:
            secilen_kat = st.pills("Kategoriler", all_kats, default="Hepsi")
        except:
            secilen_kat = st.selectbox("Kategori", all_kats)

        arama = st.text_input("🔍 Ürün Ara...", "")
        
        mask = df['Ürün'].astype(str).str.lower().str.contains(arama.lower())
        if secilen_kat != "Hepsi": mask = mask & (df['Kategori'] == secilen_kat)
        f_df = df[mask]
        
        if view_mode == "🎨 Kartlar":
            cols = st.columns(4)
            for idx, row in f_df.reset_index().iterrows():
                row_idx = int(row.get('index')) + 2
                
                # VERİLER
                m_gr = safe_float(row.get('Gr', 0))
                m_kar = safe_float(row.get('Hedef Kar', 0))
                m_kap = safe_float(row.get('KaplamaTL', 0))
                m_laz = safe_float(row.get('LazerTL', 0))
                m_maden = str(row.get('Maden', 'Gümüş'))
                
                # --- HESAPLAMA MANTIĞI (GÜMÜŞ vs ALTIN) ---
                if "Altın" in m_maden:
                    # Altın İşçiliği ve Milyem Hesabı
                    aktif_iscilik = iscilik_altin
                    base_price = altin_ons / 31.1035 # 24K Gram Dolar Fiyatı
                    
                    # Ayar (Milyem) Kontrolü
                    if "14K" in m_maden: factor = 0.585
                    elif "18K" in m_maden: factor = 0.750
                    elif "22K" in m_maden: factor = 0.916
                    else: factor = 1.00 # Has Altın
                    
                    birim_fiyat_usd = base_price * factor
                    etiket_maden = f"{m_maden}"
                else:
                    # Gümüş Hesabı
                    aktif_iscilik = iscilik_gumus
                    birim_fiyat_usd = gumus_baz_usd
                    etiket_maden = "Gümüş"
                
                # Genel Maliyet Hesabı
                ham_maden_usd = m_gr * birim_fiyat_usd
                toplam_dolar_maliyeti = ham_maden_usd + (m_gr * aktif_iscilik)
                maliyet_tl = (toplam_dolar_maliyeti * dolar_kuru) + m_kap + m_laz + kargo_tl
                
                komisyon = 0.17 + (indirim_yuzde / 100)
                satis_fiyati = (maliyet_tl + m_kar) / (1 - komisyon)
                
                # KART GÖSTERİMİ
                with cols[idx % 4]:
                    img = row.get('GörselData', '')
                    # Maden rengine göre etiket
                    badge_color = "#fff3cd" if "Altın" in m_maden else "#e0f7fa"
                    text_color = "#856404" if "Altın" in m_maden else "#006064"
                    
                    st.markdown(f"""
                    <div style="background:white; padding:15px; border-radius:12px; border:1px solid #eee; text-align:center;">
                        <span style="background:{badge_color}; color:{text_color}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">
                            {etiket_maden} | ${ham_maden_usd:.1f}
                        </span>
                        <img src="data:image/jpeg;base64,{img}" style="height:120px; object-fit:contain; margin-top:15px;">
                        <p style="font-weight:bold; margin:10px 0 5px 0; font-size:14px; height:40px; overflow:hidden;">{row.get('Ürün')}</p>
                        <h3 style="color:#27ae60; margin:0;">{satis_fiyati:,.0f} ₺</h3>
                        <div style="font-size:11px; color:gray; border-top:1px solid #eee; padding-top:5px;">
                            ⚖️ {m_gr} Gr | 🎯 Kar: {m_kar}₺
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    c_edit, c_del = st.columns(2)
                    if c_edit.button("✏️", key=f"e_{idx}"):
                        st.session_state[f"form_{idx}"] = not st.session_state.get(f"form_{idx}", False)
                    if c_del.button("🗑️", key=f"d_{idx}"):
                        sheet.delete_rows(row_idx)
                        st.cache_data.clear()
                        st.rerun()
                    
                    if st.session_state.get(f"form_{idx}"):
                        with st.form(f"edit_form_{idx}"):
                            n_name = st.text_input("Ad", value=row.get('Ürün'))
                            n_gr = st.text_input("Gram", value=str(m_gr))
                            n_kar = st.number_input("Kar (TL)", value=float(m_kar))
                            
                            if st.form_submit_button("💾 Kaydet"):
                                sheet.update_cell(row_idx, 1, n_name)
                                sheet.update_cell(row_idx, 3, n_gr.replace(',','.'))
                                sheet.update_cell(row_idx, 4, n_kar)
                                st.session_state[f"form_{idx}"] = False
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.dataframe(f_df, use_container_width=True)

# --- TAB 2: YENİ ÜRÜN EKLEME ---
with t2:
    st.subheader("Yeni Ürün Ekle")
    st.info("💡 Ürünler listenin en altına güvenli şekilde eklenir.")
    
    with st.form("yeni_urun_formu", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı", placeholder="Örn: 14K Altın Kolye")
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik", "Diğer"])
            
            # GELİŞMİŞ MADEN SEÇİMİ
            maden_tipi = st.selectbox("Maden Tipi", ["Gümüş", "Altın"])
            
            final_maden_name = "Gümüş"
            if maden_tipi == "Altın":
                altin_ayar = st.selectbox("Altın Ayarı", ["14K", "18K", "22K", "24K (Has)"])
                final_maden_name = f"Altın {altin_ayar}"
            
            u_gr = st.text_input("Gram (Nokta ile)", value="0.0")
            
        with c2:
            u_kap = st.number_input("Kaplama (TL)", value=0.0, help="Sadece Gümüş için genelde kullanılır")
            u_laz = st.number_input("Lazer (TL)", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=5000.0 if maden_tipi == "Altın" else 2500.0)
            u_img = st.file_uploader("Görsel Yükle", type=['jpg','png'])
        
        submitted = st.form_submit_button("Listeye Ekle")
        
        if submitted:
            if not u_ad:
                st.error("Lütfen ürün adı giriniz.")
            else:
                with st.spinner("Google Sheets'e yazılıyor..."):
                    img_str = image_to_base64(u_img)
                    
                    # --- GÜVENLİ SATIR BULMA ---
                    mevcut_urunler = sheet.col_values(1)
                    son_satir_index = len(mevcut_urunler) + 1
                    
                    # Veri Hazırlama
                    yeni_veri = [
                        u_ad, 
                        final_maden_name, # Örn: "Altın 14K" veya "Gümüş"
                        u_gr.replace(',','.'), 
                        u_kar, 
                        img_str, 
                        u_kat, 
                        u_kap, 
                        u_laz, 
                        0
                    ]
                    
                    # Kayıt
                    aralik = f"A{son_satir_index}:I{son_satir_index}"
                    sheet.update(range_name=aralik, values=[yeni_veri])
                    
                    st.success(f"✅ '{u_ad}' ({final_maden_name}) başarıyla eklendi!")
                    st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
