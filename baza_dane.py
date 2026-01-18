import streamlit as st
from supabase import create_client, Client
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Menedżer Produktów", layout="wide")
st.title("📦 System Zarządzania Produktami")

# --- POŁĄCZENIE Z SUPABASE ---
# Używamy st.secrets do bezpiecznego przechowywania kluczy (o tym w instrukcji niżej)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Błąd połączenia z bazą danych. Sprawdź sekrety w Streamlit.")
    st.stop()

# --- FUNKCJE POMOCNICZE ---

def pobierz_kategorie():
    """Pobiera wszystkie kategorie z bazy."""
    response = supabase.table('Kategorie').select("*").execute()
    return response.data

def pobierz_produkty():
    """Pobiera produkty i łączy je z nazwami kategorii."""
    # Pobieramy produkty i dane powiązanej kategorii
    response = supabase.table('Produkty').select("*, Kategorie(nazwa)").execute()
    data = response.data
    
    # Spłaszczamy strukturę (wyciągamy nazwę kategorii z zagnieżdżonego obiektu)
    cleaned_data = []
    for item in data:
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

tab1, tab2 = st.tabs(["🛍️ Produkty", "🗂️ Kategorie"])

# === ZAKŁADKA 1: PRODUKTY ===
with tab1:
    st.header("Zarządzanie Produktami")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Lista Produktów")
        produkty = pobierz_produkty()
        if produkty:
            df_produkty = pd.DataFrame(produkty)
            # Formatowanie kolumn
            st.dataframe(
                df_produkty, 
                column_config={
                    "cena": st.column_config.NumberColumn("Cena", format="%.2f zł"),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Brak produktów w bazie.")

    with col2:
        st.subheader("Dodaj Produkt")
        
        # Potrzebujemy listy kategorii do listy rozwijanej
        kategorie_raw = pobierz_kategorie()
        opcje_kategorii = {kat['nazwa']: kat['id'] for kat in kategorie_raw}
        
        with st.form("form_dodaj_produkt"):
            prod_nazwa = st.text_input("Nazwa produktu")
            prod_liczba = st.number_input("Liczba sztuk", min_value=0, step=1)
            prod_cena = st.number_input("Cena", min_value=0.0, step=0.01, format="%.2f")
            wybrana_kat_nazwa = st.selectbox("Kategoria", options=list(opcje_kategorii.keys()) if opcje_kategorii else [])
            
            submit_prod = st.form_submit_button("Dodaj produkt")
            
            if submit_prod:
                if not prod_nazwa:
                    st.warning("Podaj nazwę produktu.")
                elif not wybrana_kat_nazwa:
                    st.warning("Musisz najpierw stworzyć kategorię.")
                else:
                    kat_id = opcje_kategorii[wybrana_kat_nazwa]
                    try:
                        supabase.table('Produkty').insert({
                            "nazwa": prod_nazwa,
                            "liczba": prod_liczba,
                            "cena": prod_cena,
                            "kategoria_id": kat_id
                        }).execute()
                        st.success("Produkt dodany!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Wystąpił błąd: {e}")

        st.divider()
        st.subheader("Usuń Produkt")
        # Proste usuwanie po ID (można rozbudować o selectbox)
        id_to_delete = st.number_input("Podaj ID produktu do usunięcia", min_value=1, step=1, key="del_prod")
        if st.button("Usuń produkt"):
            try:
                supabase.table('Produkty').delete().eq('id', id_to_delete).execute()
                st.success(f"Usunięto produkt o ID: {id_to_delete}")
                st.rerun()
            except Exception as e:
                st.error(f"Nie udało się usunąć: {e}")

# === ZAKŁADKA 2: KATEGORIE ===
with tab2:
    st.header("Zarządzanie Kategoriami")
    
    col_k1, col_k2 = st.columns([1, 1])
    
    with col_k1:
        st.subheader("Istniejące Kategorie")
        kategorie = pobierz_kategorie()
        if kategorie:
            st.dataframe(pd.DataFrame(kategorie), use_container_width=True, hide_index=True)
        else:
            st.info("Brak kategorii.")

    with col_k2:
        st.subheader("Dodaj Kategorię")
        with st.form("form_dodaj_kat"):
            kat_nazwa = st.text_input("Nazwa kategorii")
            kat_opis = st.text_area("Opis (opcjonalnie)")
            
            submit_kat = st.form_submit_button("Stwórz kategorię")
            
            if submit_kat:
                if not kat_nazwa:
                    st.warning("Nazwa kategorii jest wymagana.")
                else:
                    try:
                        supabase.table('Kategorie').insert({
                            "nazwa": kat_nazwa,
                            "opis": kat_opis
                        }).execute()
                        st.success("Kategoria dodana!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Błąd: {e}")

        st.divider()
        st.subheader("Usuń Kategorię")
        st.warning("⚠️ Usunięcie kategorii przypisanej do produktów może spowodować błąd, jeśli nie masz ustawionego 'Cascade Delete' w bazie.")
        
        opcje_usuwania = {kat['nazwa']: kat['id'] for kat in kategorie}
        do_usuniecia = st.selectbox("Wybierz kategorię do usunięcia", options=list(opcje_usuwania.keys()) if opcje_usuwania else [])
        
        if st.button("Usuń wybraną kategorię"):
            if do_usuniecia:
                kat_id_del = opcje_usuwania[do_usuniecia]
                try:
                    supabase.table('Kategorie').delete().eq('id', kat_id_del).execute()
                    st.success("Kategoria usunięta!")
                    st.rerun()
                except Exception as e:
                    st.error("Nie można usunąć kategorii (prawdopodobnie są do niej przypisane produkty).")
