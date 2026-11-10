# ROC-37 — odtworzenie, utrzymanie i własność produktu

Stan 25.10.2026: procedura i lokalna próba odtworzenia gotowe. Właściciele
imienni, koszty umów/licencji i decyzje po pilotażach wymagają ustalenia z RockPro.
Role poniżej są propozycją odpowiedzialności, nie przypisaniem osób bez ich zgody.

## Odtworzenie i aktualizacja

1. Zachować commit, bundle historii, pliki projektowe, konfigurację i spójny backup
   SQLite przez backup API, bez kopiowania aktywnej bazy z pominięciem WAL.
2. Odtwarzać do nowego katalogu, nigdy na bieżący projekt lub zachowane wdrożenie:
   `python scripts/verify_snapshot_restore.py --snapshot <folder> --output <nowy-folder>`.
   Kontrola obejmuje SHA plików, SQLite quick_check i commit w bundle.
3. Baza zachowuje stare ścieżki. Migrować je na kopii z kontrolą wskazanych ICS;
   configure.py nie służy do migracji historii ani zastępowania danych demo.
4. Przygotować zależności według HANDOVER.md/AUTOSTART.md. Uruchomić
   `scripts/Verify.ps1 -WithAddinBuild -WithUiChecks`. Harness sam nie instaluje.
5. CAD/SDK/dodatek aktualizować najpierw na kopii testowej; zachować DLL/rejestrację.
   Rejestrować przy zapisanych dokumentach i zamkniętym hoście. Build nie przeładowuje DLL.
6. Native: źródło → nowa kopia → odczyt/zmiana/pomiar → zapis/otwarcie → kontrola
   oryginału i snapshot/SQLite → rzeczywisty widok. Dopiero potem wdrażać.
7. Rollback: przy zamkniętym hoście przywrócić poprzednią DLL/rejestrację i zgodną
   kopię konfiguracji/bazy. Nie cofać bazy bez uzgodnienia nowych realizacji.

PASS: odtworzono 268 plików nocnego snapshotu z pełną zgodnością SHA, commit
4bd25ec i spójną SQLite. Snapshot pozostał niezmieniony. Dowód:
artifacts/overnight-20261024/restore-exercise/restore_verification.json.
NOT RUN w tej próbie: instalacja/rejestracja, migracja ścieżek i otwarcie CAD.
Aktywny host i jego dokumenty nie były dotykane.

## Odpowiedzialność, ryzyka i koszty

| Obszar | Proponowana rola | Kontrola ryzyka | Koszt |
| --- | --- | --- | --- |
| Rodziny i reguły | konstruktor prowadzący | wersja, źródła, próbki dodatnie/ujemne | czas niezmierzony |
| Części i wycięcia | konstruktor + technolog | SKU, wariant, grubość, rama i tolerancje | brak danych |
| Kod i wydania | utrzymujący dodatek | commit, harness, native, rollback DLL | nieustalony |
| Dane i backup | administrator stanowiska | SQLite/ICS/bundle, próby odtworzenia | retencja/nośnik nieustalone |
| CAD/SDK/WoodLAB | administrator + właściciel licencji | zgodność wersji/modułów, test na kopii | umowy nieznane |
| AI i dane klientów | właściciel produktu + opiekun danych | limity, propozycje bez zgód, uzgodniony zakres danych | koszt/tokeny bez pilotażu niedostępne |
| Magazyn/zakupy | magazynier + zakupy | wydania, dostawy, MOQ, termin i cash limit | brak aktualnych ofert/transportu |

Własność produktu utrzymują zatwierdzane reguły, zamrożone przypadki odbioru,
historia decyzji, widoczne błędy i wersjonowane raporty. AI nie zatwierdza
geometrii, kosztów ani produkcji w imieniu konstruktora.

## Kolejna rodzina i dalszy backlog

Referencja i zatwierdzone dane → stabilne ID/role/kotwy → zakres i braki → próbki
odbioru → reguły → offline → CAD na kopii → zapis/otwarcie → konstruktor → dokumentacja.
Generator, eksport i podgląd korzystają ze wspólnego rejestru rodzin/etapów.

Po pilotażu CAD: standaryzacja części, wycięcia i styki profili ROC-41.
Po pilotażu AI: katalog urządzeń, importer ROC-39 i oznaczony benchmark ROC-24;
decyzja o dalszym zakresie/koszcie ROC-35. Po pilotażu materiałów: prawdziwy
magazyn/oferty, koszt i termin ROC-36, ewentualnie profile 1D. QR/serwis oraz
konfigurator handlowy dopiero na tych samych zatwierdzonych regułach.
