"""Geometric descriptions of the existing wooden skeleton parameters."""
PARAMETER_NOTES = {
    'RP_Length': 'Długość ZEWNĘTRZNA szkieletu w osi X, wspólna dla góry i dołu; od zewnętrznej powierzchni lewej ściany do prawej. Wolne wnętrze X = RP_Length - 2*RP_Thickness. Bez okuć i pianek.',
    'RP_Depth': 'Głębokość / szerokość ZEWNĘTRZNA szkieletu w osi Y, wspólna dla góry i dołu; od zewnętrznej powierzchni przedniej ściany do tylnej. Wolne wnętrze Y = RP_Depth - 2*RP_Thickness. Bez okuć i pianek.',
    'RP_BaseHeight': 'Wysokość ZEWNĘTRZNA dołu w osi Z: od spodu płyty dennej do górnej krawędzi ścian dołu. Zawiera grubość dna. Głębokość wnętrza dołu = RP_BaseHeight - RP_Thickness. Bez kół, profili i okuć.',
    'RP_LidHeight': 'Wysokość ZEWNĘTRZNA pokrywy w osi Z: od dolnej krawędzi jej ścian do zewnętrznej powierzchni płyty wieka. Zawiera grubość wieka. Głębokość wnętrza pokrywy = RP_LidHeight - RP_Thickness.',
    'RP_Thickness': 'Grubość T każdej z 10 płyt sklejki, mierzona prostopadle do powierzchni płyty; nie jest wymiarem wnętrza ani luzem. Wnętrze X/Y maleje o 2*T, a wysokość wnętrza zamkniętego szkieletu = RP_BaseHeight + RP_LidHeight - 2*T. Zmiana L/D/H nie skaluje T.',
    'RP_DisplayGap': 'Odstęp PREZENTACYJNY w osi Z między górną krawędzią dołu a dolną krawędzią pokrywy. 0 mm = zamknięty szkielet. Nie jest luzem montażowym ani przestrzenią użytkową. Wysokość zewnętrzna zamkniętego szkieletu = RP_BaseHeight + RP_LidHeight; bez kół i okuć.',
}
