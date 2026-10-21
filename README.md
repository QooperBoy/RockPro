# RockPro CAD

Natywny dodatek IronCAD 2027: panel projektu, parametry szkieletu skrzyni, historia snapshotów oraz lokalny serwer MCP i SQLite.

**Wersja MVP 0.4.** Obsługa CAD obejmuje znany szkielet dziesięciu płyt. To nie jest jeszcze automat do dowolnych projektów WoodLAB ani wydanie produkcyjne.

## Start

1. Windows x64, Python x64, Git, IronCAD 2027 z ICAPI SDK i .NET Framework.
2. Przeczytaj [HANDOVER.md](HANDOVER.md).
3. W stałym katalogu checkoutu: `powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -InstallAddin`.
4. Otwórz model `Integracja/skeleton/demo/RockPro_Epson_szkielet_MVP.ics` i dodatek **Dodatki → RockPro CAD**.

Agent programistyczny powinien najpierw przeczytać [AGENTS.md](AGENTS.md). Zmiany wizualne: [UI_CHANGELOG.md](UI_CHANGELOG.md).

## Źródła

- `Integracja/rockpro_cad/addin`: C# / WinForms i rejestracja dodatku.
- `Integracja/rockpro_cad/mcp`: protokół MCP, operacje CAD, SQLite i testy.
- `Integracja/rockpro_cad/qa`: testy odbiorcze i checklisty.
- `Integracja/*.py`: adapter COM i walidatory geometrii.

Dane klientów, baza SQLite, logi, środowisko Python, wygenerowane DLL i robocze rewizje nie należą do repozytorium. Zależność Python IronCAD jest przypięta do konkretnego commita. SDK jest pobierane z lokalnej instalacji IronCAD podczas budowania.

## Testy bez CAD

```powershell
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\mcp -p test_*.py -v
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\qa -p test_acceptance.py -v
```

19 testów backendu + 7 odbiorczych. Testy te nie zastępują testu natywnego IronCAD na komputerze docelowym.

Konfigurator rozmieszczenia: [LAYOUT.md](LAYOUT.md) — podgląd 3D, zapis w SQLite oraz gabaryty kopii ICS.
