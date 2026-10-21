---
name: rockpro-verification
description: Verify RockPro CAD runtime, MCP, geometry, UI or build changes and distinguish offline evidence from actual IronCAD integration before handoff.
---

# RockPro — weryfikacja zmiany

Przeczytaj „Sprawdzanie” w docs/DEVELOPMENT.md. Użyj scripts/Verify.ps1 z lokalnym venv albo jawnym `-Python`. Nie uruchamiaj Setup.ps1 do samego testowania: instaluje pakiety i zapisuje konfigurację.

- Backend/układ/SQLite/MCP: testy backendu i QA, handshake stdio, izolowane dane. Napraw przyczynę błędu, nie usuwaj testu dla PASS.
- WinForms: kompilacja i LayoutUiChecks, następnie zmieniony przepływ w IronCAD, jeśli twierdzisz, że działa w hoście. Sprawdź przycinanie, scroll, listy i komunikaty tam, gdzie dotyka ich zmiana.
- Geometria/adapter: dodatkowo nowa kopia znanego ICS, pomiar, zapis, ponowne otwarcie i raport niezmienności źródła. Nie testuj na produkcyjnym oryginale.
- Instalator/autostart: osobno bezpieczny restart i potwierdzenie załadowanej DLL. Kompilacja nie potwierdza instalacji.
- Same instrukcje/dokumentacja: audyt struktury, odnośników i zgodności ze źródłem oraz walidacja zmienionych skilli. Testów CAD nie powtarzaj bez zmiany zachowania.

Zapisz polecenia i wynik; raporty maszynowe trafiają do ignorowanego artifacts/. Oznacz PASS / FAIL / NOT RUN. Stare raporty są historyczne, nie dowodzą wykonania bieżącej wersji.

Jeśli testu natywnego nie można bezpiecznie wykonać, dokończ inne sprawdzenia, nazwij brakujący dowód i użyj checkpointu z $rockpro-scope-check. Nie deklaruj pełnej gotowości i nie przerywaj niezależnej pracy.
