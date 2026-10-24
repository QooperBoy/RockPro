# Nocna kolejka RockPro — rozpoczęta 24.10.2026

Polecenie użytkownika: snapshot, zadania z Linear po kolei, rutynowe decyzje
samodzielnie, pytania na rano. Nie oznaczamy niewykonanych odbiorów jako Done.

Snapshot PASS: workspace/snapshoty/przed-nocna-kolejka-20261024-232012 w głównym
workspace Ironcad. Git bundle, archiwum 268 plików kodu/projektów/dowodów,
spójny backup SQLite, manifest SHA256 i test integralności ZIP.
HEAD startowy 4bd25ec0b1fbf0ce26de4790b0c3b3a592aba5e4, czysty checkout.
Snapshot obejmuje zapisane pliki; niezapisane dokumenty CAD pozostają w hoście.

## Kontynuacja automatyczna

Heartbeat rockpro-nocna-realizacja-kolejki działa w tym czacie co 30 minut.
Nie powtarzać snapshotu ani zakończonych przyrostów. Nie uruchamiać kilku CAD
writerów. Nie uruchamiać pełnego harnessu równocześnie z natywnym writerem,
bo testy przechwytywania źródła współdzielą blokadę.

Konektor Linear widzi Modivo (MOD), a nie Rock_Pro (ROC). Browser IAB karta 2
ma prawidłową sesję Rock_Pro. Lista team/ROC/all odczytana, surowe AX w
raporty/LINEAR_KOLEJKA_NOC_TOP.txt i BOTTOM.txt głównego workspace.
Indeks odczytanych linków: artifacts/overnight-20261024/linear_queue.json.
Onboarding ROC-1–4 nie należy do projektu CAD. ROC-5–10 to epiki. ROC-15/43 Done.

## Stan zadań

| Zadanie | Stan lokalnej nocy | Dowód / dalsza praca |
|---|---|---|
| ROC-42 | Częściowo gotowe, pełny odbiór zablokowany danymi źródłowymi | Świeży manifest 403/403 z saved-source-native-20261024-02 i pełny prototyp 66 korzeni z registry-native-20261024-01 istnieją. Nieznana Część2648/import, SKU kół i zatwierdzenia źródła pozostają otwarte. Nie zastępować źródłowego manifestu manifestem prototypu. |
| ROC-16/17 | Gotowe działające prototypy; brak pełnego odbioru rodziny | Profile, okucia, uchwyty i pary kół/gniazd są natywne i parametryczne, dowody w docs/CASE_HANDLES_V3.md i PART_FAMILY_REGISTRY_TASK.md. H2026 i pełny źródłowy szablon niezatwierdzone. |
| ROC-40 | Kontynuacja wymagań odczytana | Porównanie baseline/current/target dla czterech H7159 działa i ma native PASS. Brak pełnego ekranu decyzji, trwałych odsadzeń i integracji z wykonaniem. Patrz NATIVE_MANUAL_CHANGES.md. |
| ROC-18 | Done w Linear po zapisie dowodów | XLSX, 3 przykłady, walidacja jednostek, trwałe wersje źródeł w tej samej SQLite, atomowy CAS i idempotencja. 9 nowych testów PASS; pełny harness/build/UI PASS 20261024T213039539715Z. Wrapper PowerShell PASS. docs/EXCEL_CONFIGURATION_INPUT.md. |
| ROC-20/22/19 | Implementacje i dowody istnieją, pozostają integracja pełnych okuć i odbiór | Nie zamykać całych zadań na podstawie syntetycznej próby. |
| ROC-11–14,27–28,34–39 | Wymagania trzeba rozpatrzyć, zależne od danych/licencji/użytkownika | Nie tworzyć fikcyjnych cenników, zakupów, licencji ani odbiorów klienta. Wykonać dostępne przygotowanie techniczne, zapisać dokładne braki. |
| ROC-21 | Pakiet rewizji i wykrywanie dezaktualizacji PASS; pełny odbiór wymaga dokumentów | release_bundle.py, 5 testów, rzeczywisty draft pakietu w artifacts/overnight-20261024/release-prototype-03. Rysunki/produkcja pending, zakupowy BOM/materiał NOT RUN. docs/REVISION_RELEASE_BUNDLE.md. |
| ROC-23 | Implementacja katalogu i ekstrakcji PASS; pełny harness PASS 20261024T214134912003Z | Per-field units/source/status, brak automatycznego scalenia wariantów, null/conflict, projekt zapytania bez wysyłki. Lokalny PDF/EML odczytany. Rekord Epson ze strony producenta zapisany do wspólnej SQLite. docs/DEVICE_CATALOG.md. |
| ROC-24 | Filtry/ranking i evaluator benchmarku PASS; pełny historyczny odbiór zablokowany etykietami | 5 testów, harness PASS 20261024T214444139483Z; rzeczywista trafność historyczna NOT RUN, brak zamrożonego oznaczonego zbioru. docs/FAMILY_RECOMMENDATIONS.md. |
| ROC-25 | Backend wariantów i kontroli wyjmowania PASS; harness PASS 20261024T214830686049Z | Do 3 odrębnych układów, jawne orientacje/kierunki, AABB toru +Z, blokada niepotwierdzonych danych dla wydania. 5 testów PASS, 2 propozycje rzeczywistego rekordu Epson. Pełny UI nowej ścieżki NOT RUN. docs/DEVICE_LAYOUT_VARIANTS.md. |
| ROC-26 | Bramka propozycji z budżetami i logami PASS; harness PASS 20261024T215341335976Z | agent_server.py ma statyczną allowlistę bez zapisów/zgód/CAD. Czas rzeczywisty, tokeny/koszt jawnie niedostępne. Zewnętrzny model/pilotaż H0–H6 NOT RUN. configure.py zmienione w źródle; istniejące mcp-config.local.json przepięte wyłącznie na agent_server.py po zachowaniu kopii, bez resetu demo. docs/AGENT_RUN_POLICY.md. |
| ROC-27 | Audyt lokalny i dokumentacja producenta wykonane; próba produkcyjna zablokowana dostępem | WoodLAB PLAN nie znaleziono w lokalnych instalacjach. Dokumentowany ASCII/Excel, resztki, rzaz i grain; preferowany istniejący PLAN po próbie na stanowisku. Technologia rzeczywista null/nieznana. docs/MATERIAL_INTEGRATION_AUDIT.md. |
| ROC-28 | Indeks źródeł i macierz braków gotowe; pięć zakończonych zleceń NOT RUN | docs/CUTTING_BOM_IMPORT.md. Brak kompletnych cen, rzeczywistego rozkroju i kosztów; nie zastępować pięcioma kartami SQLite. |
| ROC-29 | Import i agregacja backendu PASS | 7 testów; pełny harness PASS 20261024T220828460477Z. Niezmienne źródła, CAS, powtórzenia bez duplikacji, nowa rewizja zastępuje popyt, oddzielne technologie/daty/grain. Rzeczywisty zatwierdzony BOM klienta NOT RUN. |
| ROC-30 | Referencyjny rozkrój, neutralny eksport i niezależny checker PASS | 5 testów, docs/CUTTING_PLAN_CONTRACT.md. PLAN/maszyna/realna technologia NOT RUN. Nie deklarować optimum ani produkcji. |
| ROC-31 | Transakcyjny backend magazynu PASS | 6 testów, także wyścig o tę samą resztkę; brak podwójnego odejmowania i cofania zużycia. docs/INVENTORY_CONTRACT.md. Ekran/pilotaż klienta NOT RUN. |
| ROC-32 | Terminowe bilanse i propozycje backendu PASS | 6 testów; 120/20/30/paczka25 → 75, spóźniona → 100. docs/PURCHASE_PROPOSALS.md. Brak faktycznych ofert/limitów/odbioru; wspólny budżet i transport wielopozycyjny nieoptymalizowane. |
| ROC-33,41,44 | Kolejne prace techniczne | Odczytać opisy i rozpatrywać według zależności; nie pomijać. |

## Następna czynność

ROC-21: przyrost gotowy i pełny harness PASS 20261024T213454896201Z. ROC-23 gotowe technicznie: katalog i ekstrakcja lokalnych źródeł z 5 testami PASS; aktualizacja Linear jeszcze do wykonania. ROC-24: przyrost zapisany i sprawdzony, benchmark historyczny czeka na dane. ROC-25 backend ukończony i przetestowany; UI nowej ścieżki pozostaje NOT RUN. ROC-26 bramka gotowa, pełny agent/zużycie modelu i pilotaż NOT RUN. FIX_FIRST ROC-20 zakończony (szczegóły na końcu). ROC-27 audyt lokalny wykonany, próba PLAN zablokowana instalacją/technologią klienta. Następne ROC-28/29: inwentarz historycznych źródeł i import BOM/formatek z agregacją, bez zgadywania materiału/grain. Uzupełnić też status ROC-21 w Linear jako In Progress; nie Done z powodu brakujących dokumentów produkcyjnych. Po każdym sprawdzonym przyroście
uzupełnić ten dziennik, dowody i commit. Pełny zakres zakończony tylko wtedy,
gdy istnieją dowody dla kryteriów zadania; blokery to osobna lista na rano.


Dodatkowy FIX_FIRST ROC-20 zakończony: catalog_native cleanup ma potwierdzony
SaveAs i zatrzymuje własność przy nieudanym zachowaniu. Native PASS po błędzie:
artifacts/overnight-20261024/catalog-cleanup-native/verification.json.
Pełny harness PASS 20261024T215741060210Z.
