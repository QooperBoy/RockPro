from pathlib import Path
import json,csv,html,collections,shutil
refs=json.loads(Path('docs/catalog/hardware-reference.json').read_text(encoding='utf-8'))['items'];lookup={a:x for x in refs for a in x['aliases']}
audit=json.loads(Path('../Integracja/assembly_audit.json').read_text(encoding='utf-8'))['rows']; native=json.loads(Path('artifacts/parts-identification/native_inventory.json').read_text(encoding='utf-8'))['rows']
out=Path('../Integracja/parts');out.mkdir(exist_ok=True)
old=out/'Epson_czesci_do_opisania.csv';shutil.copy2(old,out/'Epson_czesci_przed_identyfikacja.csv')
custom={
 'konstrukcja':('Zespół płyt konstrukcyjnych','5 ścian/płyt w każdej połówce. Metadane PVC nie potwierdzają rzeczywistego materiału sklejki.','rola_potwierdzona_struktura'),
 'Srodek':('Wypełnienie i przegrody wewnętrzne','Piana na projektor; Jeżyk przegroda na pilot; przegroda mała i duża. Rodzaje i gęstość pianki nie są opisane.','rola_potwierdzona_nazwy'),
 'koła':('Zespół jezdny i podkładki montażowe','4 złożenia kół i 2 elementy Część33 (120 × 580,4 × 18 mm). W części tocznej obrys 100 × 100 × 40 mm. Producent i nośność nieustalone.','rola_potwierdzona_kod_brak'),
 'Zespół1':('Importowany zespół geometrii SKP','21 bezpośrednich dzieci SkpPart/SkpAssembly. Prawdopodobnie model urządzenia referencyjnego; dokładny model niepotwierdzony. U części importowanych bbox jest nieprawidłowy.','nieustalony_model_urzadzenia'),
 'Część2648':('Własny element prostopadłościenny z wycięciem','Gabaryt lokalny 150 × 582,4 × 50 mm, operacje Block i H Block. Brak materiału i opisu BOM; funkcja technologiczna niepotwierdzona. Nie oznaczać jako pianka bez dowodu.','nieustalona_funkcja')}
groups=collections.defaultdict(list)
for r in audit:
 if len(r['path'])==2:groups[tuple(r['path'])].append(r)
result=[]
for (section,name),nodes in sorted(groups.items()):
 ref=lookup.get(name);ids=[x['id'] for x in nodes];children=sum(x.get('children_count',0) for x in nodes)
 if ref:pl=ref['name_pl'];note=ref['note'];state='kod_katalogowy_dopasowany';maker=ref['manufacturer'];code=ref['code'];url=ref['source_url']
 else:pl,note,state=custom[name];maker=code=url=''
 if name=='2643':state='pusty_zespol_kod_katalogowy_znany'
 result.append(dict(zespol=section,nazwa_w_CAD=name,nazwa_opisowa=pl,producent=maker,kod_katalogowy=code,wezly_glowne=len(nodes),bezposrednie_dzieci=children,ids=','.join(map(str,ids)),status=state,uwagi=note,zrodlo=url,automatyczne_wstawianie='NIE — brak pełnej walidacji montażu'))
with old.open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,fieldnames=list(result[0]),delimiter=';');w.writeheader();w.writerows(result)
(out/'Epson_identification.json').write_text(json.dumps(dict(source_model='Showcase_Epson_parametry.ics',read_depth=5,native_nodes=len(native),identification=result),ensure_ascii=False,indent=2),encoding='utf-8')
shutil.copy2('artifacts/parts-identification/native_inventory.json',out/'Epson_native_inventory.json')
header='''# Rozpoznanie części — model Epson

Stan 21.10.2026. Odczyt API do głębokości 5: 1143 węzły, w tym 258 obiektów typu Part. Węzły operacji BREP/wyciągnięć nie są oddzielnymi pozycjami zakupowymi. Klasyfikacja obejmuje wszystkie 24 grupy nazw widoczne bezpośrednio pod górą/dołem (36 wystąpień).

## Wynik

Rozpoznano katalogowo wszystkie kody okuć/profili z głównego drzewa (12 kodów, licząc osobno dwie połówki profilu EG-0500). Nie oznacza to pełnego potwierdzenia każdej geometrii i wariantu. Dwie nazwy własne wymagają ustalenia funkcji/modelu: Zespół1 i Część2648. Koła rozpoznano funkcjonalnie i geometrycznie, ale nie ustalono producenta/nośności.

## Istotne ustalenia

- 410429: po cztery części wewnątrz grupy góry i dołu, czyli osiem narożników, a nie dwa.
- EG-0113: po osiem odcinków na górę/dół, razem szesnaście; długości są różne.
- EG-0500: po cztery odcinki każdej połówki profilu zamykającego.
- B1930: po dwa elementy wewnątrz grupy, razem cztery. B1121: dwa wystąpienia na górze i dwa na dole, razem cztery.
- H7159: cztery kompletne złożenia uchwytów; ich wewnętrzne części nie są dodatkowymi uchwytami. H2026: jedno złożenie uchwytu narożnego.
- 17251S / 17251S_1: dwa dopasowane zestawy zamka, rozdzielone między górę i dół; nie cztery kompletne zamki. 270836 / 270836_góra: analogicznie dwie pary.
- PN - W0968Z: cztery miseczki pod koła. Ich obrys w modelu 136 × 90 mm odpowiada rzutowi z katalogu producenta. Głębokość, otwory, tolerancje i koło współpracujące wymagają osobnej kontroli.
- 2643: kod katalogowy zawiasu jest znany, lecz w tym dokumencie to pusty zespół bez dzieci. Nie ma podstaw do liczenia go jako aktywnego zawiasu.
- Materiały w CAD nie są wiarygodną bazą zakupową: liczne stalowe okucia mają Aluminum - 7178, a płyty konstrukcyjne mają PVC. Zachować osobne pola „materiał CAD” i „materiał katalogowy”; nie poprawiać automatycznie oryginału.
- Odczytane pola BOMPartNumber/BOMDescription są puste. Nazwa w drzewie jest wskazówką, nie zatwierdzonym numerem zakupowym.
- Część2648: własna bryła 150 × 582,4 × 50 mm z wycięciem. To nie jest rozpoznany gotowy produkt katalogowy. Materiał i funkcja pozostają otwarte.
- Zespół1 zawiera import SKP. Niektóre obrysy API mają skrajne/ujemne wartości; te wartości należy odrzucić, zamiast liczyć z nich rozmiar urządzenia.

## Tabela

| Zespół | Nazwa CAD | Rozpoznanie | Węzły główne / dzieci | Status | Źródło / uwagi |
|---|---|---|---|---|---|
'''
lines=[]
for x in result:
 source=('[katalog]('+x['zrodlo']+') ')if x['zrodlo']else''
 lines.append('| '+ ' | '.join([x['zespol'],x['nazwa_w_CAD'],x['nazwa_opisowa'],str(x['wezly_glowne'])+' / '+str(x['bezposrednie_dzieci']),x['status'],source+x['uwagi']]).replace('\n',' ')+' |')
text=header+'\n'.join(lines)+'\n\nWęzły/dzieci opisują drzewo CAD, nie automatycznie ilość zakupu. Automatyczne wstawianie pozostaje wyłączone do ustalenia płaszczyzn montażu, otworów i reguł parowania. Oryginalny ICS nie został zapisany. Zmiany widoczności podczas oględzin były tylko podglądem.\n'
(out/'Epson_rozpoznanie_czesci.md').write_text(text,encoding='utf-8')
body=''.join('<tr>'+''.join('<td>'+html.escape(str(x[k]))+'</td>'for k in ['zespol','nazwa_w_CAD','nazwa_opisowa','producent','status','uwagi'])+'<td>'+('<a href="'+html.escape(x['zrodlo'],quote=True)+'">Katalog producenta</a>'if x['zrodlo']else'Geometria własna')+'</td></tr>'for x in result)
page='''<!doctype html><html lang="pl"><meta charset="utf-8"><title>RockPro — rozpoznanie części Epson</title><style>body{font:15px Segoe UI,sans-serif;background:#eef2f6;color:#243140;margin:32px}header{border-left:7px solid #f36d12;padding:16px 24px;background:white}h1{margin:0 0 10px}input{margin:24px 0;padding:12px;width:450px;border:1px solid #bac7d2;border-radius:6px}table{border-collapse:collapse;background:white;width:100%}th,td{padding:12px;text-align:left;border-bottom:1px solid #dae1e8;vertical-align:top}th{background:#233140;color:white;position:sticky;top:0}a{color:#a74300}td:nth-child(5){color:#8b5b09}small{color:#526479}</style><header><h1>Rozpoznanie części — Epson</h1><div>24 grupy nazw • wszystkie kody katalogowe dopasowane • dwie nazwy własne do wyjaśnienia</div><p>Kod znaleziony w katalogu nie jest zatwierdzeniem geometrii ani montażu. Puste 2643, niezgodne materiały CAD i pary zamków/zawiasów opisano w uwagach.</p><small>Odczyt API 21.10.2026. Szczegóły i liczebności fizyczne: Epson_rozpoznanie_czesci.md. Dane modelu pozostają lokalnie.</small></header><input id="q" placeholder="Szukaj kodu, funkcji lub producenta…"><table><thead><tr><th>Zespół</th><th>Nazwa CAD</th><th>Co to jest</th><th>Producent</th><th>Status</th><th>Uwagi</th><th>Źródło</th></tr></thead><tbody>'''+body+'''</tbody></table><script>document.querySelector('#q').oninput=e=>{let q=e.target.value.toLocaleLowerCase('pl');document.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLocaleLowerCase('pl').includes(q))}</script></html>'''
(out/'Epson_rozpoznanie_czesci.html').write_text(page,encoding='utf-8')
print('Saved',len(result),'rows; refs',len(refs),'native',len(native))
