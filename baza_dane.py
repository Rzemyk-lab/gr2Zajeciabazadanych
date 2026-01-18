import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Magazyn Supabase", layout="wide")

# --- POŁĄCZENIE Z SUPABASE ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia z bazą danych. Sprawdź sekrety (secrets.toml lub Streamlit Cloud).")
    st.stop()

# --- FUNKCJE POBIERANIA DANYCH ---

def pobierz_kategorie():
    response = supabase.table('Kategorie').select("*").execute()
    return response.data

def pobierz_produkty():
    # Pobieramy produkty wraz z relacją do tabeli Kategorie
    response = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = response.data
    
    cleaned_data = []
    for item in data:
        # Wyciągamy nazwę kategorii z obiektu zagnieżdżonego
        kategoria_nazwa = item['Kategorie']['nazwa'] if item['Kategorie'] else "Brak"
        cleaned_data.append({
            "id": item['id'],
            "nazwa": item['nazwa'],
            "liczba": item['liczba'],
            "cena": item['cena'],
            "kategoria": kategoria_nazwa
        })
    return cleaned_data

# --- INTERFEJS UŻYTKOWNIKA ---
st.title("📊 System Zarządzania Magazynem")

tab1, tab2 = st.tabs(["🛍️ Produkty i Analiza", "🗂️ Kategorie"])

# === ZAKŁADKA 1: PRODUKTY I WYKRES ===
with tab1:
    produkty = pobierz_produkty()
    
    if produkty:
        df_produkty = pd.DataFrame(produkty)
        
        # --- SEKCJA WYKRESU ---
        st.subheader("📈 Ilość produktów w kategoriach")
        # Grupowanie danych do wykresu: suma kolumny 'liczba' dla każdej 'kategorii'
        df_wykres = df_produkty.groupby("kategoria")["liczba"].sum().reset_index()
        df_wykres.columns = ["Kategoria", "Suma sztuk"]
        
        # Wyświetlenie wykresu słupkowego
        st.bar_chart(df_wykres, x="Kategoria", y="Suma sztuk", color="#0072B2")
        
        st.divider()

        # --- LISTA I DODAWANIE ---
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📦 Lista Produktów")
            st.dataframe(
                df_produkty, 
                column_config={
                    "cena": st.column_config.NumberColumn("Cena", format="%.2f zł"),
                    "liczba": st.column_config.NumberColumn("Stan", format="%d szt."),
                },
                use_container_width=True,
                hide_index=True
            )

        with col2:
            st.subheader("➕ Dodaj Produkt")
            kategorie_raw = pobierz_kategorie()
            opcje_kategorii = {kat['nazwa']: kat['id'] for kat in kategorie_raw}
            
            with st.form("form_produkt"):
                n_nazwa = st.text_input("Nazwa produktu")
                n_liczba = st.number_input("Liczba sztuk", min_value=0, step=1)
                n_cena = st.number_input("Cena", min_value=0.0, step=0.01)
                n_kat = st.selectbox("Kategoria", options=list(opcje_kategorii.keys()) if opcje_kategorii else [])
                
                if st.form_submit_button("Dodaj"):
                    if n_nazwa and n_kat:
                        supabase.table('Produkty').insert({
                            "nazwa": n_nazwa, "liczba": n_liczba, 
                            "cena": n_cena, "kategoria_id": opcje_kategorii[n_kat]
                        }).execute()
                        st.success("Dodano!")
                        st.rerun()
            
            st.divider()
            st.subheader("🗑️ Usuń Produkt (ID)")
            id_del = st.number_input("ID produktu", min_value=1, step=1)
            if st.button("Usuń produkt"):
                supabase.table('Produkty').delete().eq('id', id_del).execute()
                st.rerun()
    else:
        st.info("Baza produktów jest pusta. Dodaj pierwszą kategorię, a potem produkt.")

# === ZAKŁADKA 2: KATEGORIE ===
with tab2:
    st.header("Zarządzanie Kategoriami")
    k_col1, k_col2 = st.columns(2)
    
    kategorie = pobierz_kategorie()
    
    with k_col1:
        if kategorie:
            st.dataframe(pd.DataFrame(kategorie), use_container_width=True, hide_index=True)
            
    with k_col2:
        with st.form("form_kat"):
            k_nazwa = st.text_input("Nazwa nowej kategorii")
            k_opis = st.text_area("Opis")
            if st.form_submit_button("Dodaj kategorię"):
                if k_nazwa:
                    supabase.table('Kategorie').insert({"nazwa": k_nazwa, "opis": k_opis}).execute()
                    st.rerun()

        st.divider()
        st.subheader("🗑️ Usuń Kategorię")
        kat_do_usuniecia = st.selectbox("Wybierz do usunięcia", [k['nazwa'] for k in kategorie] if kategorie else [])
        if st.button("Usuń wybraną"):
            id_kat_del = next(k['id'] for k in kategorie if k['nazwa'] == kat_do_usuniecia)
            try:
                supabase.table('Kategorie').delete().eq('id', id_kat_del).execute()
                st.rerun()
            except:
                st.error("Nie można usunąć kategorii, która zawiera produkty!")
