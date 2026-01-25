import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt
import time
import random

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
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-top: 3px solid #FF4B4B !important;
    }
    /* Styl dla planszy Snake */
    .snake-board {
        font-family: monospace;
        line-height: 1.2;
        font-size: 20px;
        background-color: #222;
        color: #eee;
        padding: 10px;
        border-radius: 5px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- ZAAWANSOWANE POŁĄCZENIE Z SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("❌ Błąd krytyczny: Brak sekretów połączenia.")
        st.stop()

supabase = init_connection()

# --- FUNKCJE LOGIKI BIZNESOWEJ ---
def pobierz_dane_glowne():
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
    total_items = produkty_df["Stan (szt.)"].sum() if not produkty_df.empty else 0
    total_value = (produkty_df["Stan (szt.)"] * produkty_df["Cena (PLN)"]).sum() if not produkty_df.empty else 0
    return kategorie_df, produkty_df, total_items, total_value

# --- INTERFEJS ---
st.title("🏢 Centrum Zarządzania Magazynem")
st.markdown("---")

kategorie_df, produkty_df, total_items_metric, total_value_metric = pobierz_dane_glowne()

# DASHBOARD METRYK
m1, m2, m3 = st.columns(3)
with m1: st.metric(label="📦 Łącznie sztuk", value=f"{total_items_metric:,.0f}".replace(",", " "))
with m2: st.metric(label="💰 Wartość magazynu", value=f"{total_value_metric:,.2f} PLN".replace(",", " "))
with m3: st.metric(label="🗂️ Aktywne kategorie", value=len(kategorie_df) if not kategorie_df.empty else 0)

st.markdown("---")

tab_prod, tab_kat, tab_game = st.tabs(["🛍️ Produkty i Operacje", "⚙️ Konfiguracja Kategorii", "🐍 Przerwa na Snake'a"])

# ZAKŁADKA 1 i 2 (Skrócone dla czytelności, Twoja logika pozostaje bez zmian)
with tab_prod:
    if produkty_df.empty:
        st.info("🌟 Magazyn jest pusty.")
    else:
        # Wykresy i Edytor (Z zachowaniem Twojej logiki zapisu)
        st.subheader("📋 Baza Produktów")
        edited_df = st.data_editor(produkty_df, use_container_width=True, hide_index=True)
        # ... (Tutaj Twoja logika zapisu do bazy) ...

with tab_kat:
    st.subheader("⚙️ Zarządzanie Kategoriami")
    # ... (Tutaj Twoja logika dodawania/usuwania kategorii) ...

# ==================================================
# ZAKŁADKA 3: GRA SNAKE
# ==================================================
with tab_game:
    st.subheader("🎮 Snake: Biurowa Przerwa")
    st.write("Użyj przycisków poniżej, aby sterować wężem. Zbieraj jabłka (🍎)!")

    # Inicjalizacja stanu gry
    if 'snake' not in st.session_state:
        st.session_state.snake = [(5, 5), (5, 6), (5, 7)]
        st.session_state.direction = 'UP'
        st.session_state.food = (10, 10)
        st.session_state.score = 0
        st.session_state.game_over = False

    def reset_game():
        st.session_state.snake = [(5, 5), (5, 6), (5, 7)]
        st.session_state.direction = 'UP'
        st.session_state.food = (random.randint(0, 14), random.randint(0, 14))
        st.session_state.score = 0
        st.session_state.game_over = False

    # Sterowanie
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2: 
        if st.button("⬆️ Góra"): st.session_state.direction = 'UP'
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1: 
        if st.button("⬅️ Lewo"): st.session_state.direction = 'LEFT'
    with c2:
        if st.button("🔄 Reset"): reset_game()
    with c3: 
        if st.button("➡️ Prawo"): st.session_state.direction = 'RIGHT'
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2: 
        if st.button("⬇️ Dół"): st.session_state.direction = 'DOWN'

    # Mechanika gry
    game_placeholder = st.empty()
    
    if not st.session_state.game_over:
        # Logika ruchu
        head_x, head_y = st.session_state.snake[0]
        if st.session_state.direction == 'UP': head_x -= 1
        elif st.session_state.direction == 'DOWN': head_x += 1
        elif st.session_state.direction == 'LEFT': head_y -= 1
        elif st.session_state.direction == 'RIGHT': head_y += 1

        new_head = (head_x, head_y)

        # Kolizje ze ścianami lub samym sobą
        if (head_x < 0 or head_x >= 15 or head_y < 0 or head_y >= 15 or 
            new_head in st.session_state.snake):
            st.session_state.game_over = True
        else:
            st.session_state.snake.insert(0, new_head)
            # Jedzenie
            if new_head == st.session_state.food:
                st.session_state.score += 1
                st.session_state.food = (random.randint(0, 14), random.randint(0, 14))
            else:
                st.session_state.snake.pop()

    # Rysowanie planszy
    board = [["░" for _ in range(15)] for _ in range(15)]
    fx, fy = st.session_state.food
    board[fx][fy] = "🍎"
    for idx, (sx, sy) in enumerate(st.session_state.snake):
        board[sx][sy] = "🟢" if idx == 0 else "🟩"

    board_str = "\n".join(["".join(row) for row in board])
    
    with game_placeholder.container():
        if st.session_state.game_over:
            st.error(f"Koniec gry! Twój wynik: {st.session_state.score}")
            if st.button("Zagraj jeszcze raz"): reset_game()
        else:
            st.markdown(f'<div class="snake-board">{board_str}</div>', unsafe_allow_html=True)
            st.write(f"Punkty: **{st.session_state.score}**")
            time.sleep(0.3)
            st.rerun()
