import win32com.client
import sys
import time
import pythoncom

class SAPExtractor:
    def __init__(self, session_index=0):
        # Inicjalizacja COM dla obecnego wątku (wymagane w wielowątkowości)
        pythoncom.CoInitialize()
        self.session = self._connect_to_sap(session_index)
        # Indeksy kolumn w Twoim układzie SE16N
        self.C_FIELD = 6  # Kolumna z Nazwą Techniczną
        self.C_LOW = 2    # Kolumna na wpisanie wartości
        self.C_OPT = 1    # Kolumna z przyciskiem opcji (=, <>)

    def _connect_to_sap(self, session_index):
        try:
            SapGuiAuto = win32com.client.GetObject("SAPGUI")
            application = SapGuiAuto.GetScriptingEngine
            connection = application.Children(0)
            session = connection.Children(session_index)
            return session
        except Exception:
            print("BŁĄD KRYTYCZNY: Nie można połączyć się z SAP.")
            sys.exit(1)

    def extract_table(self, table_name, filters, export_path):
        session = self.session
        
        # Zminimalizowanie okna, by nie wyskakiwało na wierzch i nie migało
        try:
            session.findById("wnd[0]").Iconify()
        except Exception:
            pass
        
        # Reset i wejście
        session.findById("wnd[0]/tbar[0]/okcd").text = "/n"
        session.findById("wnd[0]").sendVKey(0)
        session.StartTransaction("SE16N")
        
        session.findById("wnd[0]/usr/ctxtGD-TAB").text = table_name
        session.findById("wnd[0]").sendVKey(0) 
        session.findById("wnd[0]/usr/txtGD-MAX_LINES").text = ""

        # Aplikowanie filtrów
        if filters:
            table_id = "wnd[0]/usr/tblSAPLSE16NSELFIELDS_TC"
            
            for f in filters:
                field_to_find = f['field']
                value_to_set = f['value']
                option_row = f.get('option_row')
                found = False
                
                try:
                    session.findById(table_id).VerticalScrollbar.Position = 0
                except Exception:
                    pass
                
                for _ in range(20): 
                    table_ctrl = session.findById(table_id)
                    visible_rows = table_ctrl.VisibleRowCount
                    
                    for i in range(visible_rows):
                        try:
                            # Używamy sprawdzonych indeksów
                            field_cell = session.findById(f"{table_id}/txtGS_SELFIELDS-FIELDNAME[{self.C_FIELD},{i}]")
                            current_field = field_cell.text.strip()
                            
                            if current_field == field_to_find:
                                val_input = session.findById(f"{table_id}/ctxtGS_SELFIELDS-LOW[{self.C_LOW},{i}]")
                                val_input.text = value_to_set
                                val_input.setFocus()
                                
                                if option_row is not None:
                                    btn_option = session.findById(f"{table_id}/btnOPTION[{self.C_OPT},{i}]")
                                    btn_option.press()
                                    grid = session.findById("wnd[1]/usr/cntlGRID/shellcont/shell")
                                    grid.setCurrentCell(option_row, "TEXT")
                                    grid.selectedRows = str(option_row)
                                    grid.doubleClickCurrentCell()
                                
                                found = True
                                break
                        except Exception:
                            continue
                            
                    if found:
                        break
                    
                    try:
                        table_ctrl = session.findById(table_id)
                        current_pos = table_ctrl.VerticalScrollbar.Position
                        table_ctrl.VerticalScrollbar.Position = current_pos + visible_rows
                        if session.findById(table_id).VerticalScrollbar.Position == current_pos:
                            break 
                    except Exception:
                        break

                if not found:
                    return {"status": "warning", "msg": f"Nie znaleziono pola {field_to_find}."}

        # Wykonanie (F8)
        session.findById("wnd[0]/tbar[1]/btn[8]").press()
        
        # --- OBSŁUGA NO DATA ---
        try:
            # Sprawdzamy czy przeszliśmy do ekranu wyników (Siatka ALV istnieje)
            shell = session.findById("wnd[0]/usr/cntlRESULT_LIST/shellcont/shell")
        except Exception:
            # Jeśli nie przeszliśmy, odczytujemy pasek statusu na dole ekranu
            try:
                status_msg = session.findById("wnd[0]/sbar").text
            except:
                status_msg = "Prawdopodobnie brak danych (nie odczytano statusu)"
            
            # Wychodzimy z transakcji aby skrypt mógł pójść dalej
            session.findById("wnd[0]/tbar[0]/okcd").text = "/n"
            session.findById("wnd[0]").sendVKey(0)
            
            return {"status": "nodata", "msg": status_msg}

        # --- EKSPORT (Jeśli są dane) ---
        try:
            shell.pressToolbarContextButton("&MB_EXPORT")
            shell.selectContextMenuItem("&PC")
            session.findById("wnd[1]/tbar[0]/btn[0]").press()
            session.findById("wnd[1]/usr/ctxtDY_PATH").text = export_path
            session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = f"{table_name}.txt"
            session.findById("wnd[1]/tbar[0]/btn[11]").press()
            time.sleep(1.5) 
        except Exception as e:
            return {"status": "error", "msg": f"Błąd eksportu: {str(e)}"}

        # Powrót do ekranu głównego
        session.findById("wnd[0]/tbar[0]/okcd").text = "/n"
        session.findById("wnd[0]").sendVKey(0)
        
        return {"status": "success", "msg": "Zapisano pomyślnie."}