# Studio — spójny interfejs i proces pracy

Bieżące ustawienia przestrzeni: [zwijane panele, resize i tryb nocny](STUDIO_PANELS_AND_THEME.md).

Aktualny przyrost: [przegląd agenta UI/UX, stały sidebar i standardowa kostka](STUDIO_NAVIGATION_REVIEW.md).
Opis punktowego kompasu poniżej przedstawia poprzedni checkpoint.

27.10.2026. Cel: konstruktor operuje skrzynią, kierunkiem i częścią; nie musi
znać identyfikatorów eksportu ani sposobu działania renderera.

## Sprawdzone wzorce i biblioteki

To przegląd oficjalnych dokumentacji i praktyk produktowych, nie deklaracja
certyfikacji dostępności ani zgodności z pełnym standardem branżowym.

| Źródło | Wniosek dla RockPro |
| --- | --- |
| [Onshape: View Cube](https://cad.onshape.com/help/Content/View/view_navigation_and_the_view_cube.htm) | Stały kompas, sześć kierunków, widok przestrzenny i dopasowanie kadru. Nie zmieniamy ustalonego przez użytkownika obrotu środkowym przyciskiem. |
| [Three.js ViewHelper](https://threejs.org/docs/pages/ViewHelper.html) | Helper orientacji powinien śledzić kamerę, a wybór osi ustawiać widok. Zachowujemy istniejący renderer. |
| [Three Viewport Gizmo](https://fennec-hub.github.io/three-viewport-gizmo/api.html) | Rozbudowana gotowa opcja dla Three.js, integracja z OrbitControls i animacja. Do rozważenia przy potrzebie obrotowej kostki/dragowania gizma; wymaga przypięcia wersji zgodnej z lokalnym Three.js. |
| [Three.js OrbitControls](https://threejs.org/docs/pages/OrbitControls) | Jedno źródło pozycji/targetu kamery i jawne update po zmianie widoku. Nie nakładamy drugiego niezależnego kontrolera. |
| [W3C APG Toolbar](https://www.w3.org/WAI/ARIA/apg/patterns/toolbar/) | Opisany toolbar, aria-orientation, pojedynczy punkt Tab i nawigacja strzałkami/Home/End. |
| [Lucide: dostępność ikon](https://github.com/lucide-icons/lucide/blob/main/docs/how-to/accessibility.md) | Ikona jest pomocą, nie jedynym nośnikiem znaczenia. Przycisk ma nazwę, opis po najechaniu i stan. |
| [Radix Tooltip](https://www.radix-ui.com/primitives/docs/components/tooltip) | Opisy przy hover/focus, Esc i jawne stany. Radix jest związany z React; nie przebudowujemy aplikacji dla samego tooltipa. |
| [Shoelace Tooltip](https://next.shoelace.style/components/tooltip) | Alternatywa Web Components przy większej liczbie złożonych popupów. Na obecnym etapie semantyczny HTML wystarcza. |
| [Babylon Utility Layer](https://doc.babylonjs.com/lite/typedoc/functions/createUtilityLayer) | Wzorzec oddzielnej warstwy narzędzi. Migracja renderera nie jest potrzebna dla obecnego zakresu. |

Decyzja: istniejący Three.js + OrbitControls, lokalny moduł `viewport-ui.js`
i semantyczne przyciski/select/details. Ikony to lokalne proste SVG; nie
pobieramy fontów/ikon z CDN ani nie dokładamy frameworka. Kompas DOM śledzi
kwaternion kamery z osiami Z-up. Kierunki mają polskie nazwy, nie geograficzne
N/E, ponieważ odpowiadają ścianom konstrukcji. `Pr` = przód, `Ty` = tył,
`L/P` = lewa/prawa, `G/D` = góra/dół. Lista pod kompasem daje dostęp do każdego
kierunku również wtedy, gdy dwa punkty osi nakładają się w rzucie.

## System ekranu — wdrożony

- Jasna, neutralna powierzchnia; zieleń identyfikuje konstrukcję i aktywny etap,
  pomarańczowy oznacza działanie/wybór. Kolor zawsze ma również opis lub stan.
- Biblioteka wzorców i kreator mają wspólne kolory, typografię, karty i nawigację;
  galeria nadal wyraźnie pokazuje model referencyjny. Kompas tego przyrostu
  dotyczy kreatora koncepcji.
- Stały nagłówek z zapisem. Lewy panel: nazwa projektu, nowa czysta skrzynia,
  bieżący etap oraz sześć kroków. Pasek pokazuje aktualne miejsce w procesie,
  nie zatwierdzenie poprawności lub gotowość produkcyjną.
- Prawy panel: duża przestrzeń 3D. Narzędzia wewnątrz niej, kompas w prawym
  górnym rogu. Układ nie chowa kamery w oddzielnym menu poza modelem.
- Ikony: widok przestrzenny, dopasowanie, otwieranie/zamykanie, siatka,
  podpisy ścian, powiększenie przestrzeni i pomoc. Przyciski mają tooltipy,
  aria-label, widoczny focus i stany przełączników.
- Wstawiana/zaznaczona część ma kontekstowy pasek z nazwą i możliwością
  zakończenia. Nie powstaje drugi niezależny wybór części ani kopia draftu.
- Podsumowanie części, ruchy sekcji i techniczne ograniczenia są oddzielnymi
  rozwijanymi kartami. Informacje o niezatwierdzonym montażu pozostają dostępne.
- Biblioteka ma zwartą siatkę kart, spójne miniatury i wyraźny wybór. Nadal
  pokazuje wyłącznie kompletne części według wcześniejszej preferencji.
- Zapis/import/archiwalne projekty mają własną sekcję. Nowa skrzynia nie kasuje
  zapisanych projektów. Górny zapis korzysta z tej samej funkcji i blokady zapisu.

Skróty: F dopasowuje model zachowując kierunek, 0 ustawia widok przestrzenny,
1/2/3 = przód/prawa/góra, ? otwiera pomoc. Skróty nie działają w polach edycji.
Esc anuluje wstawianie oraz zamyka pomoc/powiększony obszar. Ruch kamery jest
krótki i płynny; `prefers-reduced-motion` wyłącza animację. Środkowy przycisk
nadal obraca, prawy przesuwa, rolka przybliża. Zmiana proporcji obszaru lub
rozmiarów konstrukcji dopasowuje kadr bez wymuszenia perspektywy izometrycznej.

## Cały proces produktu

Jedna koncepcja/draft przechodzi przez kolejne etapy; podgląd i edytory czytają
te same dane. Część należy do wystąpienia na sekcji/ściance lub linii złącza.
UI nie jest źródłem zgód montażowych i nie zastępuje walidatorów backendu.

| Etap | Pytanie konstruktora | Stan |
| --- | --- | --- |
| 1. Konstrukcja | Jaki typ skrzyni? | Wdrożony |
| 2. Wieka | Co i w jakiej kolejności się otwiera/zdejmuje? | Wdrożony |
| 3. Wymiary | Jaką przestrzeń wewnętrzną zachować? | Wdrożony |
| 4. Części | Jakie kompletne elementy wybieram? | Wdrożony; baza firmy do rozszerzenia |
| 5. Uchwyty | Na których ścianach i w jakiej liczbie? | Wdrożony |
| 6. Zamknięcia | Gdzie przebiegają rzędy zawiasów i zatrzasków? | Wdrożony; kontrola obrysów koncepcyjna |
| 7. Podstawa | Koła, stopy, piętrowanie, transport walizkowy? | Plan, osobna implementacja |
| 8. Oznaczenia | Logo, etykiety, kolor wykończenia? | Plan |
| 9. Przegląd | Co jest poprawne, czego brakuje, co wymaga konstruktora? | Plan pełnego widoku review |
| 10. IronCAD | Wygeneruj na kopii, sprawdź, zrób snapshot i folder projektu. | Istnieją osobne prototypy CAD; brak pełnego eksportu kreatora |
| 11. BOM/Excel | Ile skrzyń i jaka wstępna lista materiałów dla zlecenia? | Plan; wymaga pliku i zasad firmy |

Dalszy wzorzec: każdy krok ma kontekst, wybór, bezpośredni podgląd i krótki
wynik; szczegóły montażowe są dostępne na żądanie. Review powinno rozróżniać
błędy blokujące, ostrzeżenia i brakujące dane. Wysłanie do CAD jest świadomym
krokiem po review, z przypiętą rewizją i pojedynczą kolejką wykonawcy. BOM jest
wstępny do zatwierdzenia; wyjście do Excela nie może zmieniać stocku po samym
przeciągnięciu części. Tych przyszłych kroków nie pokazujemy jako gotowych akcji.

## Weryfikacja

Dowody lokalne: `artifacts/studio-ux-20261027/`. Test przeglądarkowy obejmuje
sześć kierunków kamery, zachowanie kierunku przy dopasowaniu, przełączniki,
sterowanie klawiaturą, pomoc, tryb powiększony/Esc, pisanie bez kolizji skrótów,
etapy, filtrowanie kompletnych części, rozmieszczenie, górny zapis i szerokość
mobilną. Sprawdzenie wizualne: desktop, sama przestrzeń 3D, pomoc i ekran wąski.
Kod nie zmienia geometrii/źródeł CAD ani kontraktu draftu. Native CAD: NOT RUN.

Pełny harness PASS: `artifacts/verification/20261027T200018451926Z/`.
