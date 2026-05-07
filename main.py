import json
import os
import sys
import logging
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

def display_welcome_screen(export_dir, tables):
    print("\n" + "=" * 60)
    print("   AUTOMATYCZNY EKSTRAKTOR DANYCH SAP (SE16N)   ")
    print("=" * 60)
    print(f"-> Folder zapisu: {export_dir}")
    print(f"-> Liczba tabel:  {len(tables)}")
    for name in tables:
        print(f"  - {name}")
    print("-" * 60)
    answer = input("\nCzy chcesz kontynuować? (wpisz 'tak' i naciśnij Enter): ").lower().strip()
    
    if answer not in ['tak', 'yes', 't', 'y']:
        print("Anulowano przez użytkownika. Zamykanie programu.")
        sys.exit(0)
    print("--- Rozpoczynanie pracy ---")


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

    display_welcome_screen(export_dir, tables)

    logger.info("Nawiązywanie połączenia z SAP...")
    bot = SAPExtractor()
    logger.info("Połączono pomyślnie.")
    
    dynamic_vars = get_dynamic_dates()

    for table_name, filters in tables.items():
        logger.info(f"Rozpoczęto przetwarzanie tabeli: {table_name}")
        
        # Podmiana dynamicznych wartości z configu
        for f in filters:
            if f['value'] in dynamic_vars:
                f['value'] = dynamic_vars[f['value']]

        # Ekstrakcja
        result = bot.extract_table(table_name, filters, export_dir)
        
        # Analiza wyniku
        if result["status"] == "success":
            logger.info(f"[SUKCES] {table_name}: {result['msg']}")
        elif result["status"] == "nodata":
            logger.warning(f"[BRAK DANYCH] {table_name}: {result['msg']}")
        elif result["status"] == "warning":
            logger.warning(f"[OSTRZEŻENIE] {table_name}: {result['msg']}")
        else:
            logger.error(f"[BŁĄD] {table_name}: {result['msg']}")

    logger.info("--- Zakończono pracę programu ---\n")
    print("\nProces zakończony. Szczegóły znajdziesz w pliku run_log.txt")

if __name__ == "__main__":
    main()
    input("Wciśnij [ENTER], aby zamknąć okno...")