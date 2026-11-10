"""Measured T1 mounting constraints, in millimetres; no CAD side effects.

410429 mounting wings are at local X/Y/Z=16.5 and face negative axes.
38083 seats on face 44, not the top/bottom of its bounding box.
These datums apply to the pinned T1 parts, not arbitrary catalog replacements.
"""
import math

CORNER_SEAT = 16.5
SOCKET_SEAT = (0., 58.21088152752006, -33.28911847247994)
PROFILE_LEG = 35.
PROFILE_CENTER_INSET = 15.5
PROFILE_INNER_EDGE = PROFILE_CENTER_INSET + PROFILE_LEG / 2
DEFAULT_CLEARANCE = 2.

# Manufacturer installation envelope: 79 x 82 mm, depth 8 mm.
# Native dish corner centres are (+/-28.1, +/-29.6) mm in X/Z.
# R=11.4 preserves these centres within the installation envelope. The CAD
# cup wall has R8.4 plus the 3 mm transition into the mounting flange.
# This is a mounting contour, not a rounded hardware bounding box.
HINGE_27095_OPENING = dict(
    sku='27095', revision='27095-opening-v1', shape='rounded_rectangle',
    width_mm=79., height_mm=82., radius_mm=11.4, installation_depth_mm=8.,
    requires_plywood_cut=True, requires_profile_cut=True,
    source_url='https://www.adamhall.com/shop/en/27095-27095',
    radius_source='Native cup corner centres and transition; prototype fit checked by CAD collision test',
    production_approved=False)


def support_dimensions(depth, clearance=DEFAULT_CLEARANCE):
    if not all(math.isfinite(x) for x in (depth, clearance)) or clearance < 0:
        raise ValueError('Nieprawidłowy luz podpory')
    inset = PROFILE_INNER_EDGE + clearance
    if depth <= 2 * inset:
        raise ValueError('Brak miejsca na podporę pomiędzy profilami')
    return inset, depth - 2 * inset


def corner_pose(top, right, rear, size):
    """Seat all three wings on plywood, with the rounded shell outside.

    The local solid extends towards negative axes from the mounting planes.
    Swap Y/Z for odd parity: a rotation, never mirrored catalog geometry.
    """
    signs = [1 if right else -1, 1 if rear else -1, 1 if top else -1]
    rotation = [[signs[i] if i == j else 0 for j in range(3)] for i in range(3)]
    if math.prod(signs) < 0:
        rotation[1], rotation[2] = rotation[2], rotation[1]
    corner = [size[0] if right else 0, size[1] if rear else 0, size[2] if top else 0]
    position = [corner[j] - CORNER_SEAT * sum(rotation[k][j] for k in range(3)) for j in range(3)]
    return rotation, position


def hinge_profile_interval(center, width=102., clearance=DEFAULT_CLEARANCE):
    if width <= 0 or clearance < 0 or not all(math.isfinite(x) for x in (center, width, clearance)):
        raise ValueError('Nieprawidłowa strefa zawiasu')
    return center - width / 2 - clearance, center + width / 2 + clearance


# Identifier spelling is ASCII for stable native expression paths. Notes use Polish.
# Length/depth describe plywood, not the projecting hardware envelope.
PARAMETERS_PL = {
    'RP_Length': ('RP_Dlugosc', 'Długość obrysu sklejki, oś X: od lewej do prawej ściany. Bez wystających okuć.'),
    'RP_Depth': ('RP_Glebokosc', 'Głębokość obrysu sklejki, oś Y: od przedniej ściany z zamkami do tylnej z zawiasami. Bez okuć.'),
    'RP_BaseHeight': ('RP_WysokoscKorpusu', 'Od spodu sklejki dna do górnej krawędzi ścian korpusu. Bez kół i podpór.'),
    'RP_LidHeight': ('RP_WysokoscPokrywy', 'Od górnej krawędzi korpusu do wierzchu sklejki pokrywy przy zamknięciu; zawiera szczelinę połączenia. Obecne 115 mm to podwyższony wariant.'),
    'RP_Thickness': ('RP_GruboscSklejki', 'Grubość płyt sklejki. Podpory kół mają osobno ustaloną grubość 18 mm.'),
    'RP_JointGap': ('RP_SzczelinaPolaczenia', 'Pionowy odstęp krawędzi sklejki korpusu i pokrywy, zajmowany przez złącze profili. Nie jest luzem montażowym okuć.'),
    'RP_DisplayGap': ('RP_RozsunieciePokrywy', 'Wyłącznie prezentacyjne uniesienie całej pokrywy wraz z jej okuciami. 0 mm oznacza zamknięcie; nie zmienia wymiarów cięcia.'),
    'RP_HandleOffset': ('RP_PrzesuniecieUchwytow', 'Wspólne przesunięcie uchwytów i ich wycięć w osi Y. 0 mm: po dwa uchwyty na przeciwległych bokach, w 1/4 i 3/4 głębokości.'),
    'RP_HandleHeightOffset': ('RP_PodniesienieUchwytow', 'Przesunięcie uchwytów i ich wycięć w pionie względem połowy wysokości korpusu. Dodatnia wartość podnosi.'),
    'RP_LatchInset': ('RP_OdsuniecieZamkow', 'Odległość osi pierwszego zamka od lewej krawędzi; drugi symetrycznie od prawej. Przesuwa też wycięcia.'),
    'RP_HingeInset': ('RP_OdsuniecieZawiasow', 'Odległość osi pierwszego zawiasu od lewej krawędzi; drugi symetrycznie od prawej. Przesuwa również przerwy w profilach.'),
    'RP_MountClearance': ('RP_LuzMontazowy', 'Luz podpór względem wewnętrznych krawędzi profili oraz luz przerw w profilach po bokach zawiasów. Domyślnie 2 mm.'),
}
