from pathlib import Path
p=Path('Integracja/rockpro_cad/mcp/test_lid_policy.py')
p.write_text('''import unittest
from lid_policy import minimum_lid_height,validate_lid_height,choose_lid_height,PLYWOOD_COLORREF
from layout import calculate_layout

class LidPolicyTests(unittest.TestCase):
    def test_hinge_height_not_three_times_socket_width(self):
        self.assertEqual(minimum_lid_height([30,40]),40)
        self.assertEqual(choose_lid_height(300,[30]),36)
        self.assertEqual(validate_lid_height(45,[40],300),40)
        with self.assertRaises(ValueError):validate_lid_height(39,[40],300)
    def test_conflict_requires_explicit_constructor_exception(self):
        with self.assertRaises(ValueError):choose_lid_height(300,[80])
        with self.assertRaises(ValueError):validate_lid_height(81,[80],300)
        self.assertEqual(validate_lid_height(81,[80],300,True),80)
        with self.assertRaises(ValueError):validate_lid_height(79,[80],300,True)
        for h in (None,True,0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):minimum_lid_height([h])
    def test_layout_preserves_base_space_and_checks_proportion(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=1,lid_hinge_height=30,lid_height=40))
        self.assertEqual(r['parameters']['RP_LidHeight'],40)
        self.assertGreaterEqual(r['parameters']['RP_BaseHeight'],349)
        with self.assertRaises(ValueError):calculate_layout(dict(z=300,count=1,lid_hinge_height=30,lid_height=80))
        r=calculate_layout(dict(z=300,count=1,lid_hinge_height=80,lid_height=81,lid_constructor_override=True))
        self.assertTrue(r['lid_policy']['constructor_override'])
    def test_legacy_geometry_and_green_are_preserved(self):
        r=calculate_layout(dict(x=100,y=200,z=300,count=1,clearance=10,thickness=9,lid_height=50))
        self.assertEqual(r['external'],[138,238,338])
        self.assertNotIn('lid_hinge_height',r['spec'])
        self.assertEqual(PLYWOOD_COLORREF,64+(128<<8)+(128<<16))

if __name__=='__main__':unittest.main()
''',encoding='utf-8')
p=Path('docs/CASE_DEFAULTS.md')
p.write_text('''# Ustalenia użytkownika — aktualizacja 24.10.2026

Sklejka: RGB(64,128,128), #408080, ICAPI COLORREF 0x808040, zmierzone z T_1.

## Pokrywa — obowiązująca reguła

Pokrywa jest płytka, parametryczna. Zwykle ma 10–15% **wysokości korpusu**;
planer przyjmuje 12%, a domyślny górny limit wynosi 15%.
Minimum wynika z pionowego miejsca na zamontowanie zawiasu, złącza,
grubości płyty i niezbędnych luzów. Nie liczymy 3 × szerokość okucia.
Szerokość gniazda na poziomym dachu nie wyznacza wysokości ściany pokrywy.

Jeżeli wybrane okucia nie mieszczą się w limicie, zgłaszamy konflikt.
Dobieramy inny wariant okuć lub konstruktor jawnie dopuszcza odstępstwo.
Nie powiększamy automatycznie korpusu dla uzyskania procentu. Odstępstwo
pozwala zmienić proporcję, ale nie pozwala naruszyć minimum montażowego.

To zastępuje wcześniejszą, błędną zasadę 3 × szerokość i wynik 408 mm.
Historyczne modele i raporty pozostają zachowane jako historia, nie domyślne.

## Inspiracja rzeczywistym EB-L630U

Odczyt płyt z kopii modelu T_1: ściana pokrywy 63,2 mm i dach 9,8 mm,
czyli 73 mm; szczelina pomiędzy płytami korpusu i pokrywy około 8 mm.
Nasz RP_LidHeight obejmuje również tę strefę złącza, zatem odpowiednik wynosi
około 81 mm. Odczyt i macierze: artifacts/eb-l630u-prototype-20261024-01/reference_read.json.

Górna połówka obecnego zawiasu 270836 sięga około 67 mm ponad podział.
Z dachem 9,8 mm i luzem 2 mm wymaga około 80 mm wysokości parametrycznej.
Prototyp 02 ma więc 81 mm pokrywy, 300 mm korpusu, 381 mm obrysu płyt.
To jawne odstępstwo (27%) inspirowane wzorcem, po poleceniu użytkownika,
a nie nowy domyślny procent. Korpus nie został sztucznie powiększony.
H2026 nadal nie jest zamontowany.

## Implementacja

mcp/lid_policy.py wyznacza minimum z wymaganych wysokości montażowych,
sprawdza limit 15% i jawne odstępstwo; choose_lid_height proponuje 12%.
Konfigurator ma minimum montażowe zawiasu (0 oznacza jeszcze niewybrany
zawias), wysokość pokrywy i pole odstępstwa konstruktora.
Backend nie traktuje starego pola lid_hardware_width jako minimum wysokości.
Starsze układy bez nowych pól zachowują dotychczasową geometrię.
Nowa konfiguracja zachowuje przestrzeń urządzeń poniżej podziału.

Walidator profili pozwala na płytkie pokrywy z dodatnią długością każdego
odcinka; nadal odmawia wariantów, gdzie RP_LidHeight - RP_JointGap <= 60 mm.
To ograniczenie obecnej rodziny profili, a nie uniwersalny zakaz płytszych pokryw.

Minimum i limit są egzekwowane przez generator/backend. Bezpośrednia edycja
parametrów w IronCAD wymaga ponownej walidacji. Notatka sceny opisuje wyjątek.
Kompilacja dodatku nie przeładowuje DLL w działającym IronCAD.
''',encoding='utf-8')
p=Path('AGENTS.md');s=p.read_text(encoding='utf-8').replace('parametryczna wysokość pokrywy minimum 3 × największa potwierdzona szerokość montażowa okucia na pokrywie','płytka parametryczna pokrywa, zwykle 10–15% wysokości korpusu, minimum montażowe zawiasu; większa proporcja tylko jako jawne odstępstwo konstruktora');p.write_text(s,encoding='utf-8')
p=Path(r'C:\Users\zuzan\Documents\ChatGPT\Ironcad\AGENTS.md');s=p.read_text(encoding='utf-8');start=s.index('- Future case defaults:');end=s.index('\n',start);s=s[:start]+'- Future case defaults: green plywood RGB(64,128,128), #408080, COLORREF 0x808040. Shallow parametric lid normally 10–15% of base height, minimum set by vertical hinge mounting space including clearances. No 3-times-hardware-width rule. Larger ratios require explicit constructor override; never silently enlarge base to satisfy ratio. Read source docs/CASE_DEFAULTS.md. Preserve historical models and reports.'+s[end:];p.write_text(s,encoding='utf-8')
p=Path('docs/EPSON_PROTOTYPE_V1.md');s=p.read_text(encoding='utf-8');s=s.replace('# Prototyp EB-L630U — 24.10.2026','# Prototyp EB-L630U — 24.10.2026\n\nHISTORYCZNY: proporcja pokrywy została odrzucona przez użytkownika.\nObowiązuje docs/CASE_DEFAULTS.md i Prototyp_02_plytka_pokrywa.\nPoprzedni PASS dotyczył pomiarów, nie akceptacji konstrukcji.');p.write_text(s,encoding='utf-8')
