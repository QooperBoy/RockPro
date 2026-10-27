# Wspólny podgląd 3D siedmiu wzorców

27.10.2026. Rozwinięcie [workstation](WORKSTATION_3D_PREVIEW.md) na siedem wzorców.
To podgląd koncepcji; nie generator parametrycznych ICS ani odbiór technologii.

## Kontrakt i interfejs

Jeden renderer Three.js obsługuje wybór modelu i wariantu. Siatki poprzedniego
modelu oraz materiały są zwalniane. Zmiana wyboru anuluje nieaktualny fetch;
opóźniona odpowiedź nie podmienia geometrii nowego wariantu. Wczytywanie blokuje
sterowanie wymiarami i ruchem. Ustawienia są zachowywane osobno dla każdego SHA
i wariantu, także dla M01/M07 o wspólnych historycznych identyfikatorach CAD.

Rozszerzenie szkicu JSON `preview.motion_values` ma odrębną listę dopuszczonych
ruchów dla konkretnego wariantu. Nieznany ruch, inny hash lub przekroczony zakres
blokują import. Starszy zapis czterech wysuwów workstation pozostaje obsługiwany.
Gabaryt dotyczy siatek sklejki w zapisanym stanie wzorca, nie potwierdzonego
światła wnętrza ani transportowego gabarytu zamkniętego.

Wdrożone moduły podglądu, przypisane jawnymi ścieżkami do inwentarzy:

| Wzorzec | Moduły |
|---|---|
| M01 / M07 | Osłona górna i grupa docisków; warianty pozostają odrębne |
| M02 | Czapka oraz niezależne uniesienie miksera |
| M03 | Pokrywa oraz wnętrze |
| M04 | Cztery półki ze swoimi wkładami |
| M05 | Pokrywa oraz pięć niezależnych wkładów |
| M06 | Pokrywa i dwie niezależne referencje opraw |

Rozsunięcie opisane jako poglądowe nie symuluje potwierdzonego toru zawiasu ani
dopuszczalnego demontażu. Elementy drzewa Rendering są odrębnie przełączane;
nie zaliczamy ich do gabarytu sklejki ani zatwierdzonego zakupowego BOM.

## Źródła geometrii i odzyskiwanie

Sześć dodatkowych eksportów Web Viewer przeszło kontrolę zachowania źródeł,
kopii i kontekstu. Analiza treści wykazała jednak braki siatek, puste dane oraz
niepoprawne wartości w części plików. Sam sukces wywołania eksportera nie jest
dowodem kompletności widoku. U Martina eksporter zwrócił tylko pięć siatek.

Alternatywny `ExportKernelMeshes.cs` używa `IZPart.GetSpecifiedPolyMeshes` na
nowej kopii tylko do odczytu. Sprawdza ID części, obrysy wierzchołków, macierze
i źródła. Nie wywołuje regeneracji, Update ani Save. Materiał pochodzi z API,
a normalne trójkątów wynikają z rzeczywistej siatki. Zamykana jest wyłącznie
własna kopia. Zapisany plik źródłowy oraz istniejące dokumenty pozostają zachowane.

Uwaga wydajnościowa: parametr odchylenia normalnych jest w stopniach. Pierwszy
pełny odczyt użył zbyt drobnego 0,1° i stał się kosztowny na W0968z. Poprawione
ustawienie to 15°, zgodne z przykładem producenta
`ICAPI/Samples/cplusplus/ICAPIQuery/QuerySupport.cpp`, obok `dNormalDev`.
Częściowe wyniki zachowano; nie są zaliczane jako udany kompletny eksport.
Kontrola anulowania działa przed następną częścią i nie przerywa trwającego
wywołania SDK. Nie wolno zwalniać blokady ani zabijać klienta jako pozornego
anulowania, gdy kod nadal wykonuje się w hoście.

Źródła M03 i M06 mają po cztery węzły `17251S` bez bryły: natywny odczyt
potwierdza zero ścian i zerowy obrys, zgodny z wcześniejszym inwentarzem.
Takie węzły pozostają w rejestrze `source_empty_parts`; interfejs pokazuje
komunikat, zamiast tworzyć zastępczy zamek. Ładowanie sprawdza dokładne ścieżki
wszystkich części, także pustych. Każdy inny brak siatki blokuje podgląd.

Limity konwertera rozdzielają tekst eksportu od bufora GPU: do 768 MiB JSON
łącznie, 128 MiB na plik oraz 256 MiB wynikowej geometrii Float32. M01 ma około
554 MB tekstu i 1,53 mln trójkątów; dawny wspólny limit 512 MiB odrzucał ten
poprawny eksport. Nowe ograniczenie nadal blokuje zbyt duży bufor podglądu.

Odczyt i konwersja wszystkich siedmiu wzorców są zakończone. M02 i M04 korzystają
z kompletnych eksportów Web Viewer; pozostałe pięć z odczytu siatek jądra.
Wszystkie 2829 węzłów części są rozliczone: 2821 siatek i osiem potwierdzonych
pustych węzłów źródła. Ponowne obliczenie SHA wszystkich siedmiu oryginałów
po zakończeniu potwierdziło ich niezmienność.

| Wzorzec | Siatki | Puste węzły źródła |
|---|---:|---:|
| M01 — 85_SMHX | 433 | 0 |
| M02 — Wing Compact | 162 | 0 |
| M03 — ChainMaster | 387 | 4 |
| M04 — Workstation | 453 | 0 |
| M05 — pięć wkładów | 434 | 0 |
| M06 — Martin | 569 | 4 |
| M07 — Hisense | 383 | 0 |

Podgląd zachowuje zapisane pozycje dodatkowych zespołów źródła. Nie odgaduje
roli anonimowych części ani nie przenosi automatycznie urządzenia do wnętrza.

## Uruchomienie gotowych pakietów

Z `Integracja`, po przygotowaniu prywatnego indeksu danych:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "<pakiet wzorców>" --previews "<index.json>"
```

Indeks `rockpro.preview-index/1` mapuje klucze modeli na katalogi względne
wewnątrz wybranej biblioteki. Serwer sprawdza SHA źródeł, inwentarzy i buforów.
Nie publikuje plików ICS ani dowolnych katalogów. Starszy parametr `--workstation`
nadal działa. Prywatne indeksy i geometria pozostają poza Gitem.

## Wyniki sprawdzeń — 27.10.2026

- PASS: 10 testów Python/HTTP, w tym różne hashe M01/M07, listy ruchów
  i odmowa ukrycia brakującej geometrii jako pustego elementu źródła.
- PASS: reguły geometrii JS oraz składnia modułów.
- PASS: wszystkie siedem modeli w rzeczywistym WebGL; gabaryt +10%, brak
  skalowania sztywnych okuć, każdy ruch osobno oraz dokładny powrót macierzy.
- PASS: eksport i ponowny import JSON każdego wariantu; M01/M07 zachowują
  oddzielne wartości suwaków; szybkie przełączanie pozostawia najnowszy model
  i jeden canvas. Brak błędów JavaScript, układ 430 px bez poziomego przepełnienia.
- PASS: pełny `scripts/Verify.ps1`: repository, backend, parts, core-design,
  core-contracts, qa, harness. Pierwsza próba core-contracts podczas eksportu
  została zablokowana przez działający mutex CAD; pełna próba po zwolnieniu
  wykonawcy przeszła bez zmiany ochrony współbieżności.
- Native resize/save/reopen: NOT RUN; bieżące zmiany dotyczą podglądu.

Raporty i dane robocze: `artifacts/family-3d-20261027/`: `browser-report.json`,
`final-dataset-report.json`, `index.json` i obrazy `Mxx-browser.png` oraz
`Mxx-open-browser.png`. Pełna regresja: `artifacts/verification/20261027T121939050113Z/`.
Są to lokalne prywatne dowody; nie dodajemy ich do repozytorium.
