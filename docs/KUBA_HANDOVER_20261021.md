# RockPro CAD — aktualny handover dla Kuby

Stan: 21 października 2026. Repozytorium: https://github.com/QooperBoy/RockPro

## Co działa

- Natywny dodatek C# / WinForms w IronCAD 2027, przycisk w Dodatkach i lokalny backend Python MCP stdio + SQLite.
- Karta projektu, ręczne statusy etapów, historia zmian z porównaniem przed/po oraz osobne archiwum kopii CAD.
- Konfigurator urządzeń: wymiary, liczba sztuk, orientacja, rozmieszczenie, przegrody i komora na akcesoria; podgląd 3D oraz ranking wariantów według objętości.
- Wersjonowanie układów i powiązanie wersji ze snapshotem ICS. Karta i każdy etap mają osobne wersje; konflikt UI–AI blokuje nadpisanie starszym formularzem i zachowuje szkic.
- Odczyt sześciu parametrów RP_* i kontrolowana zmiana wymiarów znanego szkieletu 10 płyt na kopii ICS.
- Interfejs polski i angielski, przełącznik języka, opisy paneli, podpowiedzi i oznaczenie funkcji planowanych. Zmiana języka zachowuje niezapisane dane i tokeny wersji.

## Granice obecnego MVP

CAD obsługuje znany szkielet demonstracyjny, nie dowolne archiwalne skrzynie WoodLAB. Urządzenia, przegrody i akcesoria są obecnie obrysami w podglądzie; do ICS przekazywane są gabaryty szkieletu. Automatyczny dobór okuć, pianki, rysunki produkcyjne, import maili/archiwum, Excel, nesting i zakupy to dalsze etapy. Status „zatwierdzony ręcznie” nie jest wydaniem produkcyjnym.

Panel korzysta z MCP, ale nie zawiera jeszcze samodzielnego agenta AI pracującego w tle. Agent w zewnętrznym kliencie może korzystać z ograniczonych narzędzi MCP.

## Linki na start

- [Repozytorium](https://github.com/QooperBoy/RockPro)
- [Instalacja i przekazanie](https://github.com/QooperBoy/RockPro/blob/main/HANDOVER.md) oraz [autostart](https://github.com/QooperBoy/RockPro/blob/main/AUTOSTART.md)
- [Instrukcje dla agenta](https://github.com/QooperBoy/RockPro/blob/main/AGENTS.md) i [kontrakt developerski](https://github.com/QooperBoy/RockPro/blob/main/docs/DEVELOPMENT.md)
- [Konfigurator i ograniczenia CAD](https://github.com/QooperBoy/RockPro/blob/main/LAYOUT.md)
- [Wersjonowanie układów i snapshotów](https://github.com/QooperBoy/RockPro/blob/main/docs/LAYOUT_VERSIONING.md)
- [Karta, etapy i konflikty UI–AI](https://github.com/QooperBoy/RockPro/blob/main/docs/PROJECT_CONCURRENCY.md)
- [Języki, pomoc i testy UI](https://github.com/QooperBoy/RockPro/blob/main/docs/UI_LANGUAGE.md)
- [Projekt w Linearze](https://linear.app/rock-pro/project/rockpro-cad-d99cc3102643/overview)
- [Bieżący odbiór i instrukcja testów — ROC-22](https://linear.app/rock-pro/issue/ROC-22/rp-12-wprowadzic-akceptacje-historie-zmian-i-odzyskiwanie-po-bledzie)
- [Po MVP: instalacja u RockPro i import archiwum — ROC-39](https://linear.app/rock-pro/issue/ROC-39/po-mvp-wdrozenie-u-rockpro-i-import-archiwum-cad-e-maili-do-bazy)

Starsze liczby testów/narzędzi w dokumentach bazowego wydania są historyczne. Aktualny zestaw sprawdza harness, a narzędzia MCP odczytujemy przez tools/list.

## Jak zacząć pracę

1. Sklonuj repo, otwórz agenta w jego katalogu i poleć mu przeczytać AGENTS.md oraz docs/DEVELOPMENT.md.
2. Na swoim Windows x64 z IronCAD 2027 i ICAPI SDK wykonaj instalację według HANDOVER.md. Repo nie zawiera bazy klienta, SDK ani gotowych DLL; baza powstaje lokalnie.
3. Uruchom `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -WithAddinBuild -WithUiChecks` po przygotowaniu środowiska.
4. Wykonaj test na demonstracyjnej kopii ICS i odbiór opisany w ROC-22. Testy bez CAD nie potwierdzają integracji na nowym komputerze.
5. Dalej uzgodnijmy formalną akceptację konkretnej rewizji, blokadę wydania niepełnej paczki i odzyskiwanie po awarii. ROC-22 pozostaje In Progress.

## Weryfikacja dotychczasowa

Pełny harness i niezależny przegląd agenta: PASS. Na komputerze autora sprawdzono integrację IronCAD oraz główne widoki PL/EN, historię i konflikt zapisu. Instalacja na komputerze Kuby/RockPro, pełny odbiór użytkownika i macierz różnych DPI wymagają osobnego sprawdzenia.
