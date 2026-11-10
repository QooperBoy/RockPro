# Narzędzia z nadrzędnego workspace

Kod uzupełniono 09.11.2026. `narzedzia/` zachowuje osiem skryptów importu,
audytu, mapowania folderów, instalacji i przygotowania archiwów. To źródła
narzędzi używanych przy transferze, nie kolejny backend Studio.

Większość skryptów wyznacza workspace z położenia własnego pliku. Aby zachować
oryginalną semantykę, umieść kopię katalogu `narzedzia` bezpośrednio pod nowym
workspace, obok `Transfer_RockPro_20261024`, `projekty`, `raporty` i `outputs`.
Nie uruchamiaj pakowania ani instalatora z tego podfolderu klona. Historyczne
ścieżki do worktree, daty i nazwy paczek wymagają dostosowania i sprawdzenia.
Źródła z lokalnego workspace pozostały nietknięte.

`Install-RockPro.ps1` to zachowany wrapper instalacji konkretnego stanowiska.
Dla nowej instalacji korzystaj z aktualnego `Setup.ps1` i instrukcji
[Kuby](../../docs/KUBA_HANDOVER.md), nie z historycznych domyślnych ustawień.

[CODE_INVENTORY.json](CODE_INVENTORY.json) zapisuje pochodzenie i SHA kodu
dołączonego w tym uzupełnieniu. Identyczne wersje już obecne w głównym kodzie
pominięto. Archiwalne źródła z wdrożenia i diagnostyki znajdują się w
[legacy/local-code](../../legacy/local-code/README.md).
