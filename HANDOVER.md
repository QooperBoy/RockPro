# RockPro CAD — przekazanie dla Jakuba Siwca

Aktualizacja 0.4: konfigurator urządzeń i układu opisuje [LAYOUT.md](LAYOUT.md). MCP udostępnia obecnie 11 narzędzi, testy backendu obejmują 22 przypadki plus 7 QA. Poniżej zachowano opis bazowej wersji 0.3; zakres nowego modułu i ograniczenia eksportu mają opis w LAYOUT.md.

## Co dostajesz
Scalone źródła frontendu WinForms, backendu MCP stdio i lokalnej bazy SQLite, adapter COM, walidatory oraz demonstracyjny szkielet ICS (10 płyt). Repozytorium rozpoczyna wspólną historię zmian na podstawie wydania MVP 0.3. Nie zawiera środowiska autora, bazy klientów, korespondencji, oryginalnych projektów produkcyjnych ani bibliotek DLL dostawcy. Baza projektów zostanie utworzona lokalnie od zera.

## Wymagania
- Windows x64, IronCAD 2027 / 29.0 i lokalne ICAPI SDK. Innych wersji nie zweryfikowano.
- Python x64 (u autora 3.14.3), Git i dostęp do internetu podczas instalacji zależności.
- .NET Framework 4.x z kompilatorem `C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe`.
- Build.ps1 oczekuje `C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll` i `C:\Program Files (x86)\Microsoft.NET\Primary Interop Assemblies\stdole.dll`. Przy innym układzie dostosuj ścieżki w Build.ps1.
- IronCAD i backend uruchamiaj jako ten sam użytkownik w tej samej sesji Windows, z takim samym poziomem uprawnień.

## Instalacja
1. Rozpakuj cały katalog do stałej lokalizacji, np. `C:\Dev\RockPro_CAD_MVP_0.3_Kuba`. Zachowaj strukturę `Integracja` i jej podkatalogi.
2. Zapisz dokumenty i zamknij IronCAD przed instalacją/rejestracją nowej DLL.
3. W PowerShell w katalogu paczki uruchom:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Setup.ps1 -Python python -InstallAddin
```

`-Python` może być pełną ścieżką do python.exe. Skrypt tworzy venv, instaluje przypięte zależności, ustawia lokalne ścieżki demonstracji, kompiluje dodatek i rejestruje go wyłącznie w HKCU. Bez `-InstallAddin` nie rejestruje dodatku. Nie zmieniaj potem położenia folderu bez ponownego configure.py i rejestracji. Nie uruchamiaj instalatora na komputerze autora: zastąpiłby jego rejestrację tym wydaniem.

4. Otwórz IronCAD i `Integracja\skeleton\demo\RockPro_Epson_szkielet_MVP.ics`.
5. Dodatki → RockPro CAD → Połącz / Odśwież. Utwórz kartę projektu i przypisz otwarty, zapisany plik demonstracyjny.
6. Odczytaj parametry. Zmień np. RP_Length o 20 mm i zastosuj na kopii. Sprawdź nowy plik ICS, raport i historię snapshotów. Nie testuj na produkcyjnej skrzyni.

Jeżeli nie ma przycisku: sprawdź SDK, wynik kompilacji, rejestrację HKCU i restart IronCAD. Jeśli COM nie widzi dokumentu: otwórz wskazany plik, zamknij modalne dialogi i sprawdź zgodność sesji/uprawnień. Nie naprawiaj tego przez wyłączanie walidacji.

## Podłączenie agenta AI
Panel sam uruchamia MCP jako lokalny subprocess stdio, nie potrzebuje klucza AI. `configure.py` generuje `mcp-config.local.json` z absolutnymi ścieżkami dla klienta obsługującego format mcpServers. W Codex/innym kliencie przenieś wartości command i args do formatu jego konfiguracji; nie nadpisuj pozostałych serwerów. Uruchom ponownie klienta i sprawdź tools/list (8 narzędzi). Serwer: `Integracja/rockpro_cad/mcp/server.py`.

Narzędzia: inspect_project, change_dimensions_on_copy, list_projects, save_project, get_project, set_stage, list_snapshots, create_snapshot. Nie ma portu HTTP. Nie dodawaj narzędzia wykonującego dowolny Python/polecenia powłoki.

## Architektura i zakres
Panel C# → MCP stdio → project_store.py (SQLite) / worker.py → COM IronCAD. Adapter i walidatory są w katalogu Integracja. Parametry i pozycje są sprawdzane przed i po zapisie/ponownym otwarciu. Wynik idzie do revisions/<uuid>, a archiwalny snapshot.ics jest oddzielny od kopii roboczej. SHA256 wykrywa zewnętrzną zmianę archiwum; nie blokuje jej na poziomie systemu plików.

UI: karta projektu, 9 etapów, 6 parametrów, snapshoty, zakres integracji. 14 obszarów: 3 połączone, 1 częściowy, 10 bez backendu. Statusy etapów są ręczne; brak automatycznych bramek agentowych. Działa tylko znany szkielet 10 płyt i identyfikatory z manifestu, nie dowolna skrzynia WoodLAB. Nie ma jeszcze importu maili, archiwum firmy, Excela, doboru okuć, nestingu ani rysunków produkcyjnych. Ich widoki są jawnie opisanymi makietami.

## Testy
Z katalogu paczki, po instalacji środowiska:

```powershell
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\mcp -p test_*.py -v
.\Integracja\.venv\Scripts\python.exe -m unittest discover -s .\Integracja\rockpro_cad\qa -p test_acceptance.py -v
```

Oczekiwane 13 + 7 testów. Nie wymagają uruchomionego CAD. Test natywny wykonaj punktami 4–6. U autora potwierdzono zmianę z UI 964→984 mm i trzy snapshoty. Raporty QA w paczce są historycznym dowodem z jego komputera, a nie wynikiem uruchomienia u Kuby; skrypty audytu live mogą wskazywać jego lokalne ścieżki. Nie traktuj ich jako przenośnych testów instalacji.

## Kolejne kroki
1. Powtórzyć instalację i native smoke test u Kuby; zapisać wersje i wynik.
2. Zastąpić sztywne ścieżki SDK konfiguracją i dodać preflight środowiska.
3. Oddzielić konfigurację rodziny skrzyń od aktualnego manifestu demonstracji; mapowanie geometrii musi mieć zatwierdzenie konstruktora.
4. Rozwinąć model danych, migracje SQLite i import archiwum. Excel jako eksport/import, nie drugi niezależny magazyn prawdy.
5. Dopiero następnie dodać reguły okuć, walidacje etapów i agentowe planowanie ze zgodą konstruktora.

Bieżącą instrukcją instalacji jest ten plik. Historyczne raporty zależne od komputera autora nie są dołączone do repozytorium.

