# Zadanie: wspólny rejestr rodzin części i zgodność CAD / obserwator / 3D

Status: specyfikacja do realizacji, 2026-10-24. Nie jest wdrożeniem.
Linear: zapis przez konektor niedostępny — ROC-42 i ROC-44 nie zostały odnalezione.

## Problem i rezultat

Generator, dziennik i viewer klasyfikują części osobno. Dodanie rodziny wymaga
ręcznych zmian w kilku miejscach. Podgląd jest eksportem, nie synchronizacją live.
Obecnie górne gniazda pod koła (stacking cups, socket) trafiają do narożników.
Użytkownik wymaga ich powiązania z kołami w etapie 06.

Rezultat: pojedyncza definicja rodziny steruje nazwą, kolorem i warstwą we wszystkich
odbiorcach. Generator nadal wymaga jawnej implementacji oraz walidacji dla danej
rodziny. Rejestr nie generuje automatycznie obsługi dowolnego okucia.

## Kolejność warstw konstrukcyjnych

1. Sklejka.
2. Profile aluminiowe.
3. Narożniki i wzmocnienia — bez górnych gniazd pod koła.
4. Zamki i zawiasy.
5. Uchwyty.
6. Koła i gniazda do piętrowania — wspólna warstwa, kolor i moment odsłonięcia.

Numeracja dotyczy warstw konstrukcji. Przygotowanie źródła, walidacja i zapis
pozostają osobnymi fazami procesu. Nie wymuszać tej kolejności na wykonawcy CAD,
jeżeli zależności montażowe wymagają innej kolejności; dziennik zachowuje faktyczne czasy.

## Zakres i kolejność realizacji

1. Kontrakt rejestru: family_id, stage_id, nazwa PL, kolor, kolejność prezentacji,
   wykonawca, walidatory, schema_version. Rodzina fizyczna i etap prezentacji są
   odrębne: wheels i stacking_sockets należą do etapu running_gear.
2. Przenieść klasyfikację z process_observer.py, prepare_layer_viewer.py i app.js
   do wspólnego rejestru. Eksport zawiera jego wersję i potrzebne metadane UI.
   Identyfikacja przez rolę/ID z manifestu; dopasowanie nazw wyłącznie jako jawna
   migracja znanego eksportu. Nie klasyfikować każdego nieznanego socket automatycznie.
3. Powiązać gniazda z układem kół: wspólny identyfikator interfejsu piętrowania,
   pary wheel_occurrence_id / socket_occurrence_id i rozstaw XY. Gniazda na pokrywie
   skrzyni dolnej przyjmują koła skrzyni górnej w zadanej orientacji piętrowania.
   Dla jednakowych skrzyń korzystać z tego samego wzorca rozstawu. Różne rozmiary
   lub orientacje wymagają jawnego wariantu kompatybilności, nie domysłu.
   Zmiana gabarytu/rozstawu przelicza obie strony interfejsu; gotowych okuć nie skalować.
   Wyłączenie kół nie może pozostawić niezamierzonego kompletu gniazd. Niezależne
   gniazda dopuszczać tylko jako jawny wariant konstruktora, oznaczony w UI.
4. Wspólna tożsamość: project_id, revision_id, operation_id, occurrence_id,
   registry_version oraz hash źródła/eksportu. Zdarzenie utworzenia części odnosi
   się do tej samej części w CAD, raporcie i viewerze; zachować mapę siatek potomnych.
5. Odświeżanie: po udanej generacji i zapisaniu zweryfikowanej rewizji przygotować
   nowy eksport, sprawdzić integralność i atomowo podmienić pakiet podglądu.
   Nie podmieniać plików model.json i geometry.bin niezależnie w trakcie odczytu.
   Błąd eksportu pozostawia poprzedni widok oznaczony jako nieaktualny.
   Obcy trace nie animuje modelu jako historycznego przebiegu. Live mesh streaming
   z każdej operacji SDK poza pierwszym zakresem; aktualizacja po rewizji wystarcza.
6. Testy i odbiór: rejestr i grupowanie offline, potem montaż/zmiana wymiarów na
   nowej kopii ICS, zapis/otwarcie, eksport i kontrola obu widoków.

## Kryteria akceptacji

- Dodanie obsługiwanej rodziny do rejestru ujawnia ją w dzienniku i viewerze bez
  osobnego dopisywania etykiet i palet w każdym interfejsie.
- Gniazda nie pojawiają się w etapie 03; włączenie/wyłączenie etapu 06 obejmuje
  koła i gniazda. Obie rodziny można nadal odróżnić w szczegółach i BOM.
- Zmiana długości, głębokości i rozstawu zachowuje zgodność par przy piętrowaniu;
  test uwzględnia transformację skrzyni górnej oraz obrys koła i gniazda.
- Wykrywane są brakujące/parowane wielokrotnie gniazda, niezgodny rozstaw i kolizje
  z okuciami pokrywy. Nieznany wariant nie otrzymuje automatycznego statusu OK.
- Viewer, trace i CAD wskazują jedną rewizję albo jawnie pokazują niezgodność.
- Błąd eksportu, brak siatki i nieznana rodzina mają czytelny komunikat.
- Czasy nadrzędne i podrzędne nie są sumowane podwójnie. Kolor nie zastępuje statusu.
- Oryginalne ICS i historyczne raporty pozostają bez zmian.

## Poza zakresem

Nowe modele okuć, automatyczna aprobata nośności piętrowania, animacja otwierania
na zawiasach oraz streamowanie siatek w trakcie każdego wywołania COM.
Geometryczna zgodność gniazd i kół nie jest potwierdzeniem nośności konstrukcji.
