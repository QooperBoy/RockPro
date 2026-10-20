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
