# RockPro CAD — kontrakt developerski

## Źródło i środowisko

Źródłem kodu jest checkout `rockpro-cad`. Sąsiedni `../Integracja/rockpro_cad` to lokalne wdrożenie autora, z własnym venv, bazą, manifestem i rewizjami. Zmiany wdrożeniowe należy najpierw zachować w Git; baz i konfiguracji nie kopiujemy między checkoutami. Nowa kompilacja nie przeładowuje DLL w otwartym IronCAD.

Windows x64, IronCAD 2027 / 29.0 i lokalny ICAPI SDK. C# używa kompilatora .NET Framework z Build.ps1 oraz WinForms, System.Drawing, System.Web.Extensions i interop dostawcy. Nie stosujemy automatycznie zaleceń C# 14/ASP.NET. Python u autora: 3.14.3; backend bez CAD używa stdlib, operacje natywne comtypes i przypiętego python-ironcad z requirements.txt. Inne wersje hosta wymagają osobnej próby.

## Granice modułów

| Obszar | Pliki | Kontrakt |
| --- | --- | --- |
| Rejestracja | addin/RockProAddin.cs, Install-User.ps1 | Stały GUID/ProgID, per-user HKCU; osobny test autostartu |
| Interfejs | addin/RockProPanel.cs, LayoutForm.cs | UI → MCP stdio; aktualizacje na wątku formularza |
| Protokół | mcp/server.py, worker.py | Jawne narzędzia i argumenty; stdout JSON; brak arbitrary exec |
| Dane | mcp/project_store.py, layout.py | Jedna SQLite, karta i układ projektu; statusy ręczne |
| Obliczenia | mcp/layout.py | mm; obrysy, przegrody, komora; minimum objętości 18 wariantów |
| CAD | worker.py, Integracja/ironcad_adapter.py | Znany szkielet, sześć RP_*, zmiany wyłącznie na kopii |
| Walidacja | Integracja/review_skeleton*.py | Pomiary geometrii po zmianie i ponownym otwarciu |

Ścieżki addin/ i mcp/ powyżej są względem Integracja/rockpro_cad. Bieżące narzędzia MCP odczytuj przez tools/list, nie z liczby wpisanej w starym raporcie. Aktualny zakres i ograniczenia modelu są w LAYOUT.md. Kontrakt sceny zawiera RP_Length, RP_Depth, RP_BaseHeight, RP_LidHeight, RP_Thickness, RP_DisplayGap. Wartości narzędzi są w mm, wartości natywnego API przeliczamy na metry, gdy API tego wymaga.

## Instrukcje, prompty i skille

- AGENTS.md: krótkie reguły repozytorium i routing skilli.
- .github/copilot-instructions.md: wejście dla Copilota; .github/instructions/*.instructions.md: reguły z applyTo dla właściwych plików.
- .github/prompts/*.prompt.md: jawnie uruchamiane zadania. W obsługującym je edytorze wybierz prompt; w innym kliencie załącz plik lub wklej jego treść.
- .agents/skills/rockpro-scope-check: ocena zakresu i konkretny prompt powrotu do jakości.
- .agents/skills/rockpro-verification: dobór dowodów i komend.
- .agents/skills/bug-reproduction-brief: pobrany upstream, tylko do zleconego briefu diagnostycznego. Pełna naprawa nie kończy się na briefie.

Skille są repozytoryjne: otwieraj Codex w katalogu checkoutu. Przy pracy z katalogu nadrzędnego odczytuj je bezpośrednio według AGENTS.md workspace. Instalacja nie dodaje działającego w tle agenta do IronCAD i nie gwarantuje, że model zawsze rozpozna problem; wykonawcze sprawdzenia zapewnia harness.

## Sprawdzanie

Po zwykłym Setup.ps1:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -WithAddinBuild -WithUiChecks
```

Jeśli checkout nie ma venv, podaj istniejący Python bez uruchamiania instalatora:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\Verify.ps1 -Python '..\Integracja\.venv\Scripts\python.exe' -WithAddinBuild -WithUiChecks
```

Harness nie rejestruje dodatku, nie uruchamia CAD i nie zmienia modeli. Uruchamia unittest MCP/SQLite/układu i QA, audyt struktury, a opcjonalnie kompilację DLL i C# LayoutUiChecks. Ostatnia opcja tworzy chwilowy formularz testowy poza IronCAD. Raporty trafiają do ignorowanego artifacts/verification/. Nie utrzymujemy sztywnej liczby testów jako kryterium; liczy się powodzenie odkrytego zestawu.

Test natywny wykonuje jeden aktor: zapisane dane użytkownika → znany plik źródłowy → odczyt → zmiana na kopii → pomiar → zapis i ponowne otwarcie → kontrola niezmienności oryginału, historii i SQLite. Nie wykonuj live_test.py --change jako zwykłego testu: zmienia kopię i otwiera dokumenty hosta. UI, autostart oraz geometrię raportuj oddzielnie od testów bez CAD.

## Utrzymanie i wydanie

Nie mieszaj dużego refaktoru i nowych możliwości bez rozdzielenia rezultatów i dowodów. Nie przeformatowuj całego MVP przy drobnym fixie. Przy powtarzającym się problemie najpierw odtwórz objaw i napraw przyczynę, potem wróć do funkcji. Konkretna forma checkpointu jest w skillu scope-check.

Instrukcje procesu nie zastępują jawnego zlecenia użytkownika. Nie wymagamy dodatkowej zgody na odwracalne, autoryzowane zmiany. Przy publikacji, zmianie środowiska lub danych stosuj rzeczywiste uprawnienia zadania. Kopie binarne wdrażaj dopiero po testach, z zachowaniem poprzedniej wersji i zamkniętym hostem. Samo opublikowanie kodu na Git nie dowodzi instalacji u Kuby.

Zmiany instrukcji aktualizuj razem z kontraktem, który zmieniają. Źródła zewnętrzne i decyzje adopcji: docs/AI_SOURCES.md. Stan audytu i pozostałe braki: docs/REPOSITORY_AUDIT.md.

Kontrakt wersjonowania układu, konfliktów i powiązania CAD: [LAYOUT_VERSIONING.md](LAYOUT_VERSIONING.md). UI i AI muszą przekazywać odczytane expected_revision; nie ponawiać konfliktu z automatycznie odświeżonym tokenem.

Karta projektu i każdy etap mają niezależne rewizje. Kontrakt aktualizacji,
historii i odbioru: [PROJECT_CONCURRENCY.md](PROJECT_CONCURRENCY.md).
