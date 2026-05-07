# SS Level SAP Extractor

Automatyczny ekstraktor danych z systemu SAP (transakcja SE16N) przy użyciu języka Python i technologii SAP GUI Scripting. Program nawiązuje połączenie z aktywną sesją SAP, automatycznie uzupełnia filtry wyszukiwania i eksportuje wyniki do plików tekstowych.

## Wymagania
- System operacyjny Windows.
- Zainstalowany klient SAP GUI z otwartą sesją i zalogowanym użytkownikiem.
- Włączona obsługa skryptów po stronie SAP (SAP GUI Scripting API).
- Python 3.x

## Instalacja
1. Sklonuj repozytorium na swój komputer.
2. Opcjonalnie utwórz i aktywuj wirtualne środowisko (venv).
3. Zainstaluj wymagane pakiety:
   ```bash
   pip install -r requirements.txt
   ```
4. Skopiuj plik `config.example.json` i zmień jego nazwę na `config.json`. 
5. Edytuj plik `config.json` dostosowując listę tabel, parametry oraz `export_directory` do własnych potrzeb.

## Uruchomienie
Przed uruchomieniem skryptu upewnij się, że okno SAP jest otwarte, a użytkownik zalogowany na ekranie głównym (SAP Easy Access).
```bash
python main.py
```

Wszelkie informacje o przebiegu ekstrakcji oraz błędy zapisują się w pliku `run_log.txt`.