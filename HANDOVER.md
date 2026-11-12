# RockPro CAD — przekazanie dla Jakuba Siwca

Stan 10.11.2026: aktualny start projektu to [docs/KUBA_HANDOVER.md](docs/KUBA_HANDOVER.md); ten plik opisuje bazową instalację dodatku i backendu (wersja 0.3), uzupełnioną o bieżące różnice. Konfigurator urządzeń i układu: [LAYOUT.md](LAYOUT.md). Liczby narzędzi MCP i testów odczytuj z `tools/list` i wyniku `scripts/Verify.ps1`, nie z tego opisu.

Obserwowalność (rejestr przebiegów SDK/AI, logi agentów, panel Phoenix) — instrukcja krok po kroku: [docs/OBSERVABILITY_HOWTO.md](docs/OBSERVABILITY_HOWTO.md). Na co dzień: `scripts\Start-Observability.ps1` uruchamia Phoenix i automatyczny eksport, a każde zadanie CAD zapisuje się samo; instrukcja panelu: [docs/PHOENIX_DASHBOARD.md](docs/PHOENIX_DASHBOARD.md).

Aktualny kontrakt pracy i jedno polecenie sprawdzeń: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Otwieraj agenta w checkoutcie, żeby wykrył lokalne .agents/skills. Stan audytu: [docs/REPOSITORY_AUDIT.md](docs/REPOSITORY_AUDIT.md).

## Co dostajesz
Scalone źródła frontendu WinForms, backendu MCP stdio i lokalnej bazy SQLite, adapter COM, walidatory oraz demonstracyjny szkielet ICS (10 płyt). Repozytorium rozpoczyna wspólną historię zmian na podstawie wydania MVP 0.3. Nie zawiera środowiska autora, bazy klientów, korespondencji, oryginalnych projektów produkcyjnych ani bibliotek DLL dostawcy. Baza projektów zostanie utworzona lokalnie od zera.

## Wymagania
- Windows x64, **IronCAD 2023 (25.0)** i jego ICAPI SDK — wersja klienta (u firmy 2023 PU1 SP1, 25.0.12.18734). 2027 (29.0) pozostaje osobno sprawdzanym celem; szczegóły: [docs/IRONCAD_2023_COMPATIBILITY.md](docs/IRONCAD_2023_COMPATIBILITY.md).
- Modele ICS zapisane w 2027 nie otwierają się w 2023. Sparametryzowane rodziny z paczki 03.11 (`*_IC2027.ics`) wymagają odtworzenia w 2023.
- Python x64 (u autora 3.14.3), Git i dostęp do internetu podczas instalacji zależności.
- .NET Framework 4.x z kompilatorem `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`.
- Build.ps1 `-IronCADYear 2023|2027` (domyślnie 2023) oczekuje `C:\Program Files\IronCAD\<rok>\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll` i `C:\Program Files (x86)\Microsoft.NET\Primary Interop Assemblies\stdole.dll`. Przy innym układzie dostosuj ścieżki w Build.ps1.
- Po odinstalowaniu innej wersji IronCAD zostają rejestracje ICAPI użytkownika i Python zgłasza „błąd podczas ładowania biblioteki typu/DLL”. Naprawa: `Repair-IcApi.py --year 2023` (krok 0.3 w [OBSERVABILITY_HOWTO](docs/OBSERVABILITY_HOWTO.md)).
- IronCAD i backend uruchamiaj jako ten sam użytkownik w tej samej sesji Windows, z takim samym poziomem uprawnień.

## Instalacja
1. Rozpakuj cały katalog do stałej lokalizacji, np. `C:\Dev\RockPro_CAD_MVP_0.3_Kuba`. Zachowaj strukturę `Integracja` i jej podkatalogi.
2. Zapisz dokumenty i zamknij IronCAD przed instalacją/rejestracją nowej DLL.
3. W PowerShell w katalogu paczki uruchom:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Python python -IronCADYear 2023 -InstallAddin
```

`-Python` może być pełną ścieżką do python.exe. Skrypt tworzy venv, instaluje przypięte zależności, ustawia lokalne ścieżki demonstracji, kompiluje dodatek i rejestruje go wyłącznie w HKCU. Bez `-InstallAddin` nie rejestruje dodatku. Nie zmieniaj potem położenia folderu bez ponownego configure.py i rejestracji. Nie uruchamiaj instalatora na komputerze autora: zastąpiłby jego rejestrację tym wydaniem.

4. Otwórz IronCAD i `Integracja\skeleton\demo\RockPro_Epson_szkielet_MVP.ics`. Model jest ignorowany przez Git i nie ma go w klonie: trzeba go otrzymać osobnym kanałem i sprawdzić, czy otwiera się w 2023. Bez niego natywny test 2023 wykonaj według [OBSERVABILITY_HOWTO](docs/OBSERVABILITY_HOWTO.md) (`scripts/run_2023_parametric_job.py`).
5. Dodatki → RockPro CAD → Połącz / Odśwież. Utwórz kartę projektu i przypisz otwarty, zapisany plik demonstracyjny.
6. Odczytaj parametry. Zmień np. RP_Length o 20 mm i zastosuj na kopii. Sprawdź nowy plik ICS, raport i historię snapshotów. Nie testuj na produkcyjnej skrzyni.

Jeżeli nie ma przycisku: sprawdź SDK, wynik kompilacji, rejestrację HKCU i restart IronCAD. Jeśli COM nie widzi dokumentu: otwórz wskazany plik, zamknij modalne dialogi i sprawdź zgodność sesji/uprawnień. Nie naprawiaj tego przez wyłączanie walidacji.

## Podłączenie agenta AI
Instrukcja krok po kroku dla Claude Code i Codex oraz test decyzji agenta: [docs/AGENT_SETUP.md](docs/AGENT_SETUP.md) (szablon `.mcp_example.json`; lokalny `.mcp.json` jest ignorowany przez Git).

Panel sam uruchamia MCP jako lokalny subprocess stdio, nie potrzebuje klucza AI. `configure.py` generuje `mcp-config.local.json` z absolutnymi ścieżkami dla klienta obsługującego format mcpServers. W Codex/innym kliencie przenieś wartości command i args do formatu jego konfiguracji; nie nadpisuj pozostałych serwerów. Uruchom ponownie klienta i sprawdź tools/list. Klient AI dostaje `Integracja/rockpro_cad/mcp/agent_server.py` (tylko allowlista odczytu i propozycji, [AGENT_RUN_POLICY](docs/AGENT_RUN_POLICY.md)); panel nadal używa operatorowego `server.py`.

Narzędzia agenta: allowlista odczytu i propozycji z `agent_server.py` (sprawdź `tools/list`); zapisy, set_stage, wykonanie CAD i odzyskiwanie ma tylko operatorowy `server.py`. Allowlista nie ogranicza wbudowanych narzędzi klienta (pliki/powłoka w Claude Code lub Codex) — patrz sekcja o prywatnych plikach w OBSERVABILITY_HOWTO. MCP nie ma portu HTTP. Nie dodawaj narzędzia wykonującego dowolny Python/polecenia powłoki.

## Architektura i zakres
Panel C# → MCP stdio → project_store.py (SQLite) / worker.py → COM IronCAD. Adapter i walidatory są w katalogu Integracja. Parametry i pozycje są sprawdzane przed i po zapisie/ponownym otwarciu. Wynik idzie do revisions/<uuid>, a archiwalny snapshot.ics jest oddzielny od kopii roboczej. SHA256 wykrywa zewnętrzną zmianę archiwum; nie blokuje jej na poziomie systemu plików.

UI: karta projektu, 9 etapów, 6 parametrów, snapshoty, zakres integracji. 14 obszarów: 3 połączone, 1 częściowy, 10 bez backendu. Statusy etapów są ręczne; brak automatycznych bramek agentowych. Działa tylko znany szkielet 10 płyt i identyfikatory z manifestu, nie dowolna skrzynia WoodLAB. Nie ma jeszcze importu maili, archiwum firmy, Excela, doboru okuć, nestingu ani rysunków produkcyjnych. Ich widoki są jawnie opisanymi makietami.

## Testy
Z katalogu paczki, po instalacji środowiska:

```powershell
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\mcp -p test_*.py -v
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\qa -p test_acceptance.py -v
```

Pełny zestaw offline: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -IronCADYear 2023`. Nie wymaga uruchomionego CAD i nie potwierdza CAD. Test natywny wykonaj punktami 4–6. U autora potwierdzono zmianę z UI 964→984 mm i trzy snapshoty. Raporty QA w paczce są historycznym dowodem z jego komputera, a nie wynikiem uruchomienia u Kuby; skrypty audytu live mogą wskazywać jego lokalne ścieżki. Nie traktuj ich jako przenośnych testów instalacji.

## Kolejne kroki
1. Powtórzyć instalację i native smoke test u Kuby; zapisać wersje i wynik. 10.11.2026: IronCAD 2023 (25.0.0.18479, trial) — COM, natywne wiązanie parametru, zapis/otwarcie oraz rejestr Studio → Phoenix PASS na części diagnostycznej; panel dodatku i rodziny skrzyń NOT RUN.
2. Zastąpić sztywne ścieżki SDK konfiguracją i dodać preflight środowiska.
3. Oddzielić konfigurację rodziny skrzyń od aktualnego manifestu demonstracji; mapowanie geometrii musi mieć zatwierdzenie konstruktora.
4. Rozwinąć model danych, migracje SQLite i import archiwum. Excel jako eksport/import, nie drugi niezależny magazyn prawdy.
5. Dopiero następnie dodać reguły okuć, walidacje etapów i agentowe planowanie ze zgodą konstruktora.

Bieżącą instrukcją instalacji jest ten plik. Historyczne raporty zależne od komputera autora nie są dołączone do repozytorium.

