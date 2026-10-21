# ROC-15 / ROC-42 — odbiór przyrostu 21.10.2026

Implementacja: Sol high. Niezależny przegląd: Astra high, PASS po poprawieniu
wykrytych luk. Dotyczy kodu kontraktów i źródłowego inwentarza offline.

> Ten dokument zachowuje historyczny odbiór kontraktów sprzed implementacji planera.
> Bieżący stan generatora, natywnego prototypu i blokad: [CORE_PROGRESS.md](CORE_PROGRESS.md).

## Wynik historyczny

| Obszar | Wynik | Granica odbioru |
|---|---|---|
| ROC-15 | PASS | Wersje, jednostki, źródła wymiarów, rewizje, kotwy, właściwe obroty, identyfikatory, członkostwo grup i kontekst zgód |
| ROC-42 — rozliczenie źródła | PASS | Wszystkie 403 węzły, 24 grupy kandydackie, 11 pustych zespołów, zachowane 35 niepoprawnych obrysów |
| ROC-42 — gotowość montażu | ZABLOKOWANA | Brak zatwierdzonych ról, ram, kotew, parowania i reguł montażu; nierozstrzygnięte części; częściowa jakość źródła |
| Regresja repozytorium | PASS | Repository, backend, parts, core-design-green, core-contracts, QA, harness |
| Przegląd niezależny | PASS | 63 dodatkowe sprawdzenia i 43 testy pakietu (23 kontraktu, 20 manifestu) |
| Pełny generator ROC-43 | RED | 173 wymagania nadal oczekują na planer i geometrię; zero errors/skips/expectedFailure |
| CAD i produkcja | NOT RUN | Bez montażu, zmian ICS, zapisu/otwarcia, wdrożenia lub migracji danych |

`valid=true` oraz `accounting_complete=true` w manifeście potwierdzają poprawność
rozliczenia inwentarza, a `production_ready=false` blokuje użycie go do montażu.
223 węzły klasy physical nie stanowią 223 pozycji zakupowych. Ilości zakupowe
pozostają niezatwierdzone. Dane źródłowe i mapy UUID pozostają w lokalnym artifacts.

## Dokumentacja i powtórzenie

- [CASE_CONTRACT.md](CASE_CONTRACT.md): publiczne walidatory i znaczenie pól.
- [PARTS_MANIFEST.md](PARTS_MANIFEST.md): źródłowy manifest, CLI, mapowanie UUID,
  statusy oraz odmowa użycia szkicu jako gotowego szablonu.
- [ROC43_TDD.md](ROC43_TDD.md): osobna regresja GREEN i specyfikacja RED generatora.

Z katalogu checkoutu, z przygotowanym Pythonem:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify.ps1 -Python '..\Integracja\.venv\Scripts\python.exe'
```

Oczekiwany wynik zwykłej regresji: PASS. Nowe testy są w kroku `core-contracts`.
Nie uruchamia on IronCAD. Historyczny RED jest już GREEN i należy do zwykłej
regresji `core-design`; nie stosuj dawnego oczekiwania niezerowego kodu wyjścia.

Dowody lokalne: `artifacts/verification/20261021T211612594635Z/`,
`artifacts/roc15-42-review/review-results.json`, `artifacts/roc15/`,
`artifacts/roc15-42/root-manifest/` i `artifacts/roc15-42/core-red.json`.
Ponowne uruchomienie manifestu z zachowaną mapą UUID daje taki sam wynik;
istniejące wyjście nie jest nadpisywane. Odczyt i zapis JSON wymagają UTF-8.

## Status Linear i następny przyrost

[ROC-15](https://linear.app/rock-pro/issue/ROC-15/rp-05-zdefiniowac-schemat-parametrow-jednostek-i-rewizji)
może być zamknięte dla kontraktu v1. Integracja UI/Excel z tym wejściem oraz pełny
generator pozostają w kolejnych zadaniach.

`layout.count` określa urządzenia w jednej skrzyni. Opcjonalne `order_quantity`
określa liczbę zamawianych skrzyń; brak tego pola pozostaje nieustalony.

[ROC-42](https://linear.app/rock-pro/issue/ROC-42/core-zbudowac-pelny-manifest-czesci-i-regul-szablonu-epson)
pozostaje In Progress: ukończono warstwę inwentarza, nie awans do szablonu montażu.
Dalsza praca: zweryfikowane role semantyczne, pomiar transformacji i ram ścian,
kotwy i symetria wszystkich grup oraz konkretne pary zamków, zawiasów i kół/gniazd.
Należy rozstrzygnąć części własne/importowane i SKU koła, następnie potwierdzić
źródło o odpowiedniej jakości. Te pomiary współpracują z ROC-16; pierwsze
zatwierdzone okucie przechodzi do ROC-17. Wycięcia i styki pozostają w ROC-41.
