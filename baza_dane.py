import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Inventory Master Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. STYLIZACJA CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [aria-selected="true"] { border-top: 3px solid #FF4B4B !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error("❌ Błąd połączenia z bazą danych.")
        st.stop()

supabase = init_connection()

# --- 4. LOGIKA POBIERANIA DANYCH ---
def pobierz_dane():
    # Pobierz Kategorie
    kat_res = supabase.table('Kategorie').select("*").execute()
    df_kat = pd.DataFrame(kat_res.data)
    
    # Pobierz Produkty
    prod_res = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = prod_res.data
    
    cleaned = []
    for i in data:
        cleaned.append({
            "ID": i['id'],
            "Nazwa Produktu": i['nazwa'],
            "Stan (szt.)": i['liczba'],
            "Cena (PLN)": i['cena'],
            "Kategoria": i['Kategorie']['nazwa'] if i.get('Kategorie') else "Brak",
            "kat_id": i['kategoria_id']
        })
    df_prod = pd.DataFrame(cleaned)
    
    # Metryki
    total_val = (df_prod["Stan (szt.)"] * df_prod["Cena (PLN)"]).sum() if not df_prod.empty else 0
    return df_kat, df_prod, total_val

# --- 5. SIDEBAR (MAPA I INFO) ---
with st.sidebar:
    st.header("📍 Lokalizacja Magazynów")
    
    # Przykładowe dane lokalizacji (np. Warszawa, Wrocław, Gdańsk)
    map_data = pd.DataFrame({
        'lat': [52.2297, 51.1079, 54.3520],
        'lon': [21.0122, 17.0385, 18.6466],
        'name': ['Magazyn Centralny', 'Oddział Zachód', 'Punkt Północ']
    })
    
    st.map(map_data, zoom=5, use_container_width=True)
    
    st.info(f"**Status:** System Online\n\n**Ostatnia synchronizacja:** {time.strftime('%H:%M:%S')}")
    if st.button("🔄 Odśwież dane"):
        st.rerun()

# --- 6. GŁÓWNY INTERFEJS ---
st.title("🏢 Centrum Zarządzania Magazynem")
df_kat, df_prod, val_metric = pobierz_dane()

# Metryki
m1, m2, m3 = st.columns(3)
m1.metric("📦 Sztuk ogółem", f"{df_prod['Stan (szt.)'].sum():,.0f}".replace(",", " "))
m2.metric("💰 Wartość netto", f"{val_metric:,.2f} PLN")
m3.metric("🗂️ Kategorie", len(df_kat))

tab_p, tab_k = st.tabs(["🛍️ Produkty", "⚙️ Konfiguracja"])

# --- TAB: PRODUKTY ---
with tab_p:
    if df_prod.empty:
        st.info("Brak produktów.")
    else:
        # Wykresy
        with st.expander("📊 Analityka"):
            c1, c2 = st.columns(2)
            chart_data = df_prod.groupby("Kategoria").agg({"Stan (szt.)": "sum", "ID": "count"}).reset_index()
            
            with c1:
                st.altair_chart(alt.Chart(chart_data).mark_bar().encode(
                    x='Kategoria', y='Stan (szt.)', color='Kategoria'
                ), use_container_width=True)
            with c2:
                st.altair_chart(alt.Chart(df_prod).mark_arc().encode(
                    theta='Stan (szt.)', color='Kategoria'
                ), use_container_width=True)

        # Edytor
        st.subheader("📋 Edycja zasobów")
        edited = st.data_editor(
            df_prod,
            key="main_editor",
            disabled=["ID", "Nazwa Produktu", "Kategoria", "kat_id"],
            column_config={"kat_id": None},
            hide_index=True, use_container_width=True
        )

        # Zapis zmian
        if not edited.equals(df_prod):
            diff = edited[edited['Stan (szt.)'] != df_prod['Stan (szt.)']]
            for _, row in diff.iterrows():
                supabase.table('Produkty').update({"liczba": int(row['Stan (szt.)'])}).eq('id', row['ID']).execute()
            st.toast("Zapisano zmiany!", icon="💾")
            time.sleep(0.5)
            st.rerun()

    # Zarządzanie (Dodaj/Usuń)
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("➕ Nowy Produkt"):
            with st.form("add_p", clear_on_submit=True):
                n_name = st.text_input("Nazwa")
                n_qty = st.number_input("Ilość", min_value=0)
                n_price = st.number_input("Cena", min_value=0.0)
                n_k = st.selectbox("Kategoria", options=df_kat['nazwa'].tolist())
                if st.form_submit_button("Dodaj"):
                    k_id = df_kat[df_kat['nazwa'] == n_k]['id'].iloc[0]
                    supabase.table('Produkty').insert({"nazwa": n_name, "liczba": n_qty, "cena": n_price, "kategoria_id": k_id}).execute()
                    st.rerun()
    with col_b:
        with st.expander("🗑️ Usuń Produkt"):
            to_del = st.selectbox("Wybierz do usunięcia", df_prod['Nazwa Produktu'].tolist() if not df_prod.empty else [])
            if st.button("Potwierdź usunięcie"):
                id_d = df_prod[df_prod['Nazwa Produktu'] == to_del]['ID'].iloc[0]
                supabase.table('Produkty').delete().eq('id', id_d).execute()
                st.rerun()

# --- TAB: KATEGORIE ---
with tab_k:
    st.subheader("🗂️ Zarządzanie Kategoriami")
    col_k1, col_k2 = st.columns([2, 1])
    with col_k1:
        st.dataframe(df_kat, use_container_width=True, hide_index=True)
    with col_k2:
        with st.form("new_kat"):
            nk = st.text_input("Nowa kategoria")
            if st.form_submit_button("Dodaj kategorię"):
                supabase.table('Kategorie').insert({"nazwa": nk}).execute()
                st.rerun()
