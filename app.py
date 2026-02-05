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

# --- HAREM ALTIN VERİ ÇEKME FONKSİYONU ---
@st.cache_data(ttl=60) # 60 saniyede bir günceller
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
            
            # Gümüş USD ve Altın TL verilerini ayıkla
            # Harem genellikle 'ALTIN' (Has TL) ve 'GUMUSUSD' (Gümüş Dolar) anahtarlarını kullanır
            
            gumus_usd_raw = data_dict.get('GUMUSUSD', {}).get('satis', 0)
            altin_tl_raw = data_dict.get('ALTIN', {}).get('satis', 0)
            dolar_tl_raw = data_dict.get('USDTRY', {}).get('satis', 0)
            
            # Altın ONS (Global Kontrol için)
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

# --- VERİLERİ YÜKLE ---
market_data = get_harem_data()

# Eğer Harem verisi çekilemezse Yfinance yedeği
if market_data['status'] == 'error':
    # Yedek (Yfinance)
    try:
        d = yf.Ticker("USDTRY=X").history(period="1d")['Close'].iloc[-1]
        a = yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1]
        market_data = {
            'gumus_usd': 0.0, # Yfinance'de Gümüş USD/KG yok, manuel girilecek
            'altin_tl': (a/31.1035)*d,
            'dolar_tl': d,
            'altin_ons': a,
            'status': 'backup',
            'time': datetime.datetime.now().strftime("%H:%M")
        }
    except:
        market_data = {'gumus_usd':0, 'altin_tl':0, 'dolar_tl':0, 'status':'fail', 'time':'--:--'}

dolar_kuru = market_data['dolar_tl']
altin_ons = market_data['altin_ons']
saat = market_data['time']

# --- GOOGLE SHEETS ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # ID'niz
        sh = client.open_by_key("1mnUAeYsRVIooHToi3hn7cGZanIBhyulknRTOyY9_v2E").sheet1 
        return pd.DataFrame(sh.get_all_records()), sh
    except: return pd.DataFrame(), None

df, sheet = get_sheet()

# --- SIDEBAR (AYARLAR) ---
with st.sidebar:
    st.title("💎 CRIPP Jewelry")
    st.caption(f"Veri Kaynağı: {market_data['status'].upper()} | {saat}")
    
    st.divider()
    
    # 1. DOLAR KURU
    st.metric("💵 Dolar/TL", f"{dolar_kuru:.2f} ₺")
    
    st.divider()

    # 2. GÜMÜŞ AYARI (Harem Otomatik)
    st.subheader("🥈 Gümüş Fiyatlandırması")
    
    # Harem'den gelen veri KG fiyatı mı Gram fiyatı mı kontrolü
    raw_gumus = market_data['gumus_usd']
    
    # Eğer fiyat 500'den büyükse muhtemelen KG fiyatıdır (Örn: 3143), 1000'e bölüp Gram buluruz
    if raw_gumus > 500:
        auto_gumus_gram_usd = raw_gumus / 1000
        etiket_bilgi = f"Harem (KG): ${raw_gumus:,.2f}"
    else:
        auto_gumus_gram_usd = raw_gumus
        etiket_bilgi = f"Harem (Gr): ${raw_gumus:.2f}"

    # Kullanıcıya Seçenek Sunma
    mode = st.radio("Kur Kaynağı", ["Otomatik (Harem)", "Manuel"], horizontal=True)
    
    if mode == "Otomatik (Harem)" and market_data['status'] == 'success':
        gumus_baz_usd = auto_gumus_gram_usd
        st.success(f"Güncel: ${gumus_baz_usd:.3f} / gr")
        st.caption(etiket_bilgi)
    else:
        if market_data['status'] != 'success' and mode == "Otomatik (Harem)":
            st.warning("Otomatik veri alınamadı, manuel mod aktif.")
        # Manuel Giriş (Varsayılan olarak son hesaplanan veya 3.15)
        varsayilan = 3.15 if auto_gumus_gram_usd == 0 else auto_gumus_gram_usd
        gumus_baz_usd = st.number_input("Manuel Gümüş ($/Gr)", value=float(varsayilan), step=0.01, format="%.3f")
    
    st.divider()
    
    # 3. DİĞER MALİYETLER
    st.write("🔧 **Ek Maliyetler**")
    # İşçilik Maliyeti (Varsayılan 1.50)
    iscilik_usd = st.number_input("Ek İşçilik ($/gr)", value=1.50, step=0.10)
    kargo_tl = st.number_input("Kargo (TL)", value=650.0)
    indirim_yuzde = st.number_input("Etsy İndirim (%)", value=15.0)
    
    st.divider()
    view_mode = st.radio("Görünüm", ["🎨 Kartlar", "📋 Liste"])

# --- ANA EKRAN ---
st.header("💎 Etsy Akıllı Fiyat Paneli")

t1, t2 = st.tabs(["📊 Ürünler", "➕ Yeni Ekle"])

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
                m_maden = row.get('Maden', 'Gümüş')
                
                # --- HESAPLAMA MANTIĞI ---
                if m_maden == "Altın":
                    # Altın için: (Ons / 31.1035) formülü
                    birim_fiyat_usd = altin_ons / 31.1035
                else:
                    # Gümüş için: Harem'den gelen veya manuel girilen $/Gr fiyatı
                    birim_fiyat_usd = gumus_baz_usd
                
                # 1. Ham Maden Maliyeti
                ham_maden_usd = m_gr * birim_fiyat_usd
                
                # 2. Toplam Dolar (Ham + İşçilik)
                toplam_dolar_maliyeti = ham_maden_usd + (m_gr * iscilik_usd)
                
                # 3. TL Çevrimi ve Ekler
                maliyet_tl = (toplam_dolar_maliyeti * dolar_kuru) + m_kap + m_laz + kargo_tl
                
                # 4. Satış Fiyatı
                komisyon = 0.17 + (indirim_yuzde / 100)
                satis_fiyati = (maliyet_tl + m_kar) / (1 - komisyon)
                
                with cols[idx % 4]:
                    img = row.get('GörselData', '')
                    st.markdown(f"""
                    <div style="background:white; padding:15px; border-radius:12px; border:1px solid #eee; text-align:center; position:relative;">
                        <span style="position:absolute; top:10px; left:10px; background:#e0f7fa; color:#006064; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">${ham_maden_usd:.2f} Ham</span>
                        <img src="data:image/jpeg;base64,{img}" style="height:120px; object-fit:contain; margin-top:15px;">
                        <p style="font-weight:bold; margin:10px 0 5px 0; font-size:14px; height:40px; overflow:hidden;">{row.get('Ürün')}</p>
                        <h3 style="color:#27ae60; margin:0;">{satis_fiyati:,.0f} ₺</h3>
                        <div style="font-size:11px; color:gray; margin-top:8px; border-top:1px solid #eee; padding-top:5px;">
                            <div>⚖️ {m_gr} Gr | 🎯 Kar: {m_kar}₺</div>
                            <div>🧪 Kap: {m_kap}₺ | 🔦 Laz: {m_laz}₺</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # BUTONLAR
                    c_edit, c_del = st.columns(2)
                    if c_edit.button("✏️", key=f"e_{idx}"):
                        st.session_state[f"form_{idx}"] = not st.session_state.get(f"form_{idx}", False)
                    if c_del.button("🗑️", key=f"d_{idx}"):
                        sheet.delete_rows(row_idx)
                        st.rerun()
                    
                    # DÜZENLEME FORMU
                    if st.session_state.get(f"form_{idx}"):
                        with st.form(f"edit_form_{idx}"):
                            n_name = st.text_input("Ad", value=row.get('Ürün'))
                            n_gr = st.text_input("Gram", value=str(m_gr))
                            n_kap = st.number_input("Kaplama", value=float(m_kap))
                            n_laz = st.number_input("Lazer", value=float(m_laz))
                            n_kar = st.number_input("Hedef Kar", value=float(m_kar))
                            
                            if st.form_submit_button("💾 Kaydet"):
                                sheet.update_cell(row_idx, 1, n_name)
                                sheet.update_cell(row_idx, 3, n_gr.replace(',','.'))
                                sheet.update_cell(row_idx, 4, n_kar)
                                sheet.update_cell(row_idx, 7, n_kap)
                                sheet.update_cell(row_idx, 8, n_laz)
                                st.session_state[f"form_{idx}"] = False
                                st.rerun()
        else:
            st.dataframe(f_df, use_container_width=True)

with t2:
    st.subheader("Yeni Ürün Ekle")
    with st.form("yeni_urun"):
        c1, c2 = st.columns(2)
        with c1:
            u_ad = st.text_input("Ürün Adı")
            u_kat = st.selectbox("Kategori", ["Yüzük", "Kolye", "Küpe", "Bileklik", "Diğer"])
            u_maden = st.selectbox("Maden", ["Gümüş", "Altın"])
            u_gr = st.text_input("Gram (Örn: 12.50)", value="0.0")
        with c2:
            u_kap = st.number_input("Kaplama Maliyeti (TL)", value=0.0)
            u_laz = st.number_input("Lazer Maliyeti (TL)", value=0.0)
            u_kar = st.number_input("Hedef Kar (TL)", value=2500.0)
            u_img = st.file_uploader("Görsel Yükle", type=['jpg','png'])
        
        if st.form_submit_button("Ekle"):
            img_str = image_to_base64(u_img)
            # Sıralama: Ürün, Maden, Gr, Kar, Görsel, Kategori, Kaplama, Lazer, Zincir
            sheet.append_row([u_ad, u_maden, u_gr.replace(',','.'), u_kar, img_str, u_kat, u_kap, u_laz, 0])
            st.success("✅ Ürün başarıyla eklendi!")
            st.rerun()
