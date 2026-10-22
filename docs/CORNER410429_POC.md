# 410429 — narożniki na prostokątnej skrzyni

## Checkpoint kodu

Stan przy małym pushu 22.10.2026: warstwa obliczeniowa i wykonawca CAD
zaimplementowane; 22 testy narożników PASS, niezależny przegląd obliczeń PASS.
Model A 914 × 602 × 352 mm przeszedł natywny zapis, ponowne otwarcie
i niezależną kontrolę 18 części. Próba B i powrót C nie mają jeszcze
potwierdzonego końcowego odbioru w tym checkpointcie; nie oznaczaj pełnego
A/B/C jako ukończonego na podstawie tego commitu. Odbiór wyglądu: **NOT RUN**.

Dowody aktualnej próby pozostają lokalnie w `native-03/` pod katalogiem
raportów wskazanym niżej. Modele klienta, snapshoty i logi nie trafiają do Git.

## Zakres

Osiem rzeczywistych narożników 410429 pochodzi z zapisanego modelu Epson:
cztery z grupy wieka i cztery z grupy korpusu. Próba ma oddzielić regułę
montażu tej jednej rodziny od pozostałych okuć. Docelowy model demonstracyjny
zawiera dziesięć nowych, uproszczonych płyt oraz osiem źródłowych narożników.
Nie jest przebudową całej oryginalnej skrzyni i nie obejmuje profili,
uchwytów, zatrzasków, zawiasów, kół ani wycięć.

Zmiany dotyczą wyłącznie nowych plików. Źródłem jest kopia bajtowa zapisanego
Epsona; nie utożsamiamy jej z historyczną, niezapisaną zawartością pamięci.
Prywatne modele, dokładne identyfikatory i raporty pozostają w lokalnym
`artifacts/corner410429-20261022/`.

## Odczyt i geometria odniesienia

Odczyt obejmuje macierze do rodzica i świata, lokalne obrysy, objętości,
liczniki topologii oraz surowe wierzchołki płaskich powierzchni. W źródle są
również istniejące transformacje lustrzane. Zachowujemy te konkretne warianty
bez prostowania macierzy lub tworzenia nowego odbicia z jednej części.
Żądany ruch montażowy jest osobno właściwym ruchem sztywnym.

Wybrane rzeczywiste zewnętrzne powierzchnie płyt wyznaczają prostokątną ramę
odniesienia **914 × 602 × 352 mm**. To rama docelowej demonstracji, a nie
deklaracja pełnego obrysu wszystkich elementów źródłowego złożenia.

Odczyt wykrył ręczne odstępstwa w części płyt wieka: lewa płyta jest przesunięta
o 18,5 mm względem bocznej płaszczyzny odniesienia korpusu, a inna płyta ma
szerokość 945,5 mm i wychodzi poza tę ramę. Nie zmieniamy tych części
w oryginale. Nowe płyty demonstracyjne tworzą regularną skrzynię zgodną
z jawną ramą odniesienia; tej normalizacji nie wolno przedstawiać jako
zatwierdzenia oryginalnego projektu do produkcji.

Nowe płyty mają zmierzoną grubość 9,8 mm, a wysokość wieka wynosi 104,13 mm.
Uproszczony korpus wypełnia źródłową strefę profilu/szczeliny 8,63 mm,
aby dziesięć prostokątnych płyt tworzyło spójny obrys o wysokości 352 mm.
Nie jest to dokładna kopia formatek ani technologii połączenia wieka z korpusem.

Źródłowe początki narożników są odsunięte o 16,5 mm do wnętrza względem
odpowiednich naroży ramy. Pomiary trzech lokalnych płaskich powierzchni części
wspierają kandydacki punkt rejestracji `[16,5; 16,5; 16,5]` mm. Powiązanie
punktu ze źródłem musi wynikać z zapisanych świadectw, a nie z samego obrysu
73,5 mm lub nazwy katalogowej. Nie jest to automatyczna zgoda konstruktora
na montaż, nośność lub współpracę z profilem.

## Reguła zmiany gabarytu i symetrii

Każdy narożnik ma stały identyfikator, ścieżkę źródłową i jedno z ośmiu miejsc
`[sx, sy, sz]`, gdzie każda wartość jest równa 0 lub 1. W ramie skrzyni
o wymiarach `[L, D, H]` odpowiada mu naroże `[sx·L, sy·D, sz·H]`.

Przy zmianie wymiarów przeliczany jest ruch punktu rejestracji względem
tego naroża. Rozmiar i orientacja konkretnej części pozostają niezmienione.
Zmiana położenia części w świecie jest przeliczana również do układu jej
rodzica; nie można wpisywać współrzędnych świata jako współrzędnych lokalnych.

Symetria jest kontrolowana dla całego zbioru ośmiu punktów w każdej osi,
łącznie z powiązaniem punktu z konkretnym miejscem. Sama zgodność środka
zbioru albo oddzielnych list X/Y/Z nie wystarcza. Źródłowa asymetria,
brak części i jednostronna zmiana mają powodować odmowę, bez uśredniania.

## API i dowody

Warstwa obliczeniowa: `core_case/corner_mount.py`.

- `capture_corner_binding(evidence, trusted_bindings)` przypina osiem części,
  ramę płyt i zadeklarowane kandydackie punkty rejestracji do źródła.
- `plan_corner_resize(binding, target_size_mm)` wyznacza położenia z zachowaniem
  źródłowych wariantów, geometrii i symetrii.
- `validate_corner_observation(plan, observed)` porównuje rzeczywiste pomiary
  z planem i odtwarzanymi regułami geometrycznymi.

Obliczenia nie wywołują CAD i nie nadają zgody produkcyjnej. Test natywny jest
oddzielnym krokiem: nowe kopie, pomiar przed zapisem i po ponownym otwarciu,
kontrola źródeł oraz odrębne archiwum pliku.

## Praca bez przejmowania pulpitu

Zwykłe otwieranie widocznej sceny nie należy do tego przepływu. Oficjalne
ICAPI udostępnia `OpenFile2` z `vbVisible=false` dla scen oraz tworzenie
ukrytego dokumentu. Kod ma pilnować własności dokumentów, wyniku
`pbAlreadyOpen`, aktywnego dokumentu i identyfikatora okna pierwszoplanowego.
Nie używa Computer Use, aktywacji dokumentu, schowka, ustawiania fokusu,
widoczności aplikacji ani restartu IronCADa.

Zgodność geometrii po zapisie nie zastępuje wizualnego odbioru modelu.
Jeżeli widok nie został sprawdzony, raport musi podawać **NOT RUN**.

## Wykryte rozbieżności i sposób sprawdzania

Pierwsza pełna próba zatrzymała się po zapisaniu i ponownym otwarciu A:
oba pomiary osobno spełniały wymagania geometrii, ale dodatkowa równość
całych dokumentów JSON była fałszywa. Nie uruchomiono wtedy B/C.

Oddzielna próba diagnostyczna `native-02/A-diagnostic/` zapisała surowe
`measurement_before_save.json` i `measurement_after_reopen.json`. Niezależne
porównania wykazały dokładnie dwie różnice: objętości części w
`observation.occurrences[*].body_signature.volume_m3`. Największa różnica
wyniosła około `3,39e-21 m³`. Wszystkie pozostałe pola, w tym identyfikatory,
pozycje, macierze, topologia i 1344 zmierzone pozycje wierzchołków, były równe.

Porównanie trwałości wymaga więc dokładnej zgodności pozostałych pól i osobnej
kontroli dodatniej, skończonej objętości według wcześniej stosowanej tolerancji
`max(1e-15 m³, abs(objętość_odniesienia) * 1e-8)`. Nie jest to ogólne
zwiększenie tolerancji geometrii. Surowe pomiary muszą być zapisane przed
końcowym porównaniem, także gdy późniejsza kontrola odmówi akceptacji.

## Powtarzanie próby przez programistę

Punkt wejścia: `scripts/accept_corner410429_poc.py`. Argumenty wskazują jawnie
istniejący lekki dokument kontekstowy, zapisany plik Epson, znormalizowany
odczyt, przypięcia rejestracji, surowy odczyt oraz świadectwa powierzchni:

```text
--context <otwarty_lekki_model.ics>
--source <zapisany_Epson.ics>
--evidence <normalized_evidence.json>
--trusted-registration <trusted_registration.json>
--raw-evidence <fresh_corner_panel_evidence.json>
--contact-witnesses <native_contact_registration.json>
--output <nowy_katalog_w_artifacts>
```

Rzeczywiste ścieżki pochodzą z lokalnego zestawu pomiarów. Nie przepisuj ścieżek
autora ani identyfikatorów CAD do innego modelu bez ponownego odczytu.
Domyślny tryb tworzy tylko plany i nie wywołuje CAD. Dopiero `--native`
uruchamia trzy nowe sceny: A o wymiarach źródłowej ramy, B 1100 × 720 × 410 mm
oraz C z powrotem do ramy A. To ponowne generowanie z parametrów, nie edycja
jednego dokumentu przez trwałe wiązania tabeli IronCAD.

Wykonawca trzyma wspólną blokadę zapisu CAD przez całą próbę. Eksportuje dwa
źródłowe kontenery po cztery części, zachowując ich warianty geometryczne.
Każdy stan ma nowy model roboczy, surowe pomiary przed zapisem i po otwarciu,
odrębny snapshot oraz kontrolę SHA256. Przy błędzie kolejny rozmiar nie jest
uruchamiany. Wznowienie wymaga nowego katalogu; nie nadpisuj wcześniejszych
dowodów.

Próba nie dodaje przycisku montażu w dodatku ani nowego narzędzia MCP.
Nie zmienia sześciu istniejących parametrów szkieletu ani manifestu WoodLAB.
