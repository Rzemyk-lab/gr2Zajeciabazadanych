import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt

# --- KONFIGURACJA STRONY (MUSI BYĆ PIERWSZA) ---
st.set_page_config(
    page_title="Inventory Master Pro",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLIZACJA CSS (OPCJONALNE UPIĘKSZENIE) ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
        gap: 5px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-top: 3px solid #FF4B4B !important;
    }
</style>
""", unsafe_allow_html=True)


# --- ZAAWANSOWANE POŁĄCZENIE Z SUPABASE (CACHE) ---
@st.cache_resource
def init_connection():
    """Nawiązuje połączenie i cache'uje je, aby nie łączyć się przy każdym odświeżeniu."""
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
    """Pobiera i przetwarza wszystkie potrzebne dane w jednym rzucie."""
    # Pobierz kategorie
    kat_response = supabase.table('Kategorie').select("*").execute()
    kategorie_df = pd.DataFrame(kat_response.data)
    
    # Pobierz produkty z relacjami
    prod_response = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = prod_response.data
    
    cleaned_data = []
    for item in data:
        # Bezpieczne pobieranie nazwy kategorii
        kat_nazwa = item['Kategorie']['nazwa'] if item.get('Kategorie') else "⚠️ Nieprzypisana"
        cleaned_data.append({
            "ID": item['id'], # ID wielkimi literami, żeby nie edytować
            "Nazwa Produktu": item['nazwa'],
            "Stan (szt.)": item['liczba'],
            "Cena (PLN)": item['cena'],
            "Kategoria": kat_nazwa,
            "kategoria_id_hidden": item['kategoria_id'] # Ukryte ID do operacji bazodanowych
        })
    
    produkty_df = pd.DataFrame(cleaned_data)
    
    # Obliczenia do metryk
    if not produkty_df.empty:
        total_items = produkty_df["Stan (szt.)"].sum()
        total_value = (produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]).sum()
    else:
        total_items = 0
        total_value = 0
        
    return kategorie_df, produkty_df, total_items, total_value

# --- GŁÓWNY INTERFEJS ---

st.title("🏢 Centrum Zarządzania Magazynem")
st.markdown("---")

# Pobranie świeżych danych na początku
kategorie_df, produkty_df, total_items_metric, total_value_metric = pobierz_dane_glowne()

# === SEKCJA METRYK (DASHBOARD) ===
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📦 Łącznie sztuk w magazynie", value=f"{total_items_metric:,.0f}".replace(",", " "))
with m2:
    st.metric(label="💰 Całkowita wartość magazynu", value=f"{total_value_metric:,.2f} PLN".replace(",", " "))
with m3:
    st.metric(label="🗂️ Aktywne kategorie", value=len(kategorie_df) if not kategorie_df.empty else 0)

st.markdown("---")

# === ZAKŁADKI GŁÓWNE ===
tab_prod, tab_kat = st.tabs(["🛍️ Produkty i Operacje", "⚙️ Konfiguracja Kategorii"])

# ==================================================
# ZAKŁADKA 1: PRODUKTY (ZAAWANSOWANA)
# ==================================================
with tab_prod:
    if produkty_df.empty:
        st.info("🌟 Twój magazyn jest pusty. Rozpocznij od dodania kategorii, a następnie produktów.")
    else:
        # --- 1. ZAAWANSOWANE WYKRESY (ALTAIR) ---
        with st.expander("📊 Rozwiń Analitykę (Wykresy)", expanded=True):
            col_chart1, col_chart2 = st.columns(2)
            
            # Przygotowanie danych do wykresów
            df_chart_qty = produkty_df.groupby("Kategoria")["Stan (szt.)"].sum().reset_index()
            # Obliczamy wartość dla każdego produktu, potem grupujemy
            produkty_df["Wartosc_Pozycji"] = produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]
            df_chart_val = produkty_df.groupby("Kategoria")["Wartosc_Pozycji"].sum().reset_index()

            with col_chart1:
                st.subheader("Ilość sztuk wg kategorii")
                chart1 = alt.Chart(df_chart_qty).mark_bar().encode(
                    x=alt.X('Kategoria', sort='-y', title=None),
                    y=alt.Y('Stan (szt.)', title='Suma sztuk'),
                    color=alt.Color('Kategoria', legend=None, scale={"scheme": "tableau10"}),
                    tooltip=['Kategoria', 'Stan (szt.)']
                ).interactive()
                st.altair_chart(chart1, use_container_width=True)

            with col_chart2:
                st.subheader("Wartość wg kategorii (PLN)")
                chart2 = alt.Chart(df_chart_val).mark_bar().encode(
                    x=alt.X('Kategoria', sort='-y', title=None),
                    y=alt.Y('Wartosc_Pozycji', title='Wartość całkowita PLN'),
                    color=alt.Color('Kategoria', legend=None, scale={"scheme": "viridis"}),
                    tooltip=[alt.Tooltip('Kategoria'), alt.Tooltip('Wartosc_Pozycji', format=',.2f', title='Wartość PLN')]
                ).interactive()
                st.altair_chart(chart2, use_container_width=True)

        st.divider()

        # --- 2. INTERAKTYWNA TABELA (EDYCJA INLINE!) ---
        st.subheader("📋 Baza Produktów (Edytuj bezpośrednio w tabeli)")
        st.caption("💡 Kliknij dwukrotnie na komórkę 'Stan' lub 'Cena', aby ją edytować. Zmiany zapisują się automatycznie.")

        # Konfiguracja edytora danych
        edited_df = st.data_editor(
            produkty_df,
            key="product_editor",
            disabled=["ID", "Nazwa Produktu", "Kategoria", "kategoria_id_hidden"], # Tych kolumn nie chcemy edytować inline
            column_config={
                "Cena (PLN)": st.column_config.NumberColumn(format="%.2f zł", min_value=0, step=0.01, required=True),
                "Stan (szt.)": st.column_config.NumberColumn(format="%d", min_value=0, step=1, required=True),
                "kategoria_id_hidden": None # Ukrywamy kolumnę techniczną
            },
            use_container_width=True,
            hide_index=True,
            num_rows="fixed" # Zapobiega dodawaniu/usuwaniu wierszy w tym widoku
        )

        # --- OBSŁUGA ZMIAN W EDYTORZE ---
        # Sprawdzamy, czy stan edytora się zmienił w stosunku do oryginału
        if not edited_df.equals(produkty_df):
            # Znajdujemy zmienione wiersze
            # (Porównujemy tylko kolumny, które mogły być edytowane)
            cols_to_check = ['Stan (szt.)', 'Cena (PLN)']
            diff = edited_df[cols_to_check].ne(produkty_df[cols_to_check]).any(axis=1)
            changed_rows = edited_df[diff]
            
            if not changed_rows.empty:
                with st.spinner("Zapisuję zmiany w bazie danych..."):
                    success_count = 0
                    for index, row in changed_rows.iterrows():
                        try:
                            supabase.table('Produkty').update({
                                "liczba": int(row['Stan (szt.)']),
                                "cena": float(row['Cena (PLN)'])
                            }).eq('id', int(row['ID'])).execute()
                            success_count += 1
                        except Exception as e:
                             st.error(f"Błąd zapisu dla ID {row['ID']}: {e}")

                    if success_count > 0:
                        st.toast(f"✅ Zapisano zmiany w {success_count} produktach!", icon="💾")
                        # Małe opóźnienie i rerun, aby tabela się odświeżyła z nowymi danymi
                        import time
                        time.sleep(0.5)
                        st.rerun()


    st.divider()

    # --- 3. ZARZĄDZANIE (DODAWANIE / USUWANIE) ---
    col_add, col_del = st.columns(2)

    with col_add:
        with st.expander("➕ Dodaj Nowy Produkt", expanded=False):
            if kategorie_df.empty:
                st.warning("Najpierw dodaj kategorie w drugiej zakładce.")
            else:
                opcje_kat = {row['nazwa']: row['id'] for index, row in kategorie_df.iterrows()}
                with st.form("form_add_prod", clear_on_submit=True):
                    n_nazwa = st.text_input("Nazwa produktu*")
                    c1, c2 = st.columns(2)
                    n_liczba = c1.number_input("Stan początkowy", min_value=0, step=1, value=0)
                    n_cena = c2.number_input("Cena (PLN)", min_value=0.0, step=0.01, value=0.0)
                    n_kat_nazwa = st.selectbox("Kategoria*", options=list(opcje_kat.keys()))
                    
                    if st.form_submit_button("🚀 Utwórz produkt", type="primary"):
                        if n_nazwa and n_kat_nazwa:
                            try:
                                supabase.table('Produkty').insert({
                                    "nazwa": n_nazwa, "liczba": n_liczba, 
                                    "cena": n_cena, "kategoria_id": opcje_kat[n_kat_nazwa]
                                }).execute()
                                st.success("Produkt dodany pomyślnie!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Błąd bazy danych: {e}")
                        else:
                            st.warning("Uzupełnij wymagane pola (Nazwa i Kategoria).")

    with col_del:
        with st.expander("🗑️ Usuń Produkt", expanded=False):
             if produkty_df.empty:
                st.write("Brak produktów do usunięcia.")
             else:
                # Używamy selectboxa z nazwami zamiast wpisywania ID ręcznie - bezpieczniej
                opcje_usuwania = {f"{row['Nazwa Produktu']} (ID: {row['ID']})": row['ID'] for index, row in produkty_df.iterrows()}
                selected_to_delete_label = st.selectbox("Wybierz produkt do trwałego usunięcia", options=list(opcje_usuwania.keys()))
                
                if st.button("🔥 Potwierdź usunięcie", type="secondary"):
                    id_to_del = opcje_usuwania[selected_to_delete_label]
                    try:
                        supabase.table('Produkty').delete().eq('id', id_to_del).execute()
                        st.toast(f"Produkt usunięty!", icon="🗑️")
                        st.rerun()
                    except Exception as e:
                         st.error(f"Nie udało się usunąć: {e}")

# ==================================================
# ZAKŁADKA 2: KATEGORIE
# ==================================================
with tab_kat:
    col_k_list, col_k_actions = st.columns([3, 2])
    
    with col_k_list:
        st.subheader("🗂️ Zdefiniowane Kategorie")
        if not kategorie_df.empty:
             # Używamy data editora również tutaj, ale tylko do podglądu (disabled)
             # Można włączyć edycję opisów, jeśli chcesz
             st.data_editor(
                 kategorie_df[['id', 'nazwa', 'opis']], 
                 disabled=["id", "nazwa", "opis"], 
                 hide_index=True, use_container_width=True,
                 column_config={"id": st.column_config.TextColumn("ID", width="small")}
             )
        else:
            st.info("Brak zdefiniowanych kategorii.")

    with col_k_actions:
        st.subheader("⚙️ Operacje")
        with st.expander("✨ Utwórz Kategorię", expanded=True):
            with st.form("form_new_kat", clear_on_submit=True):
                k_nazwa = st.text_input("Nazwa kategorii*", placeholder="np. Elektronika")
                k_opis = st.text_area("Opis (opcjonalnie)", placeholder="Krótki opis...")
                
                if st.form_submit_button("Dodaj kategorię", type="primary"):
                    if k_nazwa:
                        supabase.table('Kategorie').insert({"nazwa": k_nazwa, "opis": k_opis}).execute()
                        st.toast("Kategoria dodana!", icon="✨")
                        st.rerun()
                    else:
                        st.warning("Nazwa kategorii jest wymagana.")

        if not kategorie_df.empty:
             with st.expander("⚠️ Usuń Kategorię"):
                st.warning("Uwaga: Nie można usunąć kategorii, do której są przypisane produkty.")
                kat_del_list = {row['nazwa']: row['id'] for index, row in kategorie_df.iterrows()}
                kat_to_del_name = st.selectbox("Wybierz kategorię", options=list(kat_del_list.keys()))
                
                if st.button("Potwierdź usunięcie kategorii"):
                    try:
                        supabase.table('Kategorie').delete().eq('id', kat_del_list[kat_to_del_name]).execute()
                        st.success("Kategoria usunięta.")
                        st.rerun()
                    except Exception as e:
                        st.error("⛔ Nie można usunąć tej kategorii. Prawdopodobnie są do niej przypisane produkty.") w tym kodzie nie działa Ilość sztuk wg kategorii wykres 
