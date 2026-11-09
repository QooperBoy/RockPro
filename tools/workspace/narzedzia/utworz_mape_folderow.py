"""Create local Polish workspace maps and indexes from verified file paths."""
import csv
from datetime import date
import html
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Transfer_RockPro_20261024/RockPro/rockpro-cad'
LIB=ROOT/'biblioteka_projektow'
LABELS={'01_Kufry':'Kufry','02_Miksery':'Miksery i konsole','03_Racki':'Racki',
        '04_Telewizory':'Telewizory i ekrany','05_Serwisy_szufladowe':'Serwisy szufladowe i workstation'}

def md_link(path,label=None):
    path=Path(path)
    if not path.exists():raise FileNotFoundError(path)
    return '['+(label or path.name)+'](<'+str(path.resolve()).replace('\\','/')+'>)'

def anchor(path,label=None):
    path=Path(path)
    if not path.exists():raise FileNotFoundError(path)
    return '<a href="'+html.escape(path.resolve().as_uri(),quote=True)+'">'+html.escape(label or path.name)+'</a>'

def main():
    inventory=json.loads((LIB/'INWENTARZ.json').read_text(encoding='utf-8'))
    models=[x for x in inventory['items'] if x['role']=='model_3d_zrodlowy']
    # No model is promoted merely by extraction, file age or its name.
    library=['# Biblioteka projektów bazowych RockPro','',
        'Import: 29.10.2026. Pięć paczek od użytkownika, 27 modeli ICS, jeden rysunek ICD, jedno zdjęcie i pięć pustych opisów.',
        'To zachowane źródła konstruktora do przyszłego opracowania wzorców. Parametryzacja, otwieralność w 2023/2027 i odbiór produkcyjny NIE były sprawdzane podczas importu.',
        '', 'Oryginałów nie zapisujemy po edycji. Wybrany plik kopiujemy do nowego projektu w `projekty/`; kolejne rewizje i snapshoty powstają tam.',
        'ZIP-y pozostają w Pobranych. Pełne ścieżki, CRC i SHA256 znajdują się w `INWENTARZ.json`; tabela do Excela to `KATALOG_PROJEKTOW.csv`.','']
    rows_html=[]
    for category,label in LABELS.items():
        rows=[x for x in models if x['category']==category]
        library+=['## '+label+' — '+str(len(rows))+' modeli','']
        category_doc=['# '+label,'','Status: źródła niezmienione, bez nowego odbioru CAD i parametryzacji.','']
        for row in rows:
            path=LIB/row['path'];line='- '+md_link(path)
            library.append(line);category_doc.append(line)
            rows_html.append('<tr><td>'+html.escape(label)+'</td><td>'+anchor(path)+'</td><td>Źródło · do opracowania</td></tr>')
        extra=[x for x in inventory['items'] if x['category']==category and x['role']!='model_3d_zrodlowy']
        for row in extra:category_doc.append('- '+md_link(LIB/row['path'])+' — '+row['role'])
        (LIB/category/'CZYTAJ_MNIE.md').write_text('\n'.join(category_doc)+'\n',encoding='utf-8')
        library.append('')
    (LIB/'CZYTAJ_MNIE.md').write_text('\n'.join(library),encoding='utf-8')

    template=ROOT/'projekty/_SZABLON_NOWEGO_PROJEKTU'
    folders=['00_Karta_zlecenia','01_Kopia_zrodla','02_Studio','03_CAD/Robocze','03_CAD/Do_sprawdzenia',
             '04_Snapshoty','05_Eksporty/JSON','05_Eksporty/Excel','05_Eksporty/STEP','05_Eksporty/Rysunki','06_Odbior']
    for folder in folders:(template/folder).mkdir(parents=True,exist_ok=True)
    (template/'CZYTAJ_MNIE.md').write_text('''# Szablon nowego projektu

Skopiuj cały ten folder do `projekty/KLIENT_ZLECENIE_NAZWA/`.

1. W `00_Karta_zlecenia` zapisz urządzenie, ilość skrzyń, wymagane wymiary wewnętrzne, wersję IronCAD i status.
2. Skopiuj wybrany model z biblioteki do `01_Kopia_zrodla`; zapisz ścieżkę pierwotną i SHA z INWENTARZ.json. Nie edytuj biblioteki.
3. W `02_Studio` przechowuj wyeksportowane drafty JSON. Sam zapis Studio może być w lokalnej bazie lub przeglądarce; folder nie uzupełnia się automatycznie.
4. Nowe pliki CAD: `03_CAD/Robocze`, nazwy `Nazwa_IC2027_r001.ics` / `Nazwa_IC2023_r001.ics` zależnie od faktycznego hosta. Nie zmieniaj rozszerzenia ani nazwy wersji zamiast konwersji.
5. Kopie do oceny: `03_CAD/Do_sprawdzenia`. Taka nazwa nie oznacza odbioru produkcyjnego.
6. Przed istotną zmianą zachowaj datowany snapshot w `04_Snapshoty`. Nie nadpisuj wcześniejszego snapshotu.
7. Eksporty JSON, Excel, STEP i rysunki zapisuj w odpowiednich folderach `05_Eksporty` z numerem rewizji.
8. W `06_Odbior` zapisz uwagi, testy i jawną akceptację konstruktora. Brak potwierdzenia pozostaje brakiem.

Nowy projekt nie jest automatycznie zarejestrowany w ERP/Excelu. Wdrożenie tego przepływu jest osobnym zadaniem ROC-55.
''',encoding='utf-8')

    overview=[
      ('biblioteka_projektow','Nowa baza 27 modeli konstruktora, podzielona na pięć kategorii. Źródła, nie gotowe zatwierdzone szablony.'),
      ('projekty','Nasze projekty i kolejne prototypy. Tu zapisujemy zmieniane kopie CAD, drafty i odbiory.'),
      ('biblioteka_czesci','Modele pojedynczych okuć producentów. CAD_producenci zawiera STEP, archiwa i mapowanie 265 rekordów.'),
      ('Transfer_RockPro_20261024','Zachowany pierwotny transfer: modele, dokumentacja, historia i dwa oddzielne środowiska integracji.'),
      ('Transfer_RockPro_20261024/RockPro/rockpro-cad','AKTYWNE ŹRÓDŁA kodu dodatku i Studio, testy, dokumentacja, wersjonowane siatki dostawców.'),
      ('Transfer_RockPro_20261024/RockPro/rockpro-cad/Integracja','Runtime aktualnego checkoutu: Python MCP, WinForms, konfiguracja i lokalna baza. Nie mylić z wdrożeniem obok.'),
      ('Transfer_RockPro_20261024/RockPro/Integracja','ZACHOWANE ODDZIELNE WDROŻENIE z prywatnymi danymi. Nie podmieniać go konfiguracją demo.'),
      ('Transfer_RockPro_20261024/RockPro/rockpro-cad/docs','Instrukcje, kontrakty, statusy funkcji i TODO. Punkt wejścia dla programisty: DEVELOPMENT.md.'),
      ('Transfer_RockPro_20261024/RockPro/rockpro-cad/assets/supplier-parts','74 siatki dostawców i 81 definicji do podglądu Studio, miniatury i indeks — wersjonowane w Git.'),
      ('Transfer_RockPro_20261024/RockPro/rockpro-cad/artifacts','Lokalne dowody, importy, analizy, testowe kopie CAD i paczki Vercel. Nie jest to folder finalnych projektów.'),
      ('raporty','Raporty importu, testów, audytu i wcześniejsze podsumowania.'),
      ('snapshoty','Archiwalne kopie bezpieczeństwa sprzed audytu.'),
      ('outputs','Wygenerowane materiały pomocnicze do przekazania, m.in. zestaw Penn/Adam Hall.'),
      ('workspace','Historyczne materiały pomocnicze; obecnie podfolder snapshoty. To nie aktywny checkout kodu.'),
      ('narzedzia','Narzędzia administracyjne, weryfikacja transferu, importer nowych wzorców i generator tej mapy.'),
    ]
    projects=[
      ('projekty/Telewizor_Hisense85_parametryczny_20261029','Hisense 85 — bieżąca R002 w 2027: 34 parametry sceny, regulacja zamków i uchwytów, 56 powiązanych obróbek, 439 opisów drzewa i mapa 383 części. ICS w 03_CAD/Do_sprawdzenia; instrukcja i testy w 06_Odbior/R002_montaz. R001 zachowana. Do odbioru konstruktora.'),
      ('projekty/Epson_EB-L630U','Prototypy T1 Epson: Prototyp_01–05 i wariant uchwytów. Starsze wersje zachowane; nie wszystkie mają ten sam stan odbioru.'),
      ('projekty/RPS_Penn_AdamHall_3f8d90f0','Projekt z wybranym zestawem okuć. Do ostatniego przeglądu: IronCAD_2027/..._montaz_v2.ics; 52 wystąpienia i 22 wycięcia. Odbiór konstruktora nadal osobny.'),
      ('projekty/Skrzynia_2000x3000x4000','Historyczny prototyp skrzyni 2×3×4 m, kolejne wersje profili i transportu. warsztat to próby i odzyskiwanie, nie finalne wydanie.'),
      ('projekty/Studio_T1_kompletna_2026-10-27','Materiały pełnego projektu T1 w Studio i sprawdzenia. Zapis Studio/JSON nie oznacza automatycznie pliku ICS.'),
      ('projekty/Studio_przeglad_2026-10-27','Przegląd projektów Studio: drafty, dowody i dwa nietypowe modele koncepcyjne w IronCAD_2027.'),
      ('projekty/Referencje','Referencja T_1 Epson — podgląd, nie nowa kopia do nadpisywania.'),
      ('projekty/_SZABLON_NOWEGO_PROJEKTU','Gotowa pusta struktura do skopiowania dla kolejnego zlecenia.'),
    ]
    t2=SOURCE/'artifacts/ironcad2023-pu1sp1-validation/t2-roundtrip-03/RockPro_T2_reference_IC2023.ics'
    t1=ROOT/'projekty/Epson_EB-L630U/Prototyp_05_pokrywa115_wyciecia/T1_mvp_v_4_3.ics'
    latest=ROOT/'projekty/RPS_Penn_AdamHall_3f8d90f0/IronCAD_2027/RockPro_Penn_AdamHall_800x650x800_wieko115_montaz_v2.ics'
    md=['# RockPro — mapa folderów i projektów','', 'Stan: 29.10.2026. Główny folder: `'+str(ROOT)+'`.','',
        '## Najszybciej znajdziesz','',
        '- Nowe modele od konstruktora: '+md_link(LIB/'CZYTAJ_MNIE.md')+' — 27 modeli w pięciu kategoriach.',
        '- Lista nowych plików do Excela: '+md_link(LIB/'KATALOG_PROJEKTOW.csv')+'.',
        '- T1, zapisana wersja MVP: '+md_link(t1)+'. Historia i ograniczenia w dokumentacji; nie oznaczamy jej automatycznie najnowszym wydaniem.',
        '- T2, sprawdzona kopia referencyjna 2023: '+md_link(t2)+'. Potwierdzony zapis/odczyt, nie pełny parametryczny wykonawca T2.',
        '- Ostatni przegląd Penn/Adam Hall w 2027: '+md_link(latest)+'.',
        '- Nowy projekt zacznij od kopii '+md_link(template)+'.','',
        '## Gdzie co jest','','| Folder | Zawartość i zastosowanie |','|---|---|']
    for relative,description in overview:md.append('| '+md_link(ROOT/relative,relative)+' | '+description+' |')
    md+=['','## Dotychczasowe projekty','','| Projekt | Jak go traktować |','|---|---|']
    for relative,description in projects:md.append('| '+md_link(ROOT/relative,relative)+' | '+description+' |')
    md+=['','## Nowe wzorce od konstruktora','',*library[8:],
        '## Zasada na przyszłość','',
        'Biblioteka projektu → kopia w nowym zleceniu → draft Studio → roboczy CAD → snapshot → eksporty → jawny odbiór konstruktora.',
        'W tej chwili jest to ustalona struktura folderów i szablon do kopiowania. Studio ani Excel nie zapisują automatycznie do tych folderów; ogólna automatyzacja pozostaje w ROC-54/ROC-55.',
        'Oryginały i ZIP-y pozostają zachowane. Model ICS to dokument 3D, ICD to rysunek 2D. Pusty TXT nie dostarcza wymagań. Wersja/parametryzacja/nośność nowych modeli nie wynikają z nazwy pliku.',
        '', '## Oprogramowanie i online','',
        '- Studio online: https://rockpro-studio.vercel.app — drafty w tej przeglądarce, bez wspólnej bazy i bez połączenia z desktopowym CAD.',
        '- Studio lokalnie: http://127.0.0.1:51342/FVpz8nmQczBPgO4yEpvwEugiffxTCB-J/ — dostępne, gdy lokalny serwer działa; dane robocze pozostają lokalne.',
        '- Linear, lista dalszych prac: https://linear.app/rock-pro/issue/ROC-47 .',
        '- Aktywna gałąź Git: `codex/roc42-catalog-continuation`, repo `qoopercodding/RockPro`. Transfer, prywatne projekty i nowe modele klientów nie są publikowane.',
        '', '## Indeksy i kompletność','',
        '- '+md_link(LIB/'INWENTARZ.json')+' — 34 wypakowane pliki, źródłowe ZIP-y i sumy SHA256.',
        '- `raporty/INDEKS_PLIKOW_CAD.csv` — indeks modeli/rysunków w głównych projektach, nowych źródłach i lokalnych dowodach; status pliku wynika z kategorii, nie z nazwy final.',
        '- `raporty/INDEKS_FOLDEROW.csv` — katalog główny i foldery do dwóch poziomów w aktywnym źródle, bez wnętrza .git i środowisk Python.',
        '- Wypakowanie i CRC/SHA: PASS. Nowe otwarcia CAD, parametryzacja, zgodność 2023/2027 i produkcja: NOT RUN.','']
    (ROOT/'MAPA_FOLDEROW_I_PROJEKTOW.md').write_text('\n'.join(md),encoding='utf-8')

    cad_rows=[]
    scopes=[(ROOT/'projekty','projekt / prototyp / kopia'),(LIB,'nowa biblioteka źródłowa — niezweryfikowana'),
            (ROOT/'Transfer_RockPro_20261024/RockPro/AI_CAD','zachowany pierwotny wzorzec'),
            (ROOT/'Transfer_RockPro_20261024/RockPro/Modele','historyczne modele z transferu'),
            (SOURCE/'artifacts','lokalne dowody / próby / kopie diagnostyczne')]
    for folder,role in scopes:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and p.suffix.lower() in ('.ics','.icd'):
                cad_rows.append((p.name,p.suffix.lower(),role,p.relative_to(ROOT).as_posix(),str(p.resolve()),p.stat().st_size))
    with (ROOT/'raporty/INDEKS_PLIKOW_CAD.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Nazwa','Format','Obszar','Ścieżka względna','Pełna ścieżka','Bajty']);w.writerows(cad_rows)
    folder_rows=[]
    for base,depth in [(ROOT,2),(SOURCE,2)]:
        def walk(p,level):
            if level>depth:return
            for child in sorted(p.iterdir()):
                if child.is_dir() and child.name not in ('.git','.venv','__pycache__','supplier-mesh-env','node_modules'):
                    folder_rows.append((child.relative_to(ROOT).as_posix(),str(child.resolve())))
                    walk(child,level+1)
        walk(base,1)
    with (ROOT/'raporty/INDEKS_FOLDEROW.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f,delimiter=';');w.writerow(['Folder względem katalogu głównego','Pełna ścieżka']);w.writerows(sorted(set(folder_rows)))

    html_rows=''.join('<tr><td>'+anchor(ROOT/p,p)+'</td><td>'+html.escape(d)+'</td></tr>' for p,d in overview)
    project_rows=''.join('<tr><td>'+anchor(ROOT/p,p.removeprefix('projekty/'))+'</td><td>'+html.escape(d)+'</td></tr>' for p,d in projects)
    page='''<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RockPro — mapa folderów i projektów</title><style>
    :root{color-scheme:light}body{margin:0;background:#f2f5f2;color:#203832;font:16px/1.55 system-ui,Segoe UI,sans-serif}main{max-width:1180px;margin:auto;padding:42px 28px}h1{font-size:34px;margin:8px 0}h2{margin-top:38px;color:#215a51}a{color:#176b60;text-decoration:none}a:hover{text-decoration:underline}.tag{color:#bd591b;font-weight:700;letter-spacing:.08em}.lead{font-size:18px}.cards{display:flex;flex-wrap:wrap;gap:14px}.card{background:white;border:1px solid #d7e2da;border-radius:12px;padding:18px 22px;flex:1;min-width:190px}.card strong{display:block;font-size:28px;color:#c6631d}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;padding:13px 16px;border-bottom:1px solid #dce5de;overflow-wrap:anywhere;vertical-align:top}th{background:#dce9e1}td:first-child{width:38%}code{background:#e1e9e4;padding:2px 5px;border-radius:4px}.note{border-left:4px solid #cf6b23;background:#fff6eb;padding:16px 20px;margin:22px 0}footer{margin-top:32px;color:#61746c}@media print{body{background:white}main{padding:0}a{color:inherit}h2{break-after:avoid}tr{break-inside:avoid}}@media(max-width:650px){main{padding:22px 12px}table{font-size:13px}td,th{padding:8px}.cards{display:block}.card{margin:10px 0}}
    </style><main><div class="tag">ROCKPRO / PRZEWODNIK LOKALNY</div><h1>Gdzie są foldery i projekty?</h1><p class="lead">Stan: 29 października 2026. Jedno miejsce do odnalezienia wzorców, prototypów, kodu i raportów.</p>'''
    page+='<p>'+html.escape(str(ROOT))+'</p><div class="cards"><div class="card"><strong>5</strong>kategorii nowych wzorców</div><div class="card"><strong>27</strong>nowych modeli 3D</div><div class="card"><strong>34</strong>pliki ze zweryfikowanym SHA</div></div>'
    page+='<div class="note">Biblioteka zawiera oryginały konstruktora. Przed edycją skopiuj model do nowego projektu. Import nie oznacza potwierdzenia parametryzacji ani odbioru produkcyjnego.</div>'
    page+='<h2>Szybkie odsyłacze</h2><p>'+anchor(LIB,'Biblioteka nowych wzorców')+' · '+anchor(template,'Szablon nowego projektu')+' · '+anchor(t1,'T1 MVP')+' · '+anchor(t2,'T2 referencja 2023')+' · '+anchor(latest,'Penn/Adam Hall — ostatni przegląd 2027')+'</p>'
    page+='<h2>Główna mapa folderów</h2><table><thead><tr><th>Folder</th><th>Co tutaj jest?</th></tr></thead><tbody>'+html_rows+'</tbody></table>'
    page+='<h2>Dotychczasowe projekty</h2><table><thead><tr><th>Projekt</th><th>Stan i przeznaczenie</th></tr></thead><tbody>'+project_rows+'</tbody></table>'
    page+='<h2>Nowa baza — wszystkie 27 modeli</h2><table><thead><tr><th>Kategoria</th><th>Model 3D</th><th>Status</th></tr></thead><tbody>'+''.join(rows_html)+'</tbody></table>'
    page+='<h2>Jak zaczynamy kolejne zlecenie?</h2><ol><li>Wybierz wzorzec z biblioteki.</li><li>Skopiuj pusty szablon do <code>projekty/KLIENT_ZLECENIE_NAZWA</code>.</li><li>Zachowaj kopię źródła i jego SHA; eksport draftu Studio włóż do <code>02_Studio</code>.</li><li>CAD zapisuj w <code>03_CAD/Robocze</code>, kolejne rewizje pod nową nazwą.</li><li>Snapshoty, eksporty i akceptację przechowuj w osobnych folderach szablonu.</li></ol><p>To struktura do stosowania od teraz; automatyczny zapis do folderów/ERP jest osobnym etapem ROC-54/ROC-55. Nazwa „Do_sprawdzenia” nie oznacza zatwierdzenia.</p>'
    page+='<h2>Pełne indeksy</h2><p>'+anchor(LIB/'KATALOG_PROJEKTOW.csv','Nowe pliki — CSV do Excela')+' · '+anchor(ROOT/'raporty/INDEKS_PLIKOW_CAD.csv','Wszystkie zinwentaryzowane CAD')+' · '+anchor(ROOT/'raporty/INDEKS_FOLDEROW.csv','Foldery')+' · '+anchor(ROOT/'MAPA_FOLDEROW_I_PROJEKTOW.md','Wersja tekstowa dokumentu')+'</p><footer>Dokument działa offline; Ctrl+F wyszukuje nazwę. Można wydrukować do PDF. Odsyłacze prowadzą do lokalnych plików i folderów na tym komputerze. Modele i prywatne dane nie zostały wysłane do Git, Linear ani Vercela.</footer></main></html>'
    (ROOT/'MAPA_FOLDEROW_I_PROJEKTOW.html').write_text(page,encoding='utf-8')
    print(json.dumps(dict(new_models=len(models),new_files=inventory['files'],indexed_cad=len(cad_rows),indexed_folders=len(set(folder_rows))),ensure_ascii=False))

if __name__=='__main__':main()
