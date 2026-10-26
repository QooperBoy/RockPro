# RockPro: opcje rozszerzenia ICAPI bez zmiany aplikacji

Stan rozpoznania: 26.10.2026. Zakres: dokumentacja producenta, kod RockPro i lokalne metadane SDK.
Nie uruchamiano CAD, COM, SmartMotion ani eksportu; nie zmieniano modeli, instalacji i DLL dodatku.
To plan techniczny, a nie odbiór funkcji. Szersze produkty i integracje: [research rynku](MARKET_RESEARCH_20261026.md).

## Wniosek i poziomy dowodu

Największą wartość mają teraz powiązane wycięcia oraz powtarzalna paczka rysunków/BOM.
Obie funkcje mają potrzebne podstawowe interfejsy w 2023 i 2027. SmartAssembly może pomóc
w ręcznym montażu, a animacja jest osobnym przyrostem po ustaleniu osi zawiasów.
Nie ma powodu przepisywać WinForms: reguły zostają w Pythonie, wykonanie w istniejącym adapterze ICAPI.

| Obszar | API/dokumentacja istnieje | RockPro już używa | Dowód natywny |
|---|---|---|---|
| Parametry położenia i wycięcia płyt | TAK, wspólny rdzeń 25/29 | T1MachiningPrototype, RepairT1Mounting2023, T2ParametricPrototype | Historyczne wyniki T1/T2 opisane niżej; nie wykonano ponownie |
| SmartAssembly/attachment points | TAK w pomocy 2023; zdarzenia w lokalnym SDK | Nie znaleziono wdrożenia tych zdarzeń w kodzie `.cs`/`.py` poza artifacts | NOT RUN |
| Tworzenie nowej ścieżki SmartMotion przez SDK | Niepotwierdzone; sterowanie istniejącą animacją TAK | Dokument propozycji ROC-44, nie kreator | NOT RUN |
| Arkusze, widoki, BOM, eksport DXF/PDF | TAK w lokalnym SDK 25/29 | Nie znaleziono użycia wymienionych poniżej interfejsów rysunkowych w kodzie poza artifacts | NOT RUN |
| Nowy szybki układ arkusza i eksport oznaczonych widoków | TAK w odczytanej wersji 29, brak tych metod w 25 | Brak potwierdzonego użycia | NOT RUN |

„Brak znalezionego użycia” dotyczy tego przeglądu, nie obietnicy braku historycznych eksperymentów.
Metadane potwierdzają sygnaturę, nie zachowanie hosta, licencję ani poprawność wyniku produkcyjnego.

## Co dokładnie zbadano lokalnie

- Źródło 2023: `C:\Program Files\IronCAD\2023\bin\ICApiIronCAD.tlb`, SHA256 `612CDBB9BA69F0B70A0222DD9A2C25B043E97E1595BEEEB6A093BFA2BA89CA6F`.
- Źródło 2027: `C:\Program Files\IronCAD\2027\bin\ICApiIronCAD.tlb`, SHA256 `A4A07BE678226ECBDB3FC217BD21DC34EACAAA3D80676F626CF2147F6420B982`.
- Interop 2023 w `artifacts/t2-parametric-20261026/native-15-body/`: wersja 25.0.0.0; zapisany `interop-generation.json` wskazuje ten sam SHA źródłowego TLB.
- Interop 2027 wygenerowano do prywatnego `artifacts/night-research-20261026/sdk2027/`: wersja 29.0.0.0.
- Użyto istniejącego `scripts/native/GenerateLocalInterop.cs` (`LoadTypeLibEx` z REGKIND_NONE); bez rejestracji i uruchamiania IronCAD. Konwersja zakończona kodem 0, z ostrzeżeniami marshallingu: to nie wdrożony adapter.
- Odczyt refleksją: `sdk-2023-installed-metadata.json`, `sdk-2027-installed-metadata.json`, porównanie `sdk-comparison.json` w tym samym prywatnym katalogu.
- Dokumenty SDK istnieją w `C:\Program Files\IronCAD\2023\ICAPI\Docs\` i analogicznie `2027`: `ICAPIHELP.chm`, `ICAPIIRONCADLib.chm`. Ich samo istnienie nie stanowi dowodu przeczytania zawartości.

**Pułapka wersji:** plik `C:\Program Files\IronCAD\2027\ICAPI\Samples\C#\References\interop.ICApiIronCAD.dll`
ma metadane wersji **27.0.0.0**, mimo folderu 2027. `scripts/run_t1_machining_job.py:current_interop`
wybiera ten plik dla roku innego niż 2023. Nie dowodzi to awarii dotychczasowych prób, lecz oznacza,
że nowych metod 29 nie należy szukać wyłącznie w tym wrapperze. Przed ich użyciem: właściwy TLB,
hash, osobna kompilacja i próba hosta. Nie podmieniono DLL w tej analizie.

## 1. Okucie + wycięcie jako jedna decyzja montażowa

Pomoc [SmartAssembly 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/SmartAssembly_Positioning.htm)
opisuje nazwane pary punktów `_M`/`_F`/`_N`, pozycjonowanie przy upuszczeniu z katalogu,
dopasowanie parametrów i opcjonalne więzy. Osie Z pary są przeciwnie skierowane, X zgodne.
Konwencja nazw rozróżnia wielkość liter. To przydatne do kontrolowanego przyłączania, nie gotowa baza technologii wycięć.
[Attachment Points](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/Attachment_Point_Positioning.htm)
ostrzega, że przesunięcie dołączonego elementu może zerwać powiązanie; nie obiecujemy obsługi każdego ruchu TriBallem.
Producent opisuje [Smart eBehavior](https://www.ironcad.com/blog/configuration-based-design/)
jako inteligencję komponentów: pozycjonowanie, rozmiar, orientację i zachowania. Sama nazwa nie gwarantuje
konkretnej metody API tworzącej otwór ani trwałego właściciela obróbki.

Faktycznie znalezione wspólne mechanizmy ICAPI 25/29:

- `IZParameterMgr.CreateParameter`, `GetParameterByName`; `IZParameter.Expression`, `Value`, `Notes`.
- `IZSceneElement.ForceSetupParameterExpression`, `SetTransformToParent`, `SetAnchorTransform`, `SetPositionTransform` i indeksowane `PositionTransformComponentExpression`.
- `IZPartFeatureMgr.CreateExtrudeFeature(...)` z `eZOperationType.Z_SUBTRACT`; `IZFeature.CopyFeatureTo(IZPart)` i `OperationType`.
- `IZExtrudeFeature.CrossSection`, `ExtrudeDistance`, `ExtrudeThroughPart`: dostępne właściwości, nie dowód poprawnego konturu konkretnego SKU.
- W 29 `_IZSmartAssemblyExEvents`: `OnPreMatchPair`, `OnPreParameterMatch`, `OnPrePositioning`, `OnPostPositioning`.
- W 29 `IZSmartAssemblyExEvents.SetSmartAssemblyNextDroppedOnObj`, `ResetSmartAssemblyNextDroppedOnObjInfo`, `GetSmartAssemblyNextDroppedOnObj`; w odczytanym interfejsie 25 brak tych trzech metod.

Nie znaleziono metody o nazwie `AttachmentPoint`, `AttachPoint`, `AttachPt` ani `SmartBehavior`
w nazwach metod przejrzanych interfejsów wrappera 29. To luka rozpoznania kreatora, nie dowód niemożliwości integracji.
Zdarzenia przed/po upuszczeniu nie są dowodem przechwytywania każdej późniejszej edycji.

W RockPro istnieją już wiązania przez parametry sceny i ujemne cechy płyt:
[T1 machining](T1_MACHINING_PROTOTYPE.md), [naprawa T1 2023](T1_2023_MOUNTING_REPAIR.md), [T2](T2_PARAMETRIC_PROTOTYPE.md).
Kod: `scripts/native/T1MachiningPrototype.cs`, `RepairT1Mounting2023.cs`, `T2ParametricPrototype.cs`.
Historyczne PASS dotyczą wskazanych prototypów i zmian parametrów, nie dowolnego modelu/katalogu ani ruchu ręcznego.

Propozycja: rejestr przechowuje `occurrence_id → mounting_template_version → host_panel_id → cutout_ids`,
lokalną ramę i podpis transformacji. Kontur ma pochodzić z zatwierdzonego szablonu, nigdy z bbox okucia.
Planer liczy równocześnie transformację okucia, wycięcia i odstępy; adapter wykonuje jeden sprawdzalny krok etapu.
Ręczny ruch spoza tego przepływu najpierw oznacza „wymaga uzgodnienia”, zamiast automatycznego cięcia w niewłaściwej płycie.
SmartAssembly można później wpiąć jako sposób wprowadzania decyzji do tego samego rejestru.

## 2. Otwieranie na rzeczywistej osi zawiasu

[SmartMotion](https://www.ironcad.com/support/2024/IRONCAD_Help/Content/Animation/Animating_an_Assembly_.htm)
obraca zespół wokół osi kotwy; kotwę można przestawić. To wystarcza do zaprojektowania prezentacji,
ale oś trzeba odczytać ze sworzni lub zatwierdzonych danych montażowych, a nie ze środka bbox.
[Mechanism Mode 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/3D_Design_Environment/Positioning_Objects/Using_the_Mechanism_Mode.htm)
pozwala rozwiązywać więzy podczas ruchu, oglądać przenikanie i odtwarzać SmartMotion.
Hierarchia i więzy między poziomami ograniczają rozwiązanie; animacja nie zastępuje walidacji mechanizmu.

W 25/29 znaleziono `IZSceneDoc.AnimationMgr`; `IZAnimationMgr.On`, `Playing`, `CurrentTime`,
`StartTime`, `EndTime`, `Play(ref double, ref double)`, `Export(ref double, ref double)`, `GetElementAnimTimes`.
W tym interfejsie brak kreatora ścieżki lub klatek. Wspólna jest również obecność `IZSceneDoc.ConstraintSolver`;
nie zbadano tu kontraktu tworzenia kompletu więzów. Nie utożsamiamy odtwarzania z tworzeniem animacji.

Najmniejszy przyrost: przygotowany i sprawdzony szablon ścieżki + sterowanie ICAPI, na osobnej scenie prezentacyjnej.
Ruchome są właściwe części pokrywy i górne połówki zawiasów; zwolnić zamki przed ruchem.
Trzeba zachować lub przepiąć `Parent\Params` przy zmianie hierarchii. Istniejące rozsunięcie prezentacyjne
ani odsunięcie sztywnej osłony nie jest animacją zawiasową. Kontynuacja: [ROC-44 / plan](CASE_OPENING_ANIMATION.md).

## 3. Arkusze, formatki, BOM i eksport

Znalezione w obu wersjach:

- `IZDrawingDoc.AddSheet(bool,string)`, `GetTDSheets`, `BOMManager`, `TDExportControl`, `TDPDFExportManager`.
- `IZTDSheet.CreateStandardTDView`, `CreateGeneralTDView`, warianty `WithScale`, `HideElementsInViews`, `AutoItemBubbleView`.
- `IZBOMManager.CreateBOM`, `CreateBOMEx`, `ExportBOMAsExcel`, `ExportBOMAsTabDelimText`.
- `IZPart`/`IZAssembly.IncludedInBOM`, `BOMPartNumber`, `BOMDescription`, ustawiana ilość BOM; `IZSceneDoc.ExportBOM(string)`.
- `IZTDExportControl.Export`, `ExportSheet`, `IgnoreViewScale`, `SetDwgDxfBasedOnViewScale`; eksport jest sterowalny, więc jednostki/skala wymagają kontroli.
- `IZTDPDFExportManager.ExportDrawing`, `ExportSheet`, `ExportMultiSheet`, `Quality`, `DPI`, `ForceTrueRepresentation`.

Przykład producenta `2027\ICAPI\Samples\C#\BOMPropExample\BOMPropTool.cs` czyta właściwości BOM części/zespołów.
[Pomoc BOM 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/2D_Detail_Design_Environment/Bill_of_Material_Tables.htm)
potwierdza tabele ze sceny/widoku, właściwości użytkownika i eksport. Nie dowodzi kompletności zakupowego BOM RockPro.
Musimy rozróżniać całe zakupowe okucie, jego wewnętrzne części, formatkę i operację obróbki, aby nie podwajać ilości.

W 29, lecz nie w odczytanym 25, występują:
`IZDrawingDoc.AddSheetWithLayoutForBulkViewCreation(string,string,string,uint,uint)`,
`IZTDSheet.ReplaceFrameFromTemplate`, `ReplaceTitleBlockFromTemplate`, `UpdateAllViews`, `Activate`,
`IZTDView.UserSelectedProjectedTreeShapeIDs`, `UserSelectionForProjection`,
`IZTDExportControl.SetExportDxfDwgMarkedViewsOnly(bool)`.
Wspólny fallback: pętla arkuszy i pojedynczych widoków. Nie uzależniać całej paczki od metody tylko z 29.

Formatka produkcyjna wymaga izolacji właściwej płyty, płaszczyzny lokalnej, skali 1:1, zamkniętych konturów,
oddzielenia obrysu od kieszeni/otworów i kontroli jednostek. Zwykły eksport widoku z ukrytymi krawędziami
nie staje się automatycznie DXF do CNC. CAM, frez i postprocesor pozostają osobnym etapem zależnym od zakładu.

## Wpięcie w obecną architekturę i trzy następne próby

Rozszerzyć manifest rodziny i wersjonowany rejestr operacji, nie tworzyć równoległej bazy w C#.
Przepływ: Python planuje → weryfikuje dane/kolizje → jeden wykonawca ICAPI → odczyt wyniku →
artefakty z rewizją i hashami → SQLite/obserwator → WinForms. UI pokazuje plan, wykonanie i braki dowodów oddzielnie.
Adapter ma deklarować wykryte możliwości po wersji interfejsu, z obsługą braku metody; błąd eksportu nie może
oznaczać gotowej paczki. Nowy plugin/MCP ani zmiana frameworka nie są konieczne do tych trzech prób.

1. **P0 — właściciel wycięcia.** Na kopii jednej płyty umieścić zatwierdzony uchwyt i jego kontur; zmienić wspólny parametr X/Y,
   potem wrócić. PASS: transformacje i lokalizacja ujemnej cechy zgodne, bez duplikatów, niezmienione okucie.
   Osobno przesunąć ręcznie: oczekiwany wykryty konflikt, dopóki reconciler nie ma potwierdzonej obsługi. Zacząć od 2027, później powtórzyć kontrakt na 2023.
2. **P1 — jedna formatka i BOM.** Przygotować arkusz/widok pojedynczej płyty, PDF i DXF oraz zestawienie obejmujące jedno zakupowe okucie.
   PASS: niezależny odczyt DXF potwierdza mm, rozmiar i kontury; PDF widoczny; BOM nie liczy wewnętrznych części okucia.
   W 2023 użyć wspólnego fallbacku; w 2027 porównać nowy bulk API dopiero po podstawowym PASS.
   Nowe pliki pomocnicze mieszczą się w zleceniu; jeżeli dany eksport wymaga wcześniejszego zapisu ICS,
   ten wariant próby pozostaje zablokowany aktualnym zakazem zapisu modeli.
3. **P2 — zawias 0°/45°/90°/0°.** Zmierzyć oś obu sworzni i zgodność, użyć przygotowanej ścieżki na prezentacyjnej kopii.
   PASS: zachowane położenie osi, właściwy ruchomy zbiór, brak ruchu korpusu, powrót do 0°, raport kolizji w próbkach.
   Kąt 90° to scenariusz testu, nie deklaracja dopuszczalnego otwarcia katalogowego zawiasu. Gdy brak zweryfikowanej ścieżki, zakończyć jako NOT RUN.

Próby mają być jednorazowe i ograniczone do powyższych kryteriów; nie uruchomiono ich w tej analizie.
Nowe rodziny zgodnie z decyzją użytkownika pozostają na 2027; zgodne API nie oznacza, że plik ICS z 2027 otworzy się w 2023.
Dowód reuse to osobny build i próba na każdym hoście. Oficjalna [pomoc API 2023](https://www.ironcad.com/support/2023/IRONCAD_Help/Content/Understanding_the_Basics/Using_the_API.htm)
zaleca ICAPI dla nowych rozszerzeń; nie ma potrzeby wracać do starszego mechanizmu Add-on Tools.
