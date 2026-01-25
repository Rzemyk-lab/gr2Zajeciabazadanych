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
    initial_sidebar_state="collapsed"
)

# --- 2. STYLIZACJA CSS ---
st.markdown("""
<style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
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

# --- 3. POŁĄCZENIE Z SUPABASE ---
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

# --- 4. FUNKCJE LOGIKI BIZNESOWEJ ---

def pobierz_dane_glowne():
    """Pobiera i przetwarza dane o produktach i kategoriach."""
    kat_response = supabase.table('Kategorie').select("*").execute()
    kategorie_df = pd.DataFrame(kat_response.data)
    
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
    
    if not produkty_df.empty:
        total_items = produkty_df["Stan (szt.)"].sum()
        total_value = (produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]).sum()
    else:
        total_items, total_value = 0, 0
        
    return kategorie_df, produkty_df, total_items, total_value

# --- 5. LOGIKA GRY DOKOBAN ---

def init_sokoban():
    if 'sokoban_map' not in st.session_state:
        # 0: puste, 1: ściana, 2: cel, 3: skrzynia, 4: gracz
        st.session_state.sokoban_map = [
            [1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [1, 0, 2, 3, 4, 0, 1],
            [1, 0, 0, 3, 2, 0, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ]
        st.session_state.sokoban_pos = [2, 4]

def move_player(dy, dx):
    curr_y, curr_x = st.session_state.sokoban_pos
    ny, nx = curr_y + dy, curr_x + dx
    grid = st.session_state.sokoban_map
    targets = [(2, 2), (3, 4)] # Współrzędne celów (y, x)

    def get_cell_after_move(y, x):
        return 2 if (y, x) in targets else 0

    # Ruch na puste pole lub cel
    if grid[ny][nx] in [0, 2]:
        grid[curr_y][curr_x] = get_cell_after_move(curr_y, curr_x)
        grid[ny][nx] = 4
        st.session_state.sokoban_pos = [ny, nx]
    
    # Przesuwanie skrzyni
    elif grid[ny][nx] == 3:
        nny, nnx = ny + dy, nx + dx
        if grid[nny][nnx] in [0, 2]:
            grid[nny][nnx] = 3
            grid[ny][nx] = 4
            grid[curr_y][curr_x] = get_cell_after_move(curr_y, curr_x)
            st.session_state.sokoban_pos = [ny, nx]

# --- 6. GŁÓWNY INTERFEJS ---

st.title("🏢 Centrum Zarządzania Magazynem")
st.markdown("---")

kategorie_df, produkty_df, total_items_metric, total_value_metric = pobierz_dane_glowne()

# Metryki Dashboardu
m1, m2, m3 = st.columns(3)
with m1:
    st.metric(label="📦 Łącznie sztuk", value=f"{total_items_metric:,.0f}".replace(",", " "))
with m2:
    st.metric(label="💰 Wartość magazynu", value=f"{total_value_metric:,.2f} PLN".replace(",", " "))
with m3:
    st.metric(label="🗂️ Aktywne kategorie", value=len(kategorie_df) if not kategorie_df.empty else 0)

st.markdown("---")

tab_prod, tab_kat, tab_game = st.tabs(["🛍️ Produkty", "⚙️ Kategorie", "📦 Przerwa: Dokoban"])

# --- TAB: PRODUKTY ---
with tab_prod:
    if produkty_df.empty:
        st.info("🌟 Magazyn jest pusty. Dodaj kategorie i produkty.")
    else:
        with st.expander("📊 Analityka", expanded=True):
            col_chart1, col_chart2 = st.columns(2)
            df_chart_qty = produkty_df.groupby("Kategoria")["Stan (szt.)"].sum().reset_index()
            produkty_df["Wartosc_Pozycji"] = produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]
            df_chart_val = produkty_df.groupby("Kategoria")["Wartosc_Pozycji"].sum().reset_index()

            with col_chart1:
                st.altair_chart(alt.Chart(df_chart_qty).mark_bar().encode(
                    x=alt.X('Kategoria', sort='-y'), y='Stan (szt.)', color='Kategoria'
                ).interactive(), use_container_width=True)
            with col_chart2:
                st.altair_chart(alt.Chart(df_chart_val).mark_bar().encode(
                    x=alt.X('Kategoria', sort='-y'), y='Wartosc_Pozycji', color='Kategoria'
                ).interactive(), use_container_width=True)

        st.subheader("📋 Baza Produktów")
        edited_df = st.data_editor(
            produkty_df,
            key="product_editor",
            disabled=["ID", "Nazwa Produktu", "Kategoria", "kategoria_id_hidden", "Wartosc_Pozycji"],
            column_config={
                "Cena (PLN)": st.column_config.NumberColumn(format="%.2f zł", min_value=0),
                "Stan (szt.)": st.column_config.NumberColumn(min_value=0),
                "kategoria_id_hidden": None, "Wartosc_Pozycji": None
            },
            use_container_width=True, hide_index=True
        )

        if not edited_df.equals(produkty_df):
            cols_to_check = ['Stan (szt.)', 'Cena (PLN)']
            diff = edited_df[cols_to_check].ne(produkty_df[cols_to_check]).any(axis=1)
            changed_rows = edited_df[diff]
            
            if not changed_rows.empty:
                for _, row in changed_rows.iterrows():
                    supabase.table('Produkty').update({
                        "liczba": int(row['Stan (szt.)']), "cena": float(row['Cena (PLN)'])
                    }).eq('id', int(row['ID'])).execute()
                st.toast("✅ Zmiany zapisane!")
                time.sleep(0.5)
                st.rerun()

    st.divider()
    c_add, c_del = st.columns(2)
    with c_add:
        with st.expander("➕ Dodaj Produkt"):
            if not kategorie_df.empty:
                opcje_kat = {row['nazwa']: row['id'] for _, row in kategorie_df.iterrows()}
                with st.form("add_p", clear_on_submit=True):
                    n_nazwa = st.text_input("Nazwa*")
                    n_liczba = st.number_input("Stan", min_value=0)
                    n_cena = st.number_input("Cena", min_value=0.0)
                    n_kat = st.selectbox("Kategoria*", options=list(opcje_kat.keys()))
                    if st.form_submit_button("Utwórz"):
                        supabase.table('Produkty').insert({
                            "nazwa": n_nazwa, "liczba": n_liczba, "cena": n_cena, "kategoria_id": opcje_kat[n_kat]
                        }).execute()
                        st.rerun()
    with c_del:
        with st.expander("🗑️ Usuń Produkt"):
            if not produkty_df.empty:
                opcje_del = {f"{r['Nazwa Produktu']} (ID:{r['ID']})": r['ID'] for _, r in produkty_df.iterrows()}
                target = st.selectbox("Wybierz", list(opcje_del.keys()))
                if st.button("Usuń trwale"):
                    supabase.table('Produkty').delete().eq('id', opcje_del[target]).execute()
                    st.rerun()

# --- TAB: KATEGORIE ---
with tab_kat:
    ck1, ck2 = st.columns([3, 2])
    with ck1:
        st.subheader("🗂️ Kategorie")
        st.data_editor(kategorie_df[['id', 'nazwa', 'opis']], disabled=True, hide_index=True)
    with ck2:
        st.subheader("⚙️ Operacje")
        with st.form("new_k", clear_on_submit=True):
            kn = st.text_input("Nazwa*")
            ko = st.text_area("Opis")
            if st.form_submit_button("Dodaj"):
                if kn: 
                    supabase.table('Kategorie').insert({"nazwa": kn, "opis": ko}).execute()
                    st.rerun()
        if not kategorie_df.empty:
            with st.expander("⚠️ Usuń Kategorię"):
                k_list = {r['nazwa']: r['id'] for _, r in kategorie_df.iterrows()}
                k_target = st.selectbox("Kategoria", list(k_list.keys()))
                if st.button("Potwierdź usunięcie"):
                    try:
                        supabase.table('Kategorie').delete().eq('id', k_list[k_target]).execute()
                        st.rerun()
                    except: st.error("Nie można usunąć kategorii z przypisanymi produktami.")

# --- TAB: GRA DOKOBAN ---
with tab_game:
    st.subheader("🎮 Dokoban - Magazynowe Wyzwanie")
    st.caption("Przesuń skrzynie 📦 na miejsca docelowe 🎯 za pomocą przycisków.")
    
    init_sokoban()
    icons = {0: "⬜", 1: "🧱", 2: "🎯", 3: "📦", 4: "👷"}
    
    # Renderowanie planszy
    for row in st.session_state.sokoban_map:
        cols = st.columns(len(row) + 10) # Szerokie kolumny dla wycentrowania
        for idx, cell in enumerate(row):
            cols[idx].write(icons[cell])

    st.markdown("---")
    # Sterowanie
    gc1, gc2, gc3 = st.columns([1, 1, 1])
    with gc2:
        st.button("🔼 Góra", on_click=move_player, args=(-1, 0), use_container_width=True)
        gl, gr = st.columns(2)
        gl.button("◀️ Lewo", on_click=move_player, args=(0, -1), use_container_width=True)
        gr.button("▶️ Prawo", on_click=move_player, args=(0, 1), use_container_width=True)
        st.button("🔽 Dół", on_click=move_player, args=(1, 0), use_container_width=True)
        
        if st.button("🔄 Resetuj poziom", type="secondary"):
            if 'sokoban_map' in st.session_state:
                del st.session_state.sokoban_map
            st.rerun()

    # Warunek wygranej
    grid = st.session_state.sokoban_map
    if grid[2][2] == 3 and grid[3][4] == 3:
        st.balloons()
        st.success("🏆 Brawo! Wszystkie skrzynie na miejscu!")
