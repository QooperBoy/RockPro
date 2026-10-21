---
name: rockpro-scope-check
description: Keep RockPro CAD changes focused when adding features, changing architecture or mixing fixes with new requests; provide a concrete recovery prompt when scope or verification becomes a problem.
---

# RockPro — zakres i powrót do jakości

Stosuj do pracy developerskiej w tym projekcie. Kieruj się AGENTS.md i docs/DEVELOPMENT.md, nie ogólnymi zaleceniami dla najnowszego .NET.

Porównaj prośbę z kodem, `git status`, zakresem w LAYOUT.md i dostępnymi dowodami. Ustal rezultat i obserwowalne kryterium zakończenia; dla prostej poprawki wystarczy jedno zdanie, bez osobnego planu.

- **READY**: zakres i sprawdzenie są jasne — implementuj.
- **SPLIT**: prośba łączy niezależne moduły lub rozszerza trwającą zmianę — ułóż autoryzowane prace w sprawdzalne kroki. Powiedz, który realizujesz teraz, zachowaj pozostałe i kontynuuj je w kolejności.
- **FIX_FIRST**: potwierdzony błąd zagraża danym, zapisowi/otwarciu lub blokuje dotknięty przepływ — napraw przed zależnymi funkcjami, jeśli mieści się to w zleceniu. Niezwiązany problem opisz jako osobne zadanie.
- **NEEDS_EVIDENCE**: makieta, wynik kompilacji albo stary raport są traktowane jako działająca integracja — najpierw zdobądź brakujący dowód. Brak dowodu nie oznacza automatycznie awarii.

Sygnały do checkpointu: kilka niezależnych modułów naraz, kolejne obejścia tego samego błędu, obchodzenie allowlisty/manifestu, rozbieżność checkoutu i instalacji, przedstawianie podglądu jako modelu produkcyjnego, niedziałające istotne testy lub brak wymaganego testu natywnego.

Sam rozmiar pliku, kilka poprawek UI lub wiele pomysłów nie uzasadniają zatrzymania. Nowe życzenia aktualizują zakres; nie ignoruj ich. Nie wymuszaj ponownej zgody na autoryzowaną implementację. Pytaj dopiero o istotną decyzję lub dane, których nie da się ustalić z repozytorium i kontekstu.

## Komunikat

Przy wykrytym problemie pokaż krótko:

> Checkpoint RockPro: [problem i dowód]. Najpierw [naprawa / odtworzenie / weryfikacja], potem [zależny element].
>
> Prompt do użycia: „Wróć do [konkretny przepływ/plik]. Użyj $rockpro-scope-check i $rockpro-verification. Odtwórz [objaw], wykonaj [następny krok] i potwierdź [mierzalny wynik]. Zachowaj [dane/kontrakty]; po sprawdzeniu wróć do [pozostały zakres]”.

Wypełnij pola faktami. Nie wysyłaj pustego szablonu ani „sprawdź wszystko”. Jeśli możesz wykonać krok sam, wykonaj go w tej samej pracy. Prompt pomaga wrócić do zadania, nie przerzuca wykonania na użytkownika.

Do osobno zleconego odtworzenia niejasnego błędu można użyć ../bug-reproduction-brief/SKILL.md. Nie zastępuj diagnostycznym briefem pełnej naprawy, jeśli użytkownik zlecił naprawę.
