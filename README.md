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

22 testów backendu + 7 odbiorczych. Testy te nie zastępują testu natywnego IronCAD na komputerze docelowym.

Konfigurator rozmieszczenia: [LAYOUT.md](LAYOUT.md) — podgląd 3D, zapis w SQLite oraz gabaryty kopii ICS.

Studio wzorców: [podglądy rodzin skrzyń](docs/ALL_REFERENCE_PREVIEWS.md) — lokalny
interfejs przeglądarkowy z rzeczywistymi siatkami, zmianą gabarytu i ruchem
zespołów. Uruchomienie z `Integracja`:

```powershell
.\.venv\Scripts\python.exe -m rockpro_cad.reference_studio --bundle "<pakiet wzorców>" --previews "<index.json>"
```

Prywatny pakiet modeli i indeks eksportów trzeba przekazać osobno; nie należą
do repozytorium. Podgląd zapisuje szkic JSON i nie generuje jeszcze modelu ICS.

Docelowy kreator: [proces w 11 krokach](docs/CUSTOM_CASE_WORKFLOW.md) — typ,
wieka, sekcje, katalog i rozmieszczenie części, review, CAD/snapshoty
oraz wstępny BOM i integracja z firmowym Excelem. To specyfikacja do wdrożenia.

Instrukcje dla agentów i powtarzalne sprawdzanie: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Audyt i kolejność dalszych poprawek: [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md).

Kreator kroków 1–3 już działa: [obsługa i zapis draftów](docs/WIZARD_STEPS_1_3.md).
W Studio wybierz **Nowa konstrukcja**; nowy widok `wizard.html` pokazuje edytowalne
sekcje 3D, ich współpracę i wymiary. Drafty są zapisywane z rewizjami w lokalnej SQLite.

Aktualizacja kreatora: [trzy typy bez podtypów](docs/WIZARD_THREE_TYPES.md).
Przód skrzyni 3-elementowej automatycznie licuje z górną pokrywą.
