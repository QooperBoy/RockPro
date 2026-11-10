def panel_label(half, role):
    return {
        'front': 'przód [Y min | płaszczyzna XZ]',
        'back': 'tył [Y max | płaszczyzna XZ]',
        'left': 'lewa [X min | płaszczyzna YZ]',
        'right': 'prawa [X max | płaszczyzna YZ]',
        'closure': ('dno [Z min | płaszczyzna XY]' if half == 'base'
                    else 'wieko [Z max | płaszczyzna XY]'),
    }[role]
