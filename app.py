import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import base64
from io import BytesIO
from PIL import Image
import time

st.set_page_config(page_title="CRIPP Jewelry Panel", layout="wide")


# GOOGLE SHEETS
def get_gspread_client():

    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gsheets"],
        scopes=scope
    )

    return gspread.authorize(creds)


client = get_gspread_client()
sheet = client.open("Etsy Price Sync").get_worksheet(0)


# FLOAT DÖNÜŞÜM
def safe_float(value):

    try:

        if value is None:
            return 0

        value = str(value)

        value = value.replace(",", ".")

        return float(value)

    except:
        return 0


# IMAGE
def image_to_base64(uploaded_file):

    if uploaded_file is None:
        return ""

    img = Image.open(uploaded_file).convert("RGB")

    img.thumbnail((400, 400))

    buffer = BytesIO()

    img.save(buffer, format="JPEG", quality=75)

    return base64.b64encode(buffer.getvalue()).decode()


# MODAL
@st.dialog("Ürün Düzenle")
def edit_product_modal(row_data, row_idx):

    with st.form(f"edit_{row_idx}"):

        new_ad = st.text_input(
            "Ürün Adı",
            value=row_data["Ürün"]
        )

        c1, c2 = st.columns(2)

        with c1:

            new_gr = st.number_input(
                "Gram",
                value=float(safe_float(row_data.get("Gr"))),
                step=0.1,
                format="%.2f"
            )

            new_kar = st.number_input(
                "Hedef Kar",
                value=float(safe_float(row_data.get("Hedef Kar")))
            )

            new_mine = st.number_input(
                "Mine TL",
                value=float(safe_float(row_data.get("MineTL")))
            )

        with c2:

            new_kaplama = st.number_input(
                "Kaplama TL",
                value=float(safe_float(row_data.get("KaplamaTL")))
            )

            new_lazer = st.number_input(
                "Lazer TL",
                value=float(safe_float(row_data.get("LazerTL")))
            )

            new_kat = st.selectbox(
                "Kategori",
                ["Yüzük", "Kolye", "Bileklik", "Küpe"],
                index=0
            )

        if st.form_submit_button("Kaydet"):

            updated_row = [

                new_ad,
                row_data["Maden"],
                new_gr,
                new_kar,
                row_data["GörselData"],
                new_kat,
                new_kaplama,
                new_lazer,
                new_mine

            ]

            sheet.update(
                f"A{row_idx}:I{row_idx}",
                [updated_row],
                value_input_option="USER_ENTERED"
            )

            st.success("Güncellendi")

            time.sleep(0.5)

            st.rerun()


# DATA
data = sheet.get_all_records()

df = pd.DataFrame(data)

if not df.empty:

    df = df[df["Ürün"].astype(str).str.strip() != ""]


# SIDEBAR
with st.sidebar:

    st.title("💎 Fiyat Ayarları")

    dolar_kuru = st.number_input(
        "Dolar Kuru",
        value=44.07
    )

    st.subheader("Gümüş")

    gumus_gram_tl = st.number_input(
        "Has Gümüş TL",
        value=125.60
    )

    iscilik_gumus_usd = st.number_input(
        "İşçilik $/gr",
        value=1.50
    )

    st.subheader("14K Altın")

    altin_has_gram_usd = st.number_input(
        "Has Altın $",
        value=85.0
    )

    iscilik_altin = st.number_input(
        "Altın İşçilik $/gr",
        value=10.0
    )

    st.markdown("---")

    kargo_tl = st.number_input(
        "Kargo",
        value=650.0
    )

    indirim_yuzde = st.number_input(
        "Etsy indirim %",
        value=15.0
    )


# ANA PANEL
st.title("Etsy Akıllı Fiyat Paneli")

tab1, tab2 = st.tabs(["Ürün Listesi", "Yeni Ürün"])


# LISTE
with tab1:

    search = st.text_input("Ürün Ara")

    if not df.empty:

        if search:

            f_df = df[df["Ürün"].str.contains(search, case=False)]

        else:

            f_df = df

        cols = st.columns(4)

        for idx, row in f_df.reset_index().iterrows():

            row_idx = int(row["index"]) + 2

            gr = safe_float(row.get("Gr"))

            kar = safe_float(row.get("Hedef Kar"))

            kaplama = safe_float(row.get("KaplamaTL"))

            lazer = safe_float(row.get("LazerTL"))

            mine = safe_float(row.get("MineTL"))

            komisyon = 0.17 + (indirim_yuzde / 100)

            g_maliyet = (

                (gr * gumus_gram_tl)
                + (gr * iscilik_gumus_usd * dolar_kuru)
                + kaplama
                + lazer
                + mine
                + kargo_tl

            )

            fiyat_gumus = (g_maliyet + kar) / (1 - komisyon)

            a_maliyet = (

                (gr * 1.35 * ((altin_has_gram_usd * 0.585) + iscilik_altin))
                * dolar_kuru
                + lazer
                + mine
                + kargo_tl

            )

            fiyat_altin = (a_maliyet + (kar * 1.5)) / (1 - komisyon)

            with cols[idx % 4]:

                st.image(
                    f"data:image/jpeg;base64,{row['GörselData']}"
                )

                st.write(row["Ürün"])

                st.success(f"Gümüş: {round(fiyat_gumus)} ₺")

                st.warning(f"14K Altın: {round(fiyat_altin)} ₺")

                st.caption(f"{gr} gr | {kar}₺ kar")

                c1, c2 = st.columns(2)

                if c1.button("Düzenle", key=f"edit{idx}"):

                    edit_product_modal(row, row_idx)

                if c2.button("Sil", key=f"del{idx}"):

                    sheet.delete_rows(row_idx)

                    st.rerun()


# YENI URUN
with tab2:

    with st.form("new_product"):

        ad = st.text_input("Ürün Adı")

        gram = st.number_input(
            "Gram",
            step=0.1
        )

        kar = st.number_input(
            "Kar",
            value=3000
        )

        img = st.file_uploader("Foto", type=["jpg","jpeg","png"])

        if st.form_submit_button("Kaydet"):

            img64 = image_to_base64(img)

            sheet.append_row(
                [
                    ad,
                    "Gümüş",
                    gram,
                    kar,
                    img64,
                    "Yüzük",
                    0,
                    0,
                    0
                ],
                value_input_option="USER_ENTERED"
            )

            st.success("Ürün eklendi")

            time.sleep(1)

            st.rerun()
