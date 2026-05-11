import json
import os
import sys
import logging
import queue
import concurrent.futures
import pythoncom
import time
import win32com.client
from datetime import datetime, timedelta
from sap_bot import SAPExtractor

def get_base_dir():
    """Zwraca ścieżkę do folderu, w którym znajduje się skrypt lub plik .exe"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

# Konfiguracja profesjonalnego loggera
def setup_logger(base_dir):
    logger = logging.getLogger("SAP_Extractor")
    logger.setLevel(logging.INFO)
    
    # Format logów
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    log_path = os.path.join(base_dir, 'run_log.txt')
    # Zapis do pliku
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Wypisywanie w konsoli
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def get_dynamic_dates():
    now = datetime.now()
    current_year = now.year
    
    first_day_current_month = now.replace(day=1)
    last_day_last_month = first_day_current_month - timedelta(days=1)
    start_of_last_month = last_day_last_month.replace(day=1)
    
    return {
        "{TODAY}": now.strftime("%d.%m.%Y"),
        "{START_OF_PREV_YEAR}": f"01.01.{current_year - 1}",
        "{END_OF_PREV_YEAR}": f"31.12.{current_year - 1}",
        "{START_OF_CURRENT_YEAR}": f"01.01.{current_year}",
        "{START_OF_CURRENT_MONTH}": first_day_current_month.strftime("%d.%m.%Y"),
        "{START_OF_LAST_MONTH}": start_of_last_month.strftime("%d.%m.%Y"),
        "{END_OF_LAST_MONTH}": last_day_last_month.strftime("%d.%m.%Y")
    }

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Brak pliku '{config_path}'. Utwórz go na podstawie 'config.example.json'.")
        
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)

def get_sap_session_count():
    """Zwraca liczbę otwartych okien (sesji) SAP."""
    try:
        pythoncom.CoInitialize()
        SapGuiAuto = win32com.client.GetObject("SAPGUI")
        app = SapGuiAuto.GetScriptingEngine
        conn = app.Children(0)
        return conn.Children.Count
    except Exception:
        return 0

def open_new_sap_session(logger):
    """Próbuje otworzyć nową sesję SAP i zwraca True przy sukcesie lub False przy porażce."""
    try:
        # Potrzebujemy dowolnej aktywnej sesji, aby wysłać polecenie
        pythoncom.CoInitialize()
        SapGuiAuto = win32com.client.GetObject("SAPGUI")
        app = SapGuiAuto.GetScriptingEngine
        # Upewnij się, że istnieje co najmniej jedno połączenie i sesja
        if app.Children.Count == 0 or app.Children(0).Children.Count == 0:
            logger.error("Nie można otworzyć nowej sesji - brak aktywnego połączenia.")
            return False
            
        conn = app.Children(0)
        session = conn.Children(0) # Użyj pierwszej sesji do otwarcia kolejnych

        initial_count = conn.Children.Count
        
        # Standardowa metoda API SAP do otwierania nowego okna
        session.CreateSession()
        
        # Oczekujemy maksymalnie 5 sekund na pojawienie się nowej sesji
        for _ in range(10):
            time.sleep(0.5)
            if conn.Children.Count > initial_count:
                return True
                
        return False # Timeout lub osiągnięto maksymalny limit okien (np. 6)
    except Exception as e:
        logger.error(f"Błąd podczas próby otwarcia nowej sesji SAP: {e}")
        return False

def manage_sap_sessions(logger, num_tables):
    """Interaktywnie zarządza liczbą sesji SAP na potrzeby procesu."""
    max_sap_sessions = 6 # Domyślny limit SAP
    current_sessions = get_sap_session_count()
    logger.info(f"Wykryto {current_sessions} otwartych sesji SAP.")

    if current_sessions == 0:
        return 0

    # Zapytaj użytkownika o pożądaną liczbę sesji
    while True:
        try:
            print(f"\n[INFO] Liczba tabel do pobrania w tej paczce: {num_tables}")
            prompt = f"Ile okien SAP chcesz użyć jednocześnie (1-{max_sap_sessions}, obecnie otwarte: {current_sessions})?\nNaciśnij [ENTER], aby użyć {current_sessions}: "
            desired_str = input(prompt)
            
            if not desired_str:
                desired_sessions = current_sessions
                break
            
            desired_sessions = int(desired_str)
            if 1 <= desired_sessions <= max_sap_sessions:
                break
            else:
                print(f"BŁĄD: Wprowadź liczbę od 1 do {max_sap_sessions}.")
        except ValueError:
            print("BŁĄD: Wprowadź poprawną liczbę.")
    
    # Otwórz nowe sesje, jeśli to konieczne
    sessions_to_open = desired_sessions - current_sessions
    if sessions_to_open > 0:
        logger.info(f"Próba otwarcia {sessions_to_open} nowych sesji SAP...")
        opened_count = 0
        for _ in range(sessions_to_open):
            if open_new_sap_session(logger):
                opened_count += 1
                time.sleep(1) # Poczekaj na prawidłową inicjalizację sesji
            else:
                logger.warning("Osiągnięto maksymalną liczbę sesji SAP dozwoloną przez system. Używam dostępnych okien.")
                break
        if opened_count > 0:
            logger.info(f"Otwarto {opened_count} nowych sesji.")

    # Zwróć ostateczną liczbę sesji do użycia
    final_session_count = get_sap_session_count()
    # Powinniśmy użyć liczby, której chciał użytkownik, ale ograniczonej przez to, co jest rzeczywiście dostępne
    usable_sessions = min(final_session_count, desired_sessions)
    logger.info(f"Finalna liczba sesji do użycia w puli wątków: {usable_sessions}")
    return usable_sessions

def display_welcome_screen(export_dir, tables, session_count):
    print("\n" + "=" * 60)
    print("   AUTOMATYCZNY EKSTRAKTOR DANYCH SAP (SE16N)   ")
    print("=" * 60)
    print(f"-> Folder zapisu: {export_dir}")
    print(f"-> Liczba tabel:  {len(tables)}")
    print(f"-> Wykryte sesje SAP: {session_count} (Wielowątkowość)")
    for name in tables:
        print(f"  - {name}")
    print("-" * 60)
    answer = input("\nCzy chcesz kontynuować? (wpisz 'tak' i naciśnij Enter): ").lower().strip()
    
    if answer not in ['tak', 'yes', 't', 'y']:
        print("Anulowano przez użytkownika. Zamykanie programu.")
        sys.exit(0)
    print("--- Rozpoczynanie pracy ---")

def process_table(table_name, filters, export_dir, session_queue, dynamic_vars, logger):
    # Pobierz wolny indeks okna SAP z kolejki
    session_index = session_queue.get()
    start_time = time.time()
    try:
        logger.info(f"Rozpoczęto przetwarzanie tabeli: {table_name} [Sesja SAP: {session_index}]")
        # Podmiana dynamicznych wartości z configu
        for f in filters:
            if f['value'] in dynamic_vars:
                f['value'] = dynamic_vars[f['value']]
                
        bot = SAPExtractor(session_index=session_index)
        result = bot.extract_table(table_name, filters, export_dir)
        elapsed_time = time.time() - start_time
        return table_name, result, elapsed_time
    finally:
        # Zwróć indeks okna do kolejki, by następna tabela mogła z niego skorzystać
        session_queue.put(session_index)


def main():
    base_dir = get_base_dir()
    logger = setup_logger(base_dir)
    logger.info("--- Uruchomienie programu ---")
    
    config_path = os.path.join(base_dir, "config.json")
    try:
        config = load_config(config_path)
    except Exception as e:
        logger.error(f"Nie można wczytać pliku config.json: {e}")
        return

    export_dir = config["export_directory"]
    tables = config["tables"]
    
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)
        logger.info(f"Utworzono folder eksportu: {export_dir}")

    session_count = manage_sap_sessions(logger, len(tables))
    if session_count == 0:
        logger.error("Nie wykryto żadnej otwartej sesji SAP! Upewnij się, że SAP jest włączony i zalogowany.")
        return
        
    display_welcome_screen(export_dir, tables, session_count)
    logger.info(f"Uruchamianie w puli wątków (równoległe okna SAP: {session_count})...")
    
    program_start_time = time.time()
    
    dynamic_vars = get_dynamic_dates()
    
    # Inicjalizacja kolejki z dostępnymi indeksami okien (0, 1, 2...)
    session_queue = queue.Queue()
    for i in range(session_count):
        session_queue.put(i)

    # Uruchomienie wielowątkowe (liczba wątków ograniczona do liczby otwartych okien SAP)
    with concurrent.futures.ThreadPoolExecutor(max_workers=session_count) as executor:
        futures = [executor.submit(process_table, t_name, f, export_dir, session_queue, dynamic_vars, logger) for t_name, f in tables.items()]
        
        for future in concurrent.futures.as_completed(futures):
            table_name, result, elapsed_time = future.result()
            
            minutes, seconds = divmod(int(elapsed_time), 60)
            time_str = f"{minutes} min {seconds} sek" if minutes > 0 else f"{seconds} sek"
            
            if result["status"] == "success":
                logger.info(f"[SUKCES] {table_name}: {result['msg']} (Czas: {time_str})")
            elif result["status"] == "nodata":
                logger.warning(f"[BRAK DANYCH] {table_name}: {result['msg']} (Czas: {time_str})")
            elif result["status"] == "warning":
                logger.warning(f"[OSTRZEŻENIE] {table_name}: {result['msg']} (Czas: {time_str})")
            else:
                logger.error(f"[BŁĄD] {table_name}: {result['msg']} (Czas: {time_str})")

    total_elapsed = time.time() - program_start_time
    total_minutes, total_seconds = divmod(int(total_elapsed), 60)
    total_time_str = f"{total_minutes} min {total_seconds} sek" if total_minutes > 0 else f"{total_seconds} sek"

    logger.info(f"Całkowity czas pobierania: {total_time_str}")
    logger.info("--- Zakończono pracę programu ---\n")
    print(f"\nProces zakończony (Czas całkowity: {total_time_str}). Szczegóły znajdziesz w pliku run_log.txt")

if __name__ == "__main__":
    main()
    input("Wciśnij [ENTER], aby zamknąć okno...")