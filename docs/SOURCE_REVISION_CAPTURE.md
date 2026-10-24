# ROC-42 — jedna zapisana rewizja źródła

`rockpro_cad.core_case.source_capture` zbiera inwentarz, transformacje i szkic
manifestu z jednej nowej kopii pliku ICS. To krok przygotowania dowodów do
ROC-42/ROC-17. Nie zatwierdza montażu, nie nadaje zgody produkcyjnej, nie eksportuje
jeszcze okucia i nie zmienia panelu ani allowlisty starego szkieletu.

## Uruchomienie

Z katalogu `Integracja`, przy uruchomionym IronCAD i bez równoległej operacji CAD:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.core_case.source_capture --source 'C:\projekty\zapisany-model.ics' --expected-sha256 <niezaleznie_sprawdzony_SHA256> --output-dir '..\artifacts\nowa-rewizja'
```

Domyślnie jest to PLAN_ONLY bez COM i bez zapisywania plików. Dodanie `--native`
wykonuje przechwycenie. Wyjście musi być nowym katalogiem w `artifacts/`; istniejące
katalogi nie są nadpisywane. W lokalnej próbie źródło przypięto sumą SHA256 z
oryginalnego `PLIKI.csv`, zweryfikowaną podczas importu archiwum.

Opcjonalne `--node-id <ID> --node-name <nazwa> --occurrence-path <indeksy>` wybiera
jedno jawne wystąpienie. Należy podać wszystkie trzy argumenty. ID, ścieżka, nazwa
i poprawna transformacja muszą odpowiadać świeżym danym. Nazwa nie służy do
wyszukiwania zamiennika. Przy odmowie zachowane są surowe obserwacje; nie powstaje
`selected_binding.json`. Wybór wystąpienia nie zatwierdza jego roli ani reguły.

Czysta funkcja `select_source_binding(inventory, poses, ...)` pozwala wykonać ten
wybór po przejrzeniu zachowanych danych, bez ponawiania pełnego odczytu CAD.
Wymaga przypiętej zapisanej rewizji oraz dokładnej tożsamości i poprawnej ramy
świata. Jedyny dopuszczony błąd surowego czytnika pozycji to jawnie wykazane
odbicie niezmienionej ramy rodzica: macierz jest ponownie sprawdzana pod kątem
sztywności i odbicia. Nie jest prostowana. Odbicie ramy świata, skalowanie,
ścinanie i pozostałe błędy blokują wybór.

## Zapisane dowody

- `source_snapshot.ics`: byte-identyczna kopia; oryginał nie jest otwierany.
- `raw_inventory.json`: wynik istniejącego czytnika wraz z błędami i ograniczeniami.
- `poses.json`: świeże macierze, obrysy i błędy odczytu. Odbicia pozostają jawne;
  nie są zamieniane na zwykłe obroty.
- `inventory.json`: inwentarz związany z kontrolowanym otwarciem tej kopii.
- `manifest.json`: nowa mapa tożsamości i pełne rozliczenie odczytanych węzłów.
- `manifest_validation.json`: poprawność rozliczenia i pozostałe blokady.
- `selected_binding.json`: tylko po poprawnym, jawnym wyborze wystąpienia.
- `capture_receipt.json`: powodzenie operacji, integralność oryginału/kopii,
  zamknięcie własnego dokumentu i granice dowodu, także po błędzie.

Zapisana rewizja jest rozpoznawana wyłącznie dla własnej, nowo otwartej,
byte-identycznej kopii: pełna ścieżka, GUID i `Modified=false` muszą pozostać
zgodne w obu czytnikach oraz po nich. Kontrole SHA256 obejmują oryginał i kopię.
Zwykłe `parts.inspect_source` nadal zachowuje konserwatywne `not_proven` dla
arbitralnego, już otwartego dokumentu. Surowy raport nie jest nadpisywany.

Własna kopia jest zamykana w `finally`, także po niepowodzeniu. Jeżeli mimo braku
setterów stała się zmodyfikowana, jej stan jest zachowywany w nowej kopii przed
zamknięciem. `pbAlreadyOpen=true` odmawia przejęcia własności dokumentu. Operacja
nie zamyka ani nie zapisuje innych dokumentów hosta i nie uruchamia IronCAD.

Nowy odczyt otrzymuje własną mapę identyfikatorów; stara mapa nie jest przenoszona
przez dopasowanie nazw. Uzgodnienie tożsamości między rewizjami jest oddzielnym,
jawnym krokiem. Nie ustawia się `runtime_template_compatible=true`, zgody
montażowej, zgody produkcyjnej ani liczności zakupowych.

Powodzenie przechwycenia nie oznacza, że wszystkie obrysy i ramy są poprawne.
Czytniki mogą uczciwie zwrócić stan `partial`; ich błędy pozostają w danych i
blokują wykorzystanie danego wystąpienia. Następny krok: wybrać właściwy korzeń
H7159 ze świeżych danych, wykonać eksport i pomiary z tej samej przypiętej rewizji,
a potem uzgodnić istniejący kontrakt `catalog_assets` i sidecar.

Testy: `test_source_capture.py` — przypięcie źródła przed COM, wyłączność wyjścia,
niezapisany stan, dryf tożsamości i pozycji, zmiana oryginału, błąd otwarcia,
sprzątanie dokumentów, pełne rozliczenie oraz odmowa podmiany wystąpienia.
