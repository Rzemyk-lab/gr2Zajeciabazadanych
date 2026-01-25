import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Inventory Master Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLIZACJA CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        padding: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-top: 3px solid #FF4B4B !important;
    }
</style>
""", unsafe_allow_html=True)

# --- POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("❌ Błąd krytyczny: Brak sekretów połączenia z bazą danych.")
        st.stop()

supabase = init_connection()

# --- FUNKCJE LOGIKI BIZNESOWEJ ---

def pobierz_dane_glowne():
    # Pobierz kategorie
    kat_response = supabase.table('Kategorie').select("*").execute()
    kategorie_df = pd.DataFrame(kat_response.data)
    
    # Pobierz produkty
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
    
    # Konwersja typów dla stabilności obliczeń i wykresów
    if not produkty_df.empty:
        produkty_df["Stan (szt.)"] = pd.to_numeric(produkty_df["Stan (szt.)"], errors='coerce').fillna(0)
        produkty_df["Cena (PLN)"] = pd.to_numeric(produkty_df["Cena (PLN)"], errors='coerce').fillna(0)
        produkty_df["Wartosc_Pozycji"] = produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]
        
        total_items = produkty_df["Stan (szt.)"].sum()
        total_value = produkty_df["Wartosc_Pozycji"].sum()
    else:
        total_items = 0
        total_value = 0
        
    return kategorie_df, produkty_df, total_items, total_value

# --- GŁÓWNY INTERFEJS ---

st.title("🏢 Centrum Zarządzania Magazynem")
st.markdown("---")

kategorie_df, produkty_df, total_items_metric, total_value_metric = pobierz_dane_glowne()

# === DASHBOARD METRYK ===
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📦 Łącznie sztuk", value=f"{total_items_metric:,.0f}".replace(",", " "))
with m2:
    st.metric(label="💰 Wartość magazynu", value=f"{total_value_metric:,.2f} PLN".replace(",", " "))
with m3:
    st.metric(label="🗂️ Kategorie", value=len(kategorie_df) if not kategorie_df.empty else 0)

st.markdown("---")

tab_prod, tab_kat = st.tabs(["🛍️ Produkty i Operacje", "⚙️ Konfiguracja Kategorii"])

# ==================================================
# ZAKŁADKA 1: PRODUKTY
# ==================================================
with tab_prod:
    if produkty_df.empty:
        st.info("🌟 Magazyn jest pusty. Dodaj kategorie i produkty.")
    else:
        # --- ANALITYKA (WYKRESY) ---
        with st.expander("📊 Rozwiń Analitykę (Wykresy)", expanded=True):
            col_chart1, col_chart2 = st.columns(2)
            
            # Grupowanie danych
            df_qty = produkty_df.groupby("Kategoria")["Stan (szt.)"].sum().reset_index()
            df_val = produkty_df.groupby("Kategoria")["Wartosc_Pozycji"].sum().reset_index()

            with col_chart1:
                st.subheader("Ilość sztuk wg kategorii")
                c1 = alt.Chart(df_qty).mark_bar().encode(
                    x=alt.X('Kategoria:N', sort='-y', title=None),
                    y=alt.Y('Stan (szt.):Q', title='Suma sztuk'),
                    color=alt.Color('Kategoria:N', legend=None, scale={"scheme": "tableau10"}),
                    tooltip=['Kategoria', 'Stan (szt.)']
                ).properties(height=300).interactive()
                st.altair_chart(c1, use_container_width=True)

            with col_chart2:
                st.subheader("Wartość wg kategorii (PLN)")
                c2 = alt.Chart(df_val).mark_bar().encode(
                    x=alt.X('Kategoria:N', sort='-y', title=None),
                    y=alt.Y('Wartosc_Pozycji:Q', title='Wartość PLN'),
                    color=alt.Color('Kategoria:N', legend=None, scale={"scheme": "viridis"}),
                    tooltip=['Kategoria', alt.Tooltip('Wartosc_Pozycji', format=',.2f')]
                ).properties(height=300).interactive()
                st.altair_chart(c2, use_container_width=True)

        st.divider()

        # --- EDYTOR TABELI ---
        st.subheader("📋 Baza Produktów")
        edited_df = st.data_editor(
            produkty_df,
            key="prod_editor",
            disabled=["ID", "Nazwa Produktu", "Kategoria", "kategoria_id_hidden", "Wartosc_Pozycji"],
            column_config={
                "Cena (PLN)": st.column_config.NumberColumn(format="%.2f zł", min_value=0),
                "Stan (szt.)": st.column_config.NumberColumn(format="%d", min_value=0),
                "kategoria_id_hidden": None,
                "Wartosc_Pozycji": st.column_config.NumberColumn("Wartość", format="%.2f zł")
            },
            use_container_width=True,
            hide_index=True
        )

        # Zapis zmian inline
        if not edited_df.equals(produkty_df):
            # Porównujemy tylko kolumny edytowalne
            cols = ['Stan (szt.)', 'Cena (PLN)']
            diff = edited_df[cols].ne(produkty_df[cols]).any(axis=1)
            changes = edited_df[diff]
            
            if not changes.empty:
                for _, row in changes.iterrows():
                    supabase.table('Produkty').update({
                        "liczba": int(row['Stan (szt.)']),
                        "cena": float(row['Cena (PLN)'])
                    }).eq('id', int(row['ID'])).execute()
                st.toast("Zapisano zmiany!", icon="💾")
                time.sleep(0.5)
                st.rerun()

    st.divider()

    # --- DODAWANIE / USUWANIE ---
    c_add, c_del = st.columns(2)
    with c_add:
        with st.expander("➕ Dodaj Produkt"):
            if kategorie_df.empty:
                st.warning("Dodaj najpierw kategorię.")
            else:
                kat_map = {r['nazwa']: r['id'] for _, r in kategorie_df.iterrows()}
                with st.form("add_p", clear_on_submit=True):
                    name = st.text_input("Nazwa*")
                    col1, col2 = st.columns(2)
                    qty = col1.number_input("Stan", min_value=0, value=0)
                    prc = col2.number_input("Cena", min_value=0.0, value=0.0)
                    cat = st.selectbox("Kategoria*", options=list(kat_map.keys()))
                    if st.form_submit_button("Dodaj"):
                        if name:
                            supabase.table('Produkty').insert({
                                "nazwa": name, "liczba": qty, "cena": prc, "kategoria_id": kat_map[cat]
                            }).execute()
                            st.rerun()

    with c_del:
        with st.expander("🗑️ Usuń Produkt"):
            if not produkty_df.empty:
                p_map = {f"{r['Nazwa Produktu']} (ID: {r['ID']})": r['ID'] for _, r in produkty_df.iterrows()}
                to_del = st.selectbox("Produkt", options=list(p_map.keys()))
                if st.button("Usuń trwale"):
                    supabase.table('Produkty').delete().eq('id', p_map[to_del]).execute()
                    st.rerun()

# ==================================================
# ZAKŁADKA 2: KATEGORIE
# ==================================================
with tab_kat:
    ck1, ck2 = st.columns([3, 2])
    with ck1:
        st.subheader("🗂️ Lista Kategorii")
        if not kategorie_df.empty:
            st.dataframe(kategorie_df[['id', 'nazwa', 'opis']], use_container_width=True, hide_index=True)
    
    with ck2:
        st.subheader("⚙️ Zarządzaj")
        with st.expander("✨ Nowa Kategoria", expanded=True):
            with st.form("add_k"):
                k_n = st.text_input("Nazwa*")
                k_o = st.text_area("Opis")
                if st.form_submit_button("Dodaj"):
                    if k_n:
                        supabase.table('Kategorie').insert({"nazwa": k_n, "opis": k_o}).execute()
                        st.rerun()
