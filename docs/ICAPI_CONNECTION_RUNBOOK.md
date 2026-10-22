# ICAPI — diagnoza połączenia i kontynuowanie pracy

Przeznaczenie: dla programisty i kolejnego agenta, gdy otwarty IronCAD nie
udostępnia interfejsu. To zapis obserwacji z 22.10.2026, a nie instrukcja
ponawiania całego audytu przed każdym montażem.

## Krótka ścieżka

1. Sprawdź istniejący proces i połączenie z dokładnym zapisanym dokumentem.
   Narzędzie uruchomione w izolacji może nie widzieć procesu pulpitu. Potwierdź
   stan poza izolacją, zanim napiszesz użytkownikowi, że IronCAD jest zamknięty.
   Wyjście poza izolację nie oznacza uruchomienia jako administrator.
2. Wykonaj jeden odczyt `IZBaseApp` i tożsamości dokumentu. Korzystaj z istniejącego
   ROT; nie aktywuj dokumentu i nie otwieraj widocznej sceny jako obejścia.
3. Rozdziel: brak procesu, brak otwartego dokumentu, brak interfejsu COM oraz
   błąd geometrii/schematu. `E_NOINTERFACE` nie dowodzi braku uruchomionego CAD.
4. Jeśli połączenie działa, przejdź do zleconego montażu. Nie powtarzaj
   diagnostyki rejestru, DLL ani BRep bez konkretnego nowego błędu.
5. Jeśli połączenie nie działa, zapisz kod HRESULT i krótki raport. Naprawiaj
   konkretną rozbieżność, z kopią stanu i możliwością wycofania. Nie uruchamiaj
   w pętli instalatora, rejestracji DLL ani kolejnych instancji programu.

## Co faktycznie sprawdzono

- Istniejący moniker dokumentu, globalny `IronCAD.Application` i fabryka COM
  nie są tym samym krokiem. W tym incydencie odczyty istniejącej aplikacji
  wskazywały ten sam rzeczywisty PID, więc nie był to osierocony moniker.
- Python i oficjalny interop C# miały ten sam IID `IZBaseApp` i zwracały
  `E_NOINTERFACE`. Odczyt `IDispatch.GetTypeInfo` zwracał
  `TYPE_E_LIBNOTREGISTERED`. Samo przepisanie adaptera z Pythona na C# nie pomogło.
- Sześć bibliotek SDK 29.0 ładowało się przez `LoadRegTypeLib`. Klient i host
  działały jako ten sam użytkownik, z tokenem Medium. Załadowane DLL pochodziły
  z instalacji 2027 i miały architekturę x64.
- Jednorazowe ponowienie standardowej rejestracji dla użytkownika nie zmieniło
  żadnego klucza w porównaniu kopii przed/po. Nie było uzasadnienia, aby je
  ponawiać.
- Symbole i struktury ATL w komponentach Base/App/Core/Drawing zawierały
  wymaganie metadanych 12.0, podczas gdy zasoby TYPELIB miały wersję 29.0.
  Dla dwóch interfejsów sprawdzono również wyłącznie te konkretne struktury
  w pamięci hosta; wartości nadal wynosiły 12.0. To potwierdzona rozbieżność,
  ale nie dowód, że sama wyjaśnia wszystkie błędy połączenia.
- Zwykły alias wpisu 12.0 do pliku 29.0 nie wystarczył. Oddzielne eksperymentalne
  kopie metadanych 12.0 ładowały się w kliencie, lecz nie naprawiły odczytu
  interfejsu w działającym hoście. Nie wolno opisywać tego jako potwierdzonej
  naprawy API.
- Start serwera `/Automation` zatrzymywał się na potwierdzeniu wersji testowej,
  a bez potwierdzenia kończył przekroczeniem czasu. Ten gate wymaga działania
  użytkownika; nie obchodzimy go przez sterowanie oknem.

Odczyt przez udokumentowany AddOn wewnątrz hosta zakończył się pozytywnie:
`IZBaseApp` i `ApiVersion` zwróciły `PASS`, wersja `29.0.2.20605`.
Raport lokalny: `artifacts/latch17251-inprocess-probe-20261022-04/inprocess_probe.json`.
PID aplikacji i procesu DLL był zgodny; okno na pierwszym planie, zapisany
kontekst i SHA oryginału pozostały bez zmian. Jednocześnie `LoadRegTypeLib(12)`
wewnątrz hosta nadal nie działał. Sam odczyt wewnętrzny nie dowodzi więc naprawy
zewnętrznego COM ani poprawności eksperymentalnych metadanych zgodności.

Ten raport potwierdza tylko getter. Nie potwierdza montażu zatrzasków,
połączenia MCP ani zakończenia sprzątania tymczasowego AddOn; dla tych operacji
potrzebne są osobne końcowe wyniki. Zmienna `own_temporary_addon_removed=true`
z pierwszego wrappera nie jest wystarczającym dowodem: liczba dodatków po
wywołaniu nie spadła. Należy sprawdzić dokładną tożsamość własnego UUID,
nie usuwać nieznanego wpisu na podstawie samego indeksu.

Kolejna próba opublikowała ten interfejs pod prywatnym identyfikatorem ROT
wyłącznie na czas sesji. Publikacja wewnątrz hosta zadziałała, ale jawne pobranie
`IZBaseApp` przez klienta nadal zwracało `E_NOINTERFACE`. To nie jest działający
most Python–CAD. Uchwyt rejestracji ROT trzeba wycofać w procesie właściciela;
wywołanie `RevokeActiveObject` z klienta zwróciło `E_INVALIDARG`.
Nie należy obchodzić tej granicy przez podmianę wskaźników w pamięci ATL.

## Własna kopia źródła w POC

Wykonawca CLR wewnątrz hosta potwierdził działanie API i ukrytego otwarcia
własnej kopii. Kolejne próby wykazały dwie pułapki:

- CLR może zachować pierwszą słabo podpisaną bibliotekę o danej nazwie.
  Sama zmiana `AssemblyVersion` nie wystarczyła. Roboczy loader przypina nazwę
  pliku/assembly do SHA źródła; nie podmienia biblioteki już działającej w pamięci.
- `IsReadOnly()` zwracał `false` mimo argumentu `OpenFile2(..., true, false)`.
  Próba wymuszenia atrybutu Windows ReadOnly na własnej kopii zmieniła foreground
  podczas otwierania. Guard przerwał operację i zamknięto własną kopię. Tej
  próby nie wolno zaliczać jako działania bez zmiany fokusu.

Dla ograniczonego POC przyjęto jawny tryb **owned getter-only clone**: nowa
byte-identyczna kopia w katalogu operacji, zgodny SHA/GUID, `Modified=false`
przed i po, wyłącznie gettery oraz eksport całych okuć do nowych plików.
Kopia źródła nie jest zapisywana; oryginał nie jest otwierany przez wykonawcę.
Nie jest to dowód działania trybu read-only SDK. Zmiana stanu, hasha lub
foreground nadal zatrzymuje próbę. Własność dokumentu i zamknięcie w `finally`
pozostają wymagane także po błędzie.

## Końcowy wynik POC zatrzasków

`artifacts/latch17251-inprocess-native-20261022-09/acceptance.json`: **PASS**.
Wykonawca wewnątrz hosta odczytał i wyeksportował cztery rzeczywiste zespoły,
zmontował A 914×602×352 i B 1100×720×410 mm, a następnie zapisał i ponownie
otworzył oba ICS. Pomiary całych okuć, orientacje i symetria są zgodne.
Obie fazy mają `remaining_owned=0`; kontekst, foreground i SHA oryginału
pozostały bez zmian. Niezależny przegląd porównał zapisane raporty i hashe.

Modele zawierają 10 płyt zastępczych, 8 rzeczywistych narożników i 4 całe
zespoły połówek zatrzasków. Nie są pełnym Epsonem. To regenerowane A/B,
bez trwałych natywnych wiązań; wygląd pozostaje do oceny przez użytkownika.
Zewnętrzny COM nie został naprawiony, a stały transport MCP do tego wykonawcy
nie został jeszcze wdrożony. Odbiór POC nie oznacza wdrożenia tego mechanizmu
w panelu produkcyjnym.

Próba `08` po ręcznym zamknięciu komunikatu zakończyła się błędem guardu
foreground, zamknęła swoją kopię i nie uruchomiła A/B. Cztery własne wpisy
eksperymentalnych metadanych `compat-04` wycofano z wynikiem **PASS**.
Nieznany wpis AddOn pozostawiono; dokładny stan własnego tymczasowego wpisu
i sesyjnej publikacji ROT należy zachować w końcowym raporcie aktora natywnego.

## Narzędzia i granice naprawy

- `addin/Repair-IcApi.py` rejestruje metadane dla bieżącego użytkownika.
  Wczytanie typu używa `REGKIND_NONE`, aby samo czytanie nie próbowało rejestracji
  systemowej. Nie jest to uniwersalna odpowiedź na każdy błąd połączenia.
- `addin/Repair-IcApi-Compat.py` jest eksperymentem dla konkretnych hashy SDK.
  Nie jest częścią automatycznej instalacji. Nie zmienia zainstalowanych DLL,
  istniejących interfejsów 29.0 ani HKLM. Nie uruchamiaj go bez sprawdzenia
  najnowszego raportu i stanu wycofania wcześniejszej próby.
- Kopie metadanych, modele, pełne kopie rejestru i logi pozostają w ignorowanym
  `artifacts/`; nie publikuj ich z kodem. Wycofanie wpisów musi sprawdzać, czy
  nie nastąpiła cudza równoległa zmiana.
- `OaEnablePerUserTLibRegistration` według dokumentacji Microsoft zmienia
  zachowanie **rejestracji** przez `RegisterTypeLib`; nie jest udokumentowanym
  przełącznikiem naprawiającym odczyt `LoadRegTypeLib`.

Ścieżki `addin/` powyżej są względem `Integracja/rockpro_cad/`.

## Minimalny log dla przyszłego agenta

Zapisuj fakty operacyjne, nie wewnętrzny tok rozumowania modelu:

- identyfikator przebiegu, czas, wersję kodu i SDK;
- rozpoznane źródło, jego SHA, GUID i stan modyfikacji;
- etap i konkretne wywołanie, wynik HRESULT, `PASS` / `FAIL` / `NOT RUN`;
- własne otwarte dokumenty oraz zamknięcia i zachowane kopie;
- zakres i wynik zmiany konfiguracji, dokładny plik wycofania;
- modele wynikowe, ich hashe, wynik zapisu/otwarcia i zakres nieobjęty próbą.

Jedna próba montażu powinna kończyć się jednym czytelnym podsumowaniem.
Sukces planera lub kompilacji nie może zastępować natywnego odbioru modelu.

## Źródła

- [Oficjalny pakiet Python IronCAD](https://github.com/IronCAD/python-ironcad)
- [Microsoft: LoadRegTypeLib](https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-loadregtypelib)
- [Microsoft: OaEnablePerUserTLibRegistration](https://learn.microsoft.com/en-us/windows/win32/api/oleauto/nf-oleauto-oaenableperusertlibregistration)
- Lokalny przykład producenta: `ICAPI/Samples/C#/StartIronCAD/Form1.cs`.

## Prompt powrotu do zadania

„Wróć do połączenia ICAPI według tego runbooka i najnowszego raportu. Użyj
$rockpro-scope-check oraz $rockpro-verification. Nie powtarzaj nieskutecznych
prób rejestracji ani startów Trial. Potwierdź działający odczyt API, wykonaj
gotowy runner zatrzasków A/B na kopiach i zamknij swoje dokumenty. Zachowaj
oryginał, symetrię grup oraz ograniczenie pracy bez przejmowania pulpitu.”
