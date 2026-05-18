import os
import subprocess
import shutil

def build_and_package():
    print("--- Rozpoczynam kompilację aplikacji (PyInstaller) ---")
    
    # 1. Uruchomienie PyInstallera w trybie folderu
    # Flaga --noconfirm automatycznie nadpisuje stare foldery build/dist
    try:
        subprocess.run([
            "pyinstaller", 
            "--noconfirm", 
            "--name", "SAP_Extractor", 
            "main.py"
        ], check=True)
    except subprocess.CalledProcessError:
        print("BŁĄD: Wystąpił problem podczas budowania aplikacji przez PyInstaller.")
        return

    print("\n--- Kompilacja zakończona. Przygotowuję paczkę ---")
    
    dist_dir = os.path.join("dist", "SAP_Extractor")
    
    # 2. Kopiowanie wymaganych plików dla użytkownika końcowego
    # Kopiujemy config.example.json i od razu zmieniamy mu nazwę na config.json
    print("Kopiowanie pliku konfiguracyjnego (config.json)...")
    shutil.copy("config.json", os.path.join(dist_dir, "config.json"))
    
    if os.path.exists("README.md"):
        print("Kopiowanie instrukcji (README.md)...")
        shutil.copy("README.md", dist_dir)
        
    # 3. Kompresja folderu wynikowego do pliku .zip
    zip_name = "SAP_Extractor_Release"
    print(f"\nPakowanie do archiwum: {zip_name}.zip ...")
    shutil.make_archive(zip_name, 'zip', root_dir="dist", base_dir="SAP_Extractor")
    
    print(f"\n[SUKCES] Gotowe! Paczka z programem znajduje się w: {zip_name}.zip")

if __name__ == "__main__":
    build_and_package()