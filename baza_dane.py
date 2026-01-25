import streamlit as st
from supabase import create_client, Client
import pandas as pd
import altair as alt
import time
import random

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(
    page_title="Inventory Pro + Snake",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. STYLIZACJA CSS ---
st.markdown("""
<style>
    .stApp { background-color: #FFFBF5; }
    div[data-testid="metric-container"] {
        background-color: #FFFFFF;
        border-left: 6px solid #FF8C00;
        padding: 15px; border-radius: 8px;
    }
    [data-testid="stMetricValue"] { color: #D35400 !important; }
    .snake-board {
        font-family: monospace; font-size: 18px; line-height: 1;
        background-color: #222; color: #0f0; padding: 10px;
        border-radius: 10px; text-align: center; border: 3px solid #5D4037;
    }
    h1, h2, h3 { color: #5D4037 !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. POŁĄCZENIE Z BAZĄ (CACHE) ---
@st.cache_resource
def init_connection():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Błąd połączenia z bazą danych!")
        st.stop()

supabase = init_connection()

# --- 4. FUNKCJE DANYCH ---
def pobierz_wszystko():
    # Kategorie
    k_res = supabase.table('Kategorie').select("*").execute()
    df_k = pd.DataFrame(k_res.data)
    
    # Produkty
    p_res = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = p_res.data
    
    clean = []
    for i in data:
        kat_n = i['Kategorie']['nazwa'] if i.get('Kategorie') else "Brak"
        clean.append({
            "id": i['id'],
            "nazwa": i['nazwa'],
            "liczba": i['liczba'],
            "cena": i['cena'],
            "kategoria": kat_n,
            "kategoria_id": i['kategoria_id']
        })
    df_p = pd.DataFrame(clean)
    
    val = (df_p["liczba"] * df_p["cena"]).sum() if not df_p.empty else 0
    szt = df_p["liczba"].sum() if not df_p.empty else 0
    
    return df_k, df_p, szt, val

# --- 5. LOGIKA GRY SNAKE ---
def init_snake():
    if 'snake' not in st.session_state:
        st.session_state.snake = [(5, 5), (5, 6)]
        st.session_state.direction = 'UP'
        st.session_state.food = (2, 2)
        st.session_state.score = 0
        st.session_state.game_over = False

# --- 6. INTERFEJS GŁÓWNY ---
st.title("🏢 Magazyn & Chill")

df_k, df_p, total_szt, total_val = pobierz_wszystko()

# METRYKI
c1, c2, c3 = st.columns(3)
c1.metric("📦 Sztuk ogółem", f"{total_szt:,.0f}")
c2.metric("💰 Wartość", f"{total_val:,.2f} zł")
c3.metric("🏷️ Kategorie", len(df_k))

tab_mag, tab_kat, tab_snake = st.tabs(["🛍️ Magazyn", "⚙️ Kategorie", "🐍 Snake Time"])

# --- TAB: MAGAZYN ---
with tab_mag:
    if not df_p.empty:
        # WYKRES (Naprawiony Altair)
        with st.expander("📊 Wykresy stanów", expanded=True):
            chart_data = df_p.groupby("kategoria")["liczba"].sum().reset_index()
            # Używamy prostych nazw kolumn dla Altair
            c = alt.Chart(chart_data).mark_bar(color='#FF8C00', cornerRadius=5).encode(
                x=alt.X('kategoria:N', title="Kategoria"),
                y=alt.Y('liczba:Q', title="Suma sztuk"),
                tooltip=['kategoria', 'liczba']
            ).properties(height=300)
            st.altair_chart(c, use_container_width=True)

        # TABELA
        st.subheader("📋 Produkty")
        # Wyświetlamy ładne nazwy, ale edytujemy oryginał
        edited = st.data_editor(
            df_p[["id", "nazwa", "liczba", "cena", "kategoria"]],
            hide_index=True, use_container_width=True,
            disabled=["id", "nazwa", "kategoria"],
            key="editor"
        )
        
        # Zapis zmian w tabeli
        if not edited.equals(df_p[["id", "nazwa", "liczba", "cena", "kategoria"]]):
            for idx, row in edited.iterrows():
                orig = df_p.iloc[idx]
                if row['liczba'] != orig['liczba'] or row['cena'] != orig['cena']:
                    supabase.table('Produkty').update({
                        "liczba": int(row['liczba']), "cena": float(row['cena'])
                    }).eq('id', int(row['id'])).execute()
            st.toast("Zapisano zmiany!")
            time.sleep(1)
            st.rerun()
            
    # DODAWANIE
    with st.expander("➕ Dodaj nowy produkt"):
        with st.form("new_p"):
            n = st.text_input("Nazwa")
            l = st.number_input("Ilość", 0)
            p = st.number_input("Cena", 0.0)
            k_opt = {r['nazwa']: r['id'] for _, r in df_k.iterrows()}
            k = st.selectbox("Kategoria", list(k_opt.keys()))
            if st.form_submit_button("Dodaj"):
                supabase.table('Produkty').insert({
                    "nazwa": n, "liczba": l, "cena": p, "kategoria_id": k_opt[k]
                }).execute()
                st.rerun()

# --- TAB: KATEGORIE ---
with tab_kat:
    st.dataframe(df_k[['nazwa', 'opis']], use_container_width=True, hide_index=True)
    with st.form("new_k"):
        kn = st.text_input("Nowa kategoria")
        if st.form_submit_button("Dodaj kategorię"):
            supabase.table('Kategorie').insert({"nazwa": kn}).execute()
            st.rerun()

# --- TAB: SNAKE ---
with tab_snake:
    init_snake()
    col_g1, col_g2 = st.columns([1, 2])
    
    with col_g1:
        st.write(f"### Wynik: {st.session_state.score}")
        # Przyciski sterowania
        st.button("⬆️", on_click=lambda: st.session_state.update(direction='UP'))
        c_l, c_r = st.columns(2)
        c_l.button("⬅️", on_click=lambda: st.session_state.update(direction='LEFT'))
        c_r.button("➡️", on_click=lambda: st.session_state.update(direction='RIGHT'))
        st.button("⬇️", on_click=lambda: st.session_state.update(direction='DOWN'))
        if st.button("Restart"): 
            del st.session_state.snake
            st.rerun()

    with col_g2:
        game_placeholder = st.empty()
        
        # Mechanika ruchu
        if not st.session_state.game_over:
            head_x, head_y = st.session_state.snake[0]
            if st.session_state.direction == 'UP': head_x -= 1
            elif st.session_state.direction == 'DOWN': head_x += 1
            elif st.session_state.direction == 'LEFT': head_y -= 1
            elif st.session_state.direction == 'RIGHT': head_y += 1
            
            new_h = (head_x, head_y)
            
            # Kolizje
            if (head_x < 0 or head_x >= 15 or head_y < 0 or head_y >= 15 or new_h in st.session_state.snake):
                st.session_state.game_over = True
            else:
                st.session_state.snake.insert(0, new_h)
                if new_h == st.session_state.food:
                    st.session_state.score += 1
                    st.session_state.food = (random.randint(0, 14), random.randint(0, 14))
                else:
                    st.session_state.snake.pop()
        
        # Rysowanie
        board = [["." for _ in range(15)] for _ in range(15)]
        fx, fy = st.session_state.food
        board[fx][fy] = "🍎"
        for i, (sx, sy) in enumerate(st.session_state.snake):
            board[sx][sy] = "🐲" if i == 0 else "🟢"
            
        b_str = "\n".join([" ".join(r) for r in board])
        game_placeholder.markdown(f'<div class="snake-board">{b_str}</div>', unsafe_allow_html=True)
        
        if st.session_state.game_over:
            st.error("GAME OVER!")
        else:
            time.sleep(0.4)
            st.rerun()
