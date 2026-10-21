# Ładowanie RockPro CAD przy starcie IronCAD 2027

Dodatek jest ładowany do procesu IronCAD jako zarządzana klasa COM. Nie wymaga otwierania CMD. Przycisk jest tworzony w środowisku sceny 3D: **Dodatki → RockPro CAD**. Sam panel otwiera się po kliknięciu; automatyczne ładowanie dodatku nie oznacza automatycznego otwierania jego okna ani uruchomienia agenta AI.

Instalacja: zamknąć IronCAD po zapisaniu dokumentów, uruchomić Setup.ps1 -InstallAddin ze stałego folderu projektu. Instalator rejestruje natywne metadane COM/typelib ICAPI dla użytkownika, klasę .NET RockPro, kategorie dodatku, deklarację zgodności hosta oraz LoadOnStartup=1 i ShowInList=1 dla IronCAD 29.0. Lokalizacja źródeł/DLL musi pozostać stała. Rejestracja ma zasięg bieżącego użytkownika; nie wymaga kopiowania DLL do katalogu Program Files.

Diagnostyka 2026-10-21: klasa RockPro aktywowała się przez COM, lecz przycisku nie było w menedżerze i brakowało dzisiejszego InitSelf w logu. Natywne API zwracało Library not registered / No such interface supported. Naprawiono metadane dostarczonych bibliotek ICAPI w HKCU, uzupełniono zgodność hosta i ponowiono rejestrację dodatku. Po pełnym restarcie hosta log zawierał 2026-10-21T12:10:31 InitSelf OK; ribbon command registered. Połączenie IZBaseApp 29.0 zadziałało; przycisk Dodatki → RockPro CAD był widoczny i otworzył panel 0.3. Zmiany wykonano razem, więc nie przypisujemy sukcesu wyłącznie deklaracji zgodności wersji.

Log: Integracja/rockpro_cad/logs/addin.log. Sam wynik instalatora nie potwierdza startu hosta: wymagane jest InitSelf po czasie uruchomienia procesu oraz test przycisku. Po aktualizacji DLL lub naprawie rejestracji należy ponownie uruchomić IronCAD. Aktualna wersja jest zweryfikowana dla 2027/29.0; kolejne wersje wymagają ponownego testu.
