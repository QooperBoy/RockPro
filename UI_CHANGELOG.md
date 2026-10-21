# UI 0.3 — zmiany i weryfikacja

- Ciemna nawigacja, spokojne jasnoszare tło, logo RockPro, pomarańczowe akcenty.
- Własny zaokrąglony przycisk WinForms: hover, focus klawiatury, stan disabled.
- Karty ścieżek: nazwa pliku, tooltip pełnej lokalizacji, przycisk Kopiuj, menu PPM: pełna ścieżka / nazwa / katalog.
- Menu kopiowania w karcie projektu, na wierszach historii oraz szczegółach snapshotu.
- Tabela: spokojne zaznaczenie, naprzemienne tło, odstępy, skrócone daty i nazwy plików.
- Szczegóły: kopiowanie ścieżki i całego raportu.

Kompilacja końcowej DLL: OK. Testy backendu 13/13 i odbiorcze 7/7: OK.
Oględziny rzeczywistego formularza Preview z tym samym kodem oraz rzeczywistym MCP/SQLite: karta projektu, snapshoty, tabela historii, menu PPM i potwierdzenie kopiowania: OK. Końcowe formatowanie dat sprawdzone kompilacją, bez ponownego uruchomienia UI.
Nie wykonano ponownego testu CAD ani restartu hosta: IronCAD ma niezapisany dokument. Nowy build zarejestrowano do następnego uruchomienia; obecna sesja IronCAD nadal ma poprzednią DLL. Podgląd działa osobno i nie umożliwia przypisania aktywnego dokumentu hosta.

## UI 0.4.1 — konfigurator wyposażenia

- Kółko myszy nad liczbami i zamkniętymi listami przewija formularz, nie zmienia wartości. Przyciski strzałek i wpisywanie nadal działają.
- Widok 3D korzysta z bufora głębokości na piksel zamiast sortowania całych ścian. Rozwiązuje błędne zasłanianie akcesoriów przez długą przegrodę.
- Podgląd wymiarów: tabela wnętrze / gabaryt sklejki × X / Y / Z, jednostki mm, regularna czcionka Segoe UI 9.
- Legenda, definicje wymiarów i ograniczenia są pod ikoną informacji w prawym górnym rogu podglądu. Hover pokazuje podpowiedź, kliknięcie otwiera pełny tekst. Postęp, błędy i krótki wynik kontroli pozostają widoczne.
- Regresje C#: qa/LayoutUiChecks.cs — kolejność rysowania nie zmienia widoczności bliższego akcesorium, kółko nie zmienia liczby i orientacji oraz przesuwa formularz. Testy backendu przed zmianą: 19/19 i QA 7/7.

Weryfikacja natywna 21.10.2026: wczytano ustawienia ze zgłoszenia (339,4 × 238,9 × 88,2; 1 szt.; orientacja YZX). Akcesorium ma poprawne zasłanianie w 3D; tabela ma osobne kolumny X/Y/Z i dwa wiersze. Kółko nad polem liczby: X 339,40 bez zmiany, przewijanie 0→22; nad listą: Y/Z/X bez zmiany, przewijanie 22→44. Dialog informacji działa. Brak zmian geometrii CAD w tej poprawce.


## UI 0.4.2 — ranking objętości

Listy orientacji i kierunku sortowane rosnąco po objętości, zielony–pomarańczowy–czerwony, litry i oznaczenia min/max. Pod tabelą bieżąca objętość i minimum 18 kombinacji; przycisk stosujący najlepszą parę. Wybrany klucz jest zachowany po sortowaniu. Testy: 22 backend + 7 QA, regresja C# zachowania klucza po zmianie kolejności. Próba natywna: 4 urządzenia, orientacja ZYX / kierunek Z → XYZ / Z; 65,2 l → 58,7 l; odświeżenie rankingu i podglądu poprawne.
