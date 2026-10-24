# Nice to have — otwieranie skrzyni na zawiasach

Status: rozpoznanie dokumentacji i lokalnego SDK, nie wykonana animacja.
Dodano na prośbę użytkownika 24.10.2026. Priorytet opcjonalny, po podstawowym
montażu, ochronie ręcznych zmian i stabilnym zapisie projektu.

## Natywne możliwości IronCAD

SmartMotion potrafi animować całe zespoły. Ruch Spin obraca zespół wokół osi
jego kotwy, a przestawienie kotwy zmienia środek obrotu. Dla skrzyni pozwala
to umieścić oś w osi zawiasów, zamiast obracać wieko wokół jego środka.
Źródło: [Animating an Assembly](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/Animation/Animating_an_Assembly_.htm).

Właściwości ścieżki obejmują Rotation About Anchor i sterowanie czasem,
m.in. łagodne rozpędzanie/hamowanie oraz ruch powrotny.
Źródło: [Animation Path Properties](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/Animation/Animation_Path_Properties_.htm).

Mechanism Mode rozwiązuje więzy podczas ruchu; pozwala oglądać mechanizm
bez trwałej zmiany pozycji projektu i korzystać z kontroli przenikania.
SmartMotion może być odtwarzany również w tym trybie z uwzględnieniem więzów.
Źródło: [Using the Mechanism Mode](https://www.ironcad.com/support/IRONCADDRAFT_Help/Content/3D_Design_Environment/Positioning_Objects/Using_the_Mechanism_Mode.htm).

Dokumentacja internetowa dotyczy wcześniejszych wydań. Mamy IronCAD 2027;
obsługę rzeczywistej sceny i zgodność eksportu trzeba potwierdzić tutaj.

## Zastosowanie do RockPro — propozycja

1. Osobna kopia prezentacyjna z zamkniętej, zapisanej rewizji. Główny model
   parametryczny, ręczne zmiany i raporty pozostają zachowane.
2. Zmierzyć rzeczywistą oś sworzni obu 270836 i sprawdzić współosiowość.
   Nie zastępować tego środkiem obrysu ani zakładać, że korzeń importu jest osią.
3. Zdefiniować ruchomy zbiór: pięć płyt wieka, profile górne i pokrywy,
   górna część złącza, narożniki/wzmocnienia wieka, gniazda, górne połówki
   zawiasów oraz właściwe części zamków. Korpus, dolne zawiasy, koła i boczne
   uchwyty do podnoszenia pozostają nieruchome.
4. Zamki muszą być zwolnione albo pokazane w osobnym uproszczonym kroku.
   Nie przedstawiać przenikania zamkniętych zamków jako poprawnego otwierania.
5. Utworzyć ruchomy zespół POKRYWA_animacja, kotwę i oś w zmierzonej osi
   zawiasów; dodać SmartMotion 0° → 90° → 0°. Kąt i czas są konfiguracją;
   90° jest początkową propozycją prezentacyjną, nie potwierdzonym ogranicznikiem.
6. Sprawdzić kilka pozycji pośrednich, brak odklejenia górnych połówek od osi,
   ruch wyposażenia razem z pokrywą i niezmienność korpusu. Powrót do 0° musi
   odtworzyć stan zamknięty; kontrola po ponownym otwarciu ICS.
7. Docelowo dodać więzy zawiasowe i Mechanism Mode, aby ruch respektował
   mechanizm, oraz zweryfikować dostępny eksport filmu na tej instalacji.

Pierwszy POC może zamrozić lokalne pozycje na kopii prezentacyjnej i animować
jeden zespół. Nie wolno bez sprawdzenia przegrupować modelu roboczego:
obecne wyrażenia Parent\Params zależą od głębokości hierarchii. Pełna wersja
musi poprawnie przepiąć te odniesienia albo generować prezentację ponownie
z aktualnej rewizji po zmianie gabarytu. RP_DisplayGap pozostaje rozsunięciem
prezentacji i nie jest kątem otwarcia.

## Lokalny SDK

W zainstalowanej bibliotece ICAPI 29.0 istnieje IZSceneDoc.AnimationMgr
oraz IZAnimationMgr: On, Playing, CurrentTime, StartTime, EndTime,
FrameCount, Play, Export i GetElementAnimTimes. Export ma opis AVI.
To potwierdza interfejs sterowania istniejącą animacją, nie pełny kreator
ścieżek. W odczytanym interfejsie nie znaleziono metod dodawania ścieżek
czy klatek. Pierwszą ścieżkę można przygotować przez SmartMotion w kopii
lub zweryfikowany szablon; automatyczne tworzenie przez SDK wymaga dowodu.
Nie uruchamiano Play ani Export i nie zmieniano aktywnego modelu.

Kryterium wykonania nice-to-have: osobna scena, rzeczywisty ruch na osi obu
zawiasów, sterowanie zamknięte/otwarte, powrót do zamkniętego po odtwarzaniu,
bezpieczny zapis/otwarcie i brak zmian w głównej rewizji. Animacja poglądowa
nie zastępuje sprawdzenia kolizji, nośności ani kwalifikacji zawiasów.

Dodatkowe źródła do etapu więzów:
[Positioning Constraints](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/Using_the_Positioning_Constraint_Tool.htm)
— m.in. współosiowość, ustalenie i kąt; oraz
[Collision Detection](https://www.ironcad.com/support/INOVATE_Help/Content/3D_Design_Environment/Positioning_Objects/Using_Collision_Detection_in_the_Mechanism_Mode.htm).
Więzy należy dobrać tak, aby zostawić dokładnie jeden stopień swobody obrotu
wieka i nie zablokować układu nadmiarowymi więzami na obu zawiasach.

Zapisano w Linear: [ROC-44](https://linear.app/rock-pro/issue/ROC-44/nice-to-have-animacja-otwierania-pokrywy-wokol-osi-zawiasow), projekt RockPro CAD, Backlog, Low.
Potwierdzono utworzenie i treść w zalogowanej przeglądarce.
