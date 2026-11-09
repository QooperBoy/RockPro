"""Small local table UI for the tested panel-integration prototype."""
import json
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

ROOT = Path(__file__).resolve().parent

def main():
    config = json.loads((ROOT / 'mvp_config.json').read_text(encoding='utf-8'))
    app = tk.Tk()
    app.title('RockPro — test integracji IronCAD')
    app.geometry('760x470')
    app.configure(padx=18, pady=18)
    ttk.Label(app, text='Tabela parametrów — prototyp jednej formatki', font=('Segoe UI', 14, 'bold')).pack(anchor='w')
    ttk.Label(app, text='Zmiana Larg → długość przedniej formatki pokrywy. Nie jest to konfigurator całej skrzyni.').pack(anchor='w', pady=(8, 12))
    table = ttk.Frame(app)
    table.pack(fill='x')
    ttk.Label(table, text='Wariant').grid(row=0, column=0, padx=8, sticky='w')
    ttk.Label(table, text='Długość [mm] — zakres testowy 800–1100').grid(row=0, column=1, padx=8, sticky='w')
    fields = []
    for i, variant in enumerate(config['variants'], start=1):
        ttk.Label(table, text=variant['name']).grid(row=i, column=0, padx=8, pady=5, sticky='w')
        value = tk.StringVar(value=str(variant['value_mm']))
        ttk.Entry(table, textvariable=value, width=18).grid(row=i, column=1, padx=8, sticky='w')
        fields.append(value)
    status = tk.StringVar(value='Otwórz źródłowy Showcase_Epson_parametry.ics w IronCAD. Każdy przebieg tworzy nowe kopie.')
    ttk.Label(app, textvariable=status, wraplength=710).pack(anchor='w', pady=12)
    output = tk.Text(app, height=12, wrap='word')
    output.pack(fill='both', expand=True)

    def finished(code, logs):
        button.configure(state='normal')
        status.set('Test zakończony poprawnie.' if code == 0 else 'Test nie przeszedł — sprawdź komunikat i raport.')
        output.insert('end', logs)
        output.see('end')

    def start():
        try:
            values = [float(v.get().replace(',', '.')) for v in fields]
            if not all(800 <= v <= 1100 for v in values):
                raise ValueError('Wpisz liczby od 800 do 1100 mm.')
        except ValueError as exc:
            messagebox.showerror('Niepoprawne wymiary', str(exc))
            return
        job = json.loads(json.dumps(config))
        for variant, value in zip(job['variants'], values):
            variant['value_mm'] = value
        job['source'] = str((ROOT / config['source']).resolve())
        inputs = ROOT / 'inputs'
        inputs.mkdir(exist_ok=True)
        path = inputs / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
        button.configure(state='disabled')
        status.set('Trwa: kopia → zmiana → przebudowa → pomiar → zapis → ponowne otwarcie.')
        def worker():
            try:
                result = subprocess.run([sys.executable, '-u', str(ROOT/'run_mvp.py'), '--config', str(path)], cwd=ROOT,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace',
                                        creationflags=subprocess.CREATE_NO_WINDOW)
                app.after(0, finished, result.returncode, result.stdout)
            except Exception as exc:
                app.after(0, finished, 1, str(exc))
        threading.Thread(target=worker, daemon=True).start()

    button = ttk.Button(app, text='Wygeneruj i sprawdź kopie ICS', command=start)
    button.pack(anchor='w', pady=(12, 0))
    app.mainloop()

if __name__ == '__main__':
    main()
