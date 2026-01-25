import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Inventory Master",
    page_icon="🔥", # Cieplejsza ikona
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLIZACJA CSS (CIEPŁE KOLORY) ---
st.markdown("""
<style>
    /* TŁO APLIKACJI - Delikatny kremowy/beżowy */
    .stApp {
        background-color: #FFFBF5; 
    }
    
    /* KARTY METRYK - Białe z ciepłym pomarańczowym akcentem i cieniem */
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-left: 6px solid #FF8C00; /* Ciemny pomarańcz */
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 10px rgba(255, 140, 0, 0.1); /* Ciepły cień */
    }
    
    /* POWIĘKSZENIE LICZB W METRYKACH */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #D35400 !important; /* Rdzawy kolor tekstu */
    }
    
    /* ZAKŁADKI - Aktywna zakładka ma ciepły czerwony pasek */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #FDF2E9; /* Bardzo jasny pomarańcz */
        border-radius: 5px 5px 0px 0px;
        gap: 5px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-top: 4px solid #FF4B4B !important; /* Streamlit Red */
        font-weight: bold;
    }
    
    /* NAGŁÓWKI - Ciemny brąz zamiast czerni dla lepszego kontrastu z ciepłym tłem */
    h1, h2, h3 {
        color: #5D4037 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z SUPABASE (CACHE) ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("❌ Błąd: Sprawdź sekrety połączenia.")
        st.stop()

supabase = init_connection()

# --- FUNKCJE ---

def pobierz_dane_glowne():
    # Kategorie
    kat_response = supabase.table('Kategorie').select("*").execute()
    kategorie_df = pd.DataFrame(kat_response.data)
    
    # Produkty
    prod_response = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = prod_response.data
    
    cleaned_data = []
    for item in data:
        kat_nazwa = item['Kategorie']['nazwa'] if item.get('Kategorie') else "⚠️ Nieprzypisana"
        cleaned_data.append({
            "ID": item['id'],
            "Nazwa Produktu": item['nazwa'],
            "Stan (szt.)": item['liczba'],
            "Cena (PLN)": item['cena'],
            "Kategoria": kat_nazwa,
            "kategoria_id_hidden": item['kategoria_id']
        })
    
    produkty_df = pd.DataFrame(cleaned_data)
    
    # Metryki
    if not produkty_df.empty:
        total_items = produkty_df["Stan (szt.)"].sum()
        total_value = (produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]).sum()
    else:
        total_items = 0
        total_value = 0
        
    return kategorie_df, produkty_df, total_items, total_value

# --- INTERFEJS ---

st.title("🔥 Gorący Magazyn")
st.caption("Panel zarządzania w wersji Spicy")
st.markdown("---")

kategorie_df, produkty_df, total_items_metric, total_value_metric = pobierz_dane_glowne()

# === METRYKI ===
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📦 Łącznie sztuk", value=f"{total_items_metric:,.0f}".replace(",", " "))
with m2:
    st.metric(label="💰 Wartość magazynu", value=f"{total_value_metric:,.2f} zł".replace(",", " "))
with m3:
    st.metric(label="🏷️ Kategorie", value=len(kategorie_df) if not kategorie_df.empty else 0)

st.markdown("---")

tab_prod, tab_kat = st.tabs(["🌶️ Produkty i Analiza", "📚 Kategorie"])

# === ZAKŁADKA 1 ===
with tab_prod:
    if produkty_df.empty:
        st.warning("Dodaj najpierw kategorie i produkty!")
    else:
        # --- WYKRESY Z CIEPŁĄ PALETĄ ---
        with st.expander("📈 Rozwiń Analitykę (Wersja Sunset)", expanded=True):
            col_chart1, col_chart2 = st.columns(2)
            
            df_chart_qty = produkty_df.groupby("Kategoria")["Stan (szt.)"].sum().reset_index()
            produkty_df["Wartosc_Pozycji"] = produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]
            df_chart_val = produkty_df.groupby("Kategoria")["Wartosc_Pozycji"].sum().reset_index()

            # Definicja ciepłej palety kolorów dla wykresów
            warm_scale = alt.Scale(range=['#FF4B4B', '#FF8C00', '#FFD700', '#E91E63', '#9C27B0'])

            with col_chart1:
                st.subheader("Ilość (Sztuki)")
                chart1 = alt.Chart(df_chart_qty).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x=alt.X('Kategoria', sort='-y', title=None),
                    y=alt.Y('Stan (szt.)', title='Suma'),
                    color=alt.Color('Kategoria', legend=None, scale=warm_scale),
                    tooltip=['Kategoria', 'Stan (szt.)']
                ).interactive()
                st.altair_chart(chart1, use_container_width=True)

            with col_chart2:
                st.subheader("Wartość (PLN)")
                chart2 = alt.Chart(df_chart_val).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x=alt.X('Kategoria', sort='-y', title=None),
                    y=alt.Y('Wartosc_Pozycji', title='Wartość'),
                    color=alt.Color('Kategoria', legend=None, scale=warm_scale),
                    tooltip=[alt.Tooltip('Kategoria'), alt.Tooltip('Wartosc_Pozycji', format=',.2f')]
                ).interactive()
                st.altair_chart(chart2, use_container_width=True)

        st.divider()

        # --- EDYCJA ---
        st.subheader("📋 Edycja Stanów (Inline)")
        
        edited_df = st.data_editor(
            produkty_df,
            key="product_editor",
            disabled=["ID", "Nazwa Produktu", "Kategoria", "kategoria_id_hidden"],
            column_config={
                "Cena (PLN)": st.column_config.NumberColumn(format="%.2f zł", min_value=0, step=0.01),
                "Stan (szt.)": st.column_config.NumberColumn(format="%d", min_value=0, step=1),
                "kategoria_id_hidden": None
            },
            use_container_width=True,
            hide_index=True
        )

        if not edited_df.equals(produkty_df):
            cols_to_check = ['Stan (szt.)', 'Cena (PLN)']
            diff = edited_df[cols_to_check].ne(produkty_df[cols_to_check]).any(axis=1)
            changed_rows = edited_df[diff]
            
            if not changed_rows.empty:
                with st.spinner("Zapisuję..."):
                    for index, row in changed_rows.iterrows():
                        try:
                            supabase.table('Produkty').update({
                                "liczba": int(row['Stan (szt.)']),
                                "cena": float(row['Cena (PLN)'])
                            }).eq('id', int(row['ID'])).execute()
                        except: pass
                    st.toast("Zmiany zapisane!", icon="🔥")
                    import time
                    time.sleep(0.5)
                    st.rerun()

    st.divider()

    # --- ZARZĄDZANIE ---
    c_add, c_del = st.columns(2)
    with c_add:
        with st.expander("➕ Dodaj Produkt"):
            if not kategorie_df.empty:
                opcje_kat = {r['nazwa']: r['id'] for i, r in kategorie_df.iterrows()}
                with st.form("add_p", clear_on_submit=True):
                    n = st.text_input("Nazwa")
                    l = st.number_input("Ilość", 0)
                    c = st.number_input("Cena", 0.0)
                    k = st.selectbox("Kategoria", list(opcje_kat.keys()))
                    if st.form_submit_button("Dodaj", type="primary"): # Primary button is RED
                        if n:
                            supabase.table('Produkty').insert({
                                "nazwa": n, "liczba": l, "cena": c, "kategoria_id": opcje_kat[k]
                            }).execute()
                            st.rerun()
    with c_del:
        with st.expander("🗑️ Usuń Produkt"):
            if not produkty_df.empty:
                d_list = {f"{r['Nazwa Produktu']} ({r['ID']})": r['ID'] for i, r in produkty_df.iterrows()}
                sel = st.selectbox("Wybierz", list(d_list.keys()))
                if st.button("Usuń", type="primary"): # Primary button is RED
                    supabase.table('Produkty').delete().eq('id', d_list[sel]).execute()
                    st.rerun()

# === ZAKŁADKA 2 ===
with tab_kat:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("📚 Kategorie")
        if not kategorie_df.empty:
            st.dataframe(kategorie_df[['nazwa', 'opis']], use_container_width=True, hide_index=True)
    with c2:
        st.subheader("⚙️ Nowa Kategoria")
        with st.form("add_k", clear_on_submit=True):
            kn = st.text_input("Nazwa")
            ko = st.text_area("Opis")
            if st.form_submit_button("Utwórz", type="primary"):
                if kn:
                    supabase.table('Kategorie').insert({"nazwa": kn, "opis": ko}).execute()
                    st.rerun()
        
        if not kategorie_df.empty:
            st.divider()
            st.write("Usuwanie kategorii:")
            k_del_names = [r['nazwa'] for i, r in kategorie_df.iterrows()]
            k_sel = st.selectbox("Którą usunąć?", k_del_names)
            if st.button("Usuń kategorię", type="secondary"):
                try:
                    kid = next(r['id'] for i, r in kategorie_df.iterrows() if r['nazwa'] == k_sel)
                    supabase.table('Kategorie').delete().eq('id', kid).execute()
                    st.rerun()
                except:
                    st.error("Nie można usunąć używanej kategorii!")
