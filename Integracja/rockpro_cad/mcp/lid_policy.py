"""Shallow lid policy: hinge mounting height, proportion and explicit override."""
import math

PLYWOOD_COLORREF=0x808040  # ICAPI COLORREF: RGB(64,128,128), #408080, measured T_1.
DEFAULT_LID_RATIO=.12
MAX_LID_RATIO=.15

def minimum_lid_height(required_heights_mm):
    heights=list(required_heights_mm)
    if any(type(h) not in (float,int) or not math.isfinite(h) or h<=0 for h in heights):
        raise ValueError('Wymagane potwierdzone wysokości montażu zawiasów, z luzem konstrukcyjnym')
    return max(heights,default=0.)

def validate_lid_height(height_mm,required_heights_mm,base_height_mm=None,constructor_override=False):
    if type(height_mm) not in (float,int) or not math.isfinite(height_mm):
        raise ValueError('Nieprawidłowa wysokość pokrywy')
    minimum=minimum_lid_height(required_heights_mm)
    if height_mm<minimum:
        raise ValueError(f'Pokrywa: minimum montażowe zawiasu wynosi {minimum:g} mm')
    if type(constructor_override) is not bool:
        raise ValueError('Odstępstwo konstruktora musi być jawne')
    if base_height_mm is not None:
        if type(base_height_mm) not in (float,int) or not math.isfinite(base_height_mm) or base_height_mm<=0:
            raise ValueError('Nieprawidłowa wysokość korpusu')
        if height_mm>MAX_LID_RATIO*base_height_mm+1e-8 and not constructor_override:
            raise ValueError('Pokrywa przekracza 15% korpusu: dobierz okucia lub jawne odstępstwo konstruktora')
    return minimum

def choose_lid_height(base_height_mm,required_heights_mm,ratio=DEFAULT_LID_RATIO):
    if type(ratio) not in (float,int) or not .10<=ratio<=MAX_LID_RATIO:
        raise ValueError('Domyślna proporcja pokrywy: 10–15% wysokości korpusu')
    height=max(base_height_mm*ratio,minimum_lid_height(required_heights_mm))
    validate_lid_height(height,required_heights_mm,base_height_mm)
    return height
