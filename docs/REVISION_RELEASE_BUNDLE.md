# ROC-21 — pakiet wydania przypięty do rewizji

core_case/release_bundle.py tworzy nowy katalog z kopią ICS, jawną listą
załączników i manifestem. Nie nadpisuje wcześniejszego wydania. Każdy załącznik
musi wskazywać tę samą rewizję i SHA modelu. Manifest zawiera wersję/hash wejścia,
reguł i wzorca, hash i rozmiar każdego pliku oraz wyniki kontroli.

inspect_bundle sprawdza pliki i bieżący model. Zmiana modelu daje status outdated,
zmiana załącznika invalid. Historyczne pliki i manifest pozostają zachowane.
Braki BOM, rysunków i plików produkcyjnych są widoczne jako pending_roles.
Wyniki FAIL / NOT RUN pozostają jawne i blokują ready_for_review.
Nie ma automatycznej zgody produkcyjnej ani identyfikacji materiału po kolorze CAD.

Polecenie dla obecnego prototypu:

    Integracja/.venv/Scripts/python.exe scripts/Prepare-Release.py --registry-report artifacts/registry-native-20261024-01/registry_report.json --project-id Epson-prototype --revision-id prototype-03-registry-01 --output artifacts/overnight-20261024/release-prototype-03

Natywny model i jego raport są sprawdzane hashami. CSV occurrence_bom rozlicza
zarządzane korzenie: 66 wpisów nie oznacza 66 części zakupowych. Ilość zakupowa
i zatwierdzony materiał pozostają puste. Złożone okucie i połówka zamka nie są
bez dodatkowego mapowania jedną pozycją zakupową. Rysunki i pliki produkcyjne
są jawnymi krokami ręcznymi, zgodnie z zakresem ROC-21 i potwierdzonym spike.

To techniczny przyrost, a nie ukończenie produkcyjnego BOM i rysunków.
Do zamknięcia całego zadania potrzebne są te dokumenty oraz rozliczenie materiału
z tej samej, odebranej rewizji. Pakiet prototypu zachowuje status draft.

PASS: pięć testów — kompletne wiązanie wersji, dezaktualizacja po zmianie modelu,
zmiana pliku, odmowa obcej rewizji/duplikatów/wyjścia ze ścieżki oraz zachowanie
pustych ilości zakupowych i materiałów. Pakiet rzeczywistej zapisanej kopii ICS
powstał lokalnie w artifacts/overnight-20261024/release-prototype-03; kontrola
hashy PASS, rysunki/produkcja pending, materiał i BOM zakupowy NOT RUN.

Pełny harness po wdrożeniu: PASS, artifacts/verification/20261024T213454896201Z/results.json.


## 25.10 — kontrola spójności przy ponownym odczycie

Odtworzono i naprawiono błędny wynik kontroli: podmiana model.ics wraz z nowym
hashem wpisanym do plików manifestu mogła przejść inspect_bundle mimo innego
model_sha256 w przypiętej rewizji. Teraz dokładnie jedna kopia ICS musi mieć
hash zgodny z wiązaniem rewizji; rozbieżność daje MODEL_BINDING_MISMATCH,
a więcej niż jeden model MODEL_COPY_COUNT. Pozostałe role i metadane plików
są jawnie walidowane podczas odczytu, nie tylko przy tworzeniu pakietu.

Ponowny odczyt wymaga niepustej, ograniczonej listy kontroli o unikalnych
nazwach i statusach PASS/FAIL/NOT RUN. Pusta lista nie może dać odbioru przez
all([]). Niejednoznaczne lub nieznane kontrole są odrzucane. Prawidłowy pakiet
z FAIL albo NOT RUN zachowuje draft i brak ready_for_review; żaden wynik nie
nadaje production_approved.

PASS: dziewięć testów pakietu. Nowe regresje najpierw odtworzyły pięć błędnych
asercji starego kodu, następnie przeszły po naprawie. Pełny harness PASS:
artifacts/verification/20261025T084401784804Z/results.json.
Ponownie sprawdzono istniejący zapisany pakiet rzeczywistego prototypu:
artifacts/release-integrity-20261025/inspection.json. Wszystkie pliki pozostały
bitowo identyczne; pakiet jest draft, rysunki/produkcja pending, zakupowy BOM
i materiał NOT RUN. To kontrola dyskowa, bez ponownej operacji natywnego CAD.
Hashy nie traktujemy jako podpisu ani autoryzacji konstruktora. Historycznych
pakietów nie przepisano i nie oznaczono całego ROC-21 Done.
