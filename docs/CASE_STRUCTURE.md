# Struktura sceny i kompletność obróbek T1

Stan: 26.10.2026. Źródłem numerów i nazw etapów jest `part_registry.STAGES`.
`core_case/scene_structure.py` przypisuje części do tych samych etapów,
których używa podgląd. W scenie powstaje sześć zespołów organizacyjnych:

1. Sklejka — 10 płyt.
2. Profile aluminiowe — 24 profile.
3. Narożniki i wzmocnienia — 8 narożników i 8 wzmocnień.
4. Zamki i zawiasy — 8 wystąpień połówek okuć.
5. Uchwyty — 4 całe uchwyty.
6. Koła i gniazda do piętrowania — 4 koła, 4 gniazda, 2 podpory.

To grupy istniejących części, a nie dodatkowe fizyczne elementy zakupowe.
Gniazda pozostają w etapie 6. Historia wycięcia pozostaje w płycie/profilu,
który jest obrabiany; `owner` w planie wskazuje odpowiednie okucie.
Gotowe okucia zachowują własną strukturę i geometrię katalogową.

## Zasady dla kolejnych modeli

- Każde wystąpienie ma stabilny klucz techniczny w planie, ID CAD, polską nazwę,
  rodzinę i grupę wynikającą ze wspólnego rejestru. Nie przypisywać po nazwie
  wyświetlanej ani kolejności w drzewie. Kopia innego źródła wymaga nowej mapy ID.
- Rozmiar i położenie wynikają z parametrów sceny; zespoły etapów mają macierz
  jednostkową. Grupowanie nie zmienia gabarytów ani położeń części.
- Przeniesienie przez MoveChild potrafi wyzerować odwołania w wyrażeniach API
  2023. Odtwarzać powiązania z zatwierdzonego planu i nowej głębokości drzewa,
  zamiast przepisywać uszkodzone teksty pobrane po przeniesieniu.
- Do położeń i wymiarów stosować lokalne parametry techniczne z odwołaniami
  do sceny. Sprawdzić faktyczną zmianę wymiarów po grupowaniu oraz powrót.
- Dane konkretnego projektu, mapy ID, logi i próby natywne pozostają w
  ignorowanym `artifacts/<zadanie>-<data>/`. Kod reguł w `core_case`, polecenia
  w `scripts`, aktualna instrukcja w `docs`; nie uruchamiać historycznych
  generatorów z artifacts jako wersji produkcyjnej.

## Okucie obejmuje wszystkie swoje wycięcia

`validate_t1_machining` odmawia wykonania niepełnego planu. W aktualnym T1:

| Okucie | Wymagana obróbka |
| --- | --- |
| Każdy uchwyt H7159 | Wycięcie we właściwej ścianie bocznej |
| Każda połówka zamka | Wycięcie w przedniej sklejce i przerwa we właściwym profilu |
| Każda połówka zawiasu 27095 | Wycięcie w tylnej sklejce i przerwa we właściwym profilu |
| Każde gniazdo koła | Otwór we właściwej płycie górnej |

Łącznie 24 operacje. Kontrola sprawdza właściciela, cel, kompletność i duplikaty.
Przerwa w profilu nie zastępuje otworu w sklejce. Wykonawca natywny sprawdza
rzeczywistą obecność operacji oraz kolizje obu materiałów z zawiasem.
Zapis w instrukcji nie zastępuje tej bramki w kodzie.

## Szablon zawiasu 27095

[Producent](https://www.adamhall.com/shop/en/27095-27095) podaje montaż 79 × 82 mm,
głębokość 8 mm. Kontur HINGE_27095_OPENING w `t1_mounting.py` to prostokąt
zaokrąglony R11,4 mm, ze środkami naroży X=±28,1/Z=±29,6 mm, zgodnymi z
pomiarami kielicha CAD i przejścia do kołnierza. Jest współdzielony przez
obydwie tylne płyty i związany z kotwą okucia. Nie rozciąga się przy zmianie
gabarytów skrzyni. Zmiana SKU wymaga osobnego szablonu.

W odzyskanej rewizji konstruktora tylne otwory miały oznaczenia L905/915
i rozmiary 76 × 52 oraz 76 × 22 mm. Próba wykazała kolizję z 27095;
nie przyjmować tych otworów jako zweryfikowanego szablonu nowego zawiasu.
Model CAD wymaga też normalizacji ramy szkicu tworzonego przez szablon hosta:
przesunięcie (10,10,1 mm) nie może przesuwać konturu montażowego.

Natywne dopasowanie sprawdzane jest na prototypie. `production_approved=false`;
odbiór technologiczny przez konstruktora jest osobnym krokiem.

## Uruchomienie i dowody

Plan: `scripts/prepare_t1_structure.py`, wykonanie:
`scripts/run_t1_structure_job.py <nowy-katalog-dowodów> <plan.json>`.
Polecenie czeka na wspólną blokadę CAD, również przy równoległej pracy drugiego
czatu; nie uruchamia równoległego wykonawcy ani nie zapisuje modelu.
Faza `cuts` dodaje wycięcia, `group` porządkuje scenę i odbudowuje powiązania.
Ponowna faza `group` sprawdza istniejące grupy zamiast tworzyć duplikaty.

Dowody lokalne: `artifacts/t1-structure-20261026/`.
PASS: cztery wycięcia, ich ruch po zmianie parametrów i 4 pary sklejka–zawias
bez kolizji w `native-cuts-06/result.json`. Kontrole obejmują też profile.
PASS: grupowanie oraz odbudowa powiązań po przeniesieniu części w
`native-group-05/result.json`. Sześć grup zachowuje 72 wystąpienia. Trzy próby
(docelowe wymiary, zmiana wymiarów/odsunięć, powrót) obejmują pozycje,
orientacje, rozmiary płyt i podpór, 4 kontury 79 × 82 mm, ich powiązania,
24 rzeczywiste operacje oraz kolizje zawiasów ze sklejką i profilami. Grafika PASS.
Pełny harness PASS: `artifacts/verification/20261026T185311168179Z/results.json`.
Scene14 pozostaje niezapisana, z korpusem 235 mm i pokrywą 115 mm.
Próba dodatkowego końcowego odczytu ActiveDoc odmówiła działania, gdy drugi
czat aktywował T2; nie zmieniła żadnej sceny. Dowodem odbioru T1 jest powyższy
natywny raport przypięty do jej GUID, a nie nazwa aktywnej zakładki.
Zapis/ponowne otwarcie i odbiór wizualny: NOT RUN na życzenie użytkownika.
