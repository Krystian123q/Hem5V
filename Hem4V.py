import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import shutil
import urllib.request
import tempfile

WORKDIR = r"C:\Hem4V"

def log(msg):
    log_text.configure(state="normal")
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    log_text.configure(state="disabled")

def check_exe(cmd):
    """Check if executable exists in PATH."""
    return shutil.which(cmd) is not None

def install_git():
    log("Git nie jest zainstalowany. Pobieram instalator Git for Windows...")
    git_url = "https://github.com/git-for-windows/git/releases/latest/download/Git-2.45.2-64-bit.exe"
    temp_path = os.path.join(tempfile.gettempdir(), "Git-64-bit.exe")
    try:
        urllib.request.urlretrieve(git_url, temp_path)
        log("Instaluję Git (tryb cichy)...")
        subprocess.run([temp_path, "/VERYSILENT", "/NORESTART"], check=True)
        log("Git został zainstalowany.")
        os.remove(temp_path)
    except Exception as e:
        log(f"Błąd podczas instalacji Git: {e}")
        messagebox.showerror("Błąd", "Nie udało się zainstalować Git. Zainstaluj ręcznie i spróbuj ponownie.")
        return False
    return True

def ensure_git():
    if check_exe("git"):
        log("Git jest zainstalowany.")
        return True
    else:
        return install_git()

def ensure_python():
    if check_exe("python"):
        log("Python jest zainstalowany.")
        return True
    else:
        log("Python nie jest zainstalowany!")
        messagebox.showwarning("Brak Pythona", "Nie znaleziono Pythona. Zainstaluj Python i spróbuj ponownie.")
        return False

def ensure_npm():
    if check_exe("npm"):
        log("Node.js (npm) jest zainstalowany.")
        return True
    else:
        log("Node.js / npm nie jest zainstalowany!")
        messagebox.showwarning("Brak npm", "Nie znaleziono Node.js ani npm. Zainstaluj Node.js i spróbuj ponownie.")
        return False

def run_cmd(cmd, cwd=None, shell=False):
    """Run command and stream output to log."""
    log(f"Uruchamiam: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            log(line.rstrip())
        proc.wait()
        return proc.returncode
    except Exception as e:
        log(f"Błąd podczas uruchamiania polecenia: {e}")
        return -1

def parse_repo_name(repo_url):
    name = repo_url.rstrip('/').split('/')[-1]
    if name.endswith('.git'):
        name = name[:-4]
    return name

def do_workflow(repo_url):
    run_btn["state"] = "disabled"
    try:
        # 1. Tworzenie folderu
        log(f"Tworzę folder roboczy: {WORKDIR}")
        os.makedirs(WORKDIR, exist_ok=True)

        # 2. Git
        if not ensure_git():
            run_btn["state"] = "normal"
            return

        # 3. Klonowanie repo
        repo_name = parse_repo_name(repo_url)
        target_dir = os.path.join(WORKDIR, repo_name)
        if os.path.exists(target_dir):
            log(f"Usuwam istniejący folder {target_dir} ...")
            try:
                shutil.rmtree(target_dir)
            except Exception as e:
                log(f"Nie mogę usunąć folderu: {e}")
                run_btn["state"] = "normal"
                return
        log(f"Klonuję repozytorium...")
        exit_code = run_cmd(["git", "clone", repo_url], cwd=WORKDIR)
        if exit_code != 0:
            log("Błąd podczas klonowania repozytorium!")
            run_btn["state"] = "normal"
            return
        log(f"Sklonowano do {target_dir}")

        # 4. Rozpoznanie technologii
        req_path = os.path.join(target_dir, "requirements.txt")
        pkg_path = os.path.join(target_dir, "package.json")
        if os.path.isfile(req_path):
            log("Wykryto projekt Python (requirements.txt).")
            if not ensure_python():
                run_btn["state"] = "normal"
                return
            # pip install
            log("Instaluję zależności: pip install -r requirements.txt")
            exit_code = run_cmd([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=target_dir)
            if exit_code != 0:
                log("Błąd podczas instalowania zależności pip!")
                run_btn["state"] = "normal"
                return
            # uruchom main.py
            main_py = os.path.join(target_dir, "main.py")
            if os.path.isfile(main_py):
                log("Uruchamiam main.py ...")
                run_cmd([sys.executable, "main.py"], cwd=target_dir)
            else:
                log("Brak pliku main.py – nie uruchamiam projektu.")
        elif os.path.isfile(pkg_path):
            log("Wykryto projekt Node.js (package.json).")
            if not ensure_npm():
                run_btn["state"] = "normal"
                return
            # npm install
            log("Instaluję zależności npm ...")
            exit_code = run_cmd(["npm", "install"], cwd=target_dir)
            if exit_code != 0:
                log("Błąd podczas npm install!")
                run_btn["state"] = "normal"
                return
            # npm start
            log("Uruchamiam npm start ...")
            run_cmd(["npm", "start"], cwd=target_dir, shell=True)
        else:
            log("Nie wykryto obsługiwanej technologii (brak requirements.txt / package.json)!")

    finally:
        run_btn["state"] = "normal"

def on_run_click():
    repo_url = repo_entry.get().strip()
    if not repo_url or not repo_url.startswith("http"):
        messagebox.showwarning("Niepoprawny adres", "Podaj poprawny link do repozytorium GitHub (https://...)")
        return
    log_text.configure(state="normal")
    log_text.delete(1.0, tk.END)
    log_text.configure(state="disabled")
    threading.Thread(target=do_workflow, args=(repo_url,), daemon=True).start()

def on_close():
    root.destroy()

# --- GUI ---
root = tk.Tk()
root.title("HEM 4V – Rozrusznik projektów")
root.geometry("720x480")
root.resizable(False, False)

frm = ttk.Frame(root, padding="10 10 10 10")
frm.pack(fill="both", expand=True)

lbl = ttk.Label(frm, text="Podaj link do repozytorium GitHub:")
lbl.grid(row=0, column=0, sticky="w", padx=(0,10))

repo_entry = ttk.Entry(frm, width=60)
repo_entry.grid(row=0, column=1, sticky="we")
repo_entry.focus()

run_btn = ttk.Button(frm, text="Uruchom", command=on_run_click)
run_btn.grid(row=0, column=2, padx=(10,0))

log_text = scrolledtext.ScrolledText(frm, width=85, height=26, state="disabled", font=("Consolas", 10))
log_text.grid(row=1, column=0, columnspan=3, pady=(14,0))

frm.grid_columnconfigure(1, weight=1)

root.protocol("WM_DELETE_WINDOW", on_close)
root.mainloop()