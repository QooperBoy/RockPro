# Studio — przegląd nawigacji przez agenta UI/UX

27.10.2026. Użytkownik zlecił osobnego agenta UI/UX, inspiracje dla konfiguratorów
wielokrokowych i zastąpienie nietypowego kompasu standardowym rozwiązaniem.
Agent wykonał niezależny przegląd dokumentacji i istniejącego interfejsu, bez
edycji kodu. Poniżej rekomendacje wdrożone w tym przyroście.

## Rozdzielenie nawigacji produktu i projektu

Stałe menu aplikacji ma dwa miejsca: **Konfigurator** oraz **Biblioteka wzorców**.
Jest wspólne dla obu ekranów. Usunięto odsyłacz „Biblioteka 7 wzorców ↗” z nagłówka;
nie sugerujemy otwierania zewnętrznej strony. Galeria ma „Wróć do projektu”.

Pionowe kroki 1–6 należą wyłącznie do aktywnego projektu, pod osobnym nagłówkiem
„Etapy projektu”. Bieżący etap jest odróżniony od poprzednio odwiedzonych; nie
uznajemy odwiedzenia kroku za jego zatwierdzenie. Na wąskim ekranie menu jest
kompaktowym paskiem, a kroki są dostępne przez podpisany select i Dalej/Wstecz.

Inspiracje i uzasadnienie:

- [PatternFly Wizard](https://www.patternfly.org/components/wizard/): osobna
  nawigacja kroków i treść bieżącego etapu.
- [Carbon UI Shell — left panel](https://v10.carbondesignsystem.com/components/UI-shell-left-panel/usage/):
  stałe miejsca aplikacji oddzielone od lokalnych czynności.
- [Carbon Progress Indicator](https://www.carbondesignsystem.com/building-blocks/core/components/progress-indicator/code):
  etapy wielokrokowego zadania z czytelnym wskazaniem bieżącego miejsca.

Przejście do biblioteki zachowuje draft w istniejącym mechanizmie odzyskiwania,
a kontekst widoku w `sessionStorage`, pod kluczem danej sesji Studio: krok,
pozycję/target kamery, zaznaczoną grupę, otwarcie wiek i filtry części. Powrót
odtwarza kontekst tego samego projektu. Nie wykonuje ukrytego zapisu do bazy,
nie tworzy nowego projektu i nie wznawia gestu przeciągania. Oryginalne modele
biblioteki nadal pozostają odrębną referencją.

## Standardowa kostka widoków

Kolorowe punkty i skróty zastąpiono gotowym **three-viewport-gizmo 2.2.0**, tryb
`cube`, z etykietami PRZÓD/TYŁ/LEWA/PRAWA/GÓRA/DÓŁ, klikalnymi krawędziami,
narożnikami oraz Home. Pozycja w prawym górnym rogu, neutralne szare ściany,
obrót zgodny z kamerą i Z-up. Lista widoków zapewnia również obsługę klawiaturą.

- [Fusion ViewCube](https://files.upskill-dev.autodesk.com/public/introduction-to-cad-learn-fusion-360-in-90-minutes/211004_SBS_M4-01_Navigation-and-display-settings.pdf):
  ściana = kierunek, narożnik = widok przestrzenny, Home = widok domyślny.
- [Autodesk Home and ViewCube](https://help.autodesk.com/cloudhelp/ENG/Coord-Models/files/models-viewing-toolbar/Model_Coord_Viewcube.html):
  kierunki standardowe, krawędzie/narożniki i informacja o aktualnym widoku.
- [Onshape View Cube](https://cad.onshape.com/help/Content/View/view_navigation_and_the_view_cube.htm):
  podobna nawigacja bez potrzeby uczenia się niestandardowego kompasu.
- [API three-viewport-gizmo](https://fennec-hub.github.io/three-viewport-gizmo/api.html):
  gotowe typy kostki, integracja z OrbitControls i warianty osi.

Zależność MIT jest przypięta lokalnie; plik i licencja mają hashe w
`viewer3d/vendor/PROVENANCE.json`. Pobrany tarball sprawdzono SHA-512 zgodnym
z metadanymi npm. Peer range obejmuje lokalny Three r180. Runtime nie używa CDN
ani nie instaluje pakietów. Kostka współdzieli renderer, bez drugiego kontekstu
WebGL. Nie zmieniono geometrii, statusów części, kontraktu draftu ani wycięć.

## Weryfikacja

PASS: przeglądarka — wspólne menu, pionowe kroki, sześć kierunków kamery,
kliknięcie kostki, przejście do rzeczywistej biblioteki i powrót z niezapisanym
draftem, kamerą, krokiem 5, zaznaczeniem i otwarciem wieka. PASS: skok etapu
na telefonie i brak poziomego przepełnienia. Prywatne obrazy i raport:
`artifacts/sidebar-viewcube-20261027/`. Natywny CAD: NOT RUN / poza zakresem.

Poprzedni opis kompasu punktowego w STUDIO_UX_DESIGN.md jest historycznym
checkpointem; obowiązuje kostka i nawigacja z niniejszego dokumentu.

Pełna regresja PASS: `artifacts/verification/20261027T201452676654Z/`.
