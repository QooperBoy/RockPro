from pathlib import Path
p=Path('docs/LAYOUT_VERSIONING.md');s=p.read_text(encoding='utf-8');s+='''
## Wynik próby 21.10.2026

- PASS: audyt repozytorium, testy backendu/QA/harness, kompilacja dodatku i testy formularzy przez scripts/Verify.ps1.
- PASS: migracja istniejącego układu użytkownika do v1; cztery urządzenia 400 × 220 × 80 mm, orientacja YXZ, piętrowanie Z.
- PASS: rzeczywisty IronCAD 2027, nowa kopia ICS, przebudowa, pomiar przed zapisem i po ponownym otwarciu. Źródło niezmienione; archiwum SHA256 verified.
- PASS: snapshot przypięty do v1; po kolejnym zapisie identycznej specyfikacji jako v2 snapshot nadal ma v1 i pierwotny hash. Stary token v1 odrzucony po utworzeniu v2.
- PASS: nowa DLL zarejestrowana i załadowana (InitSelf w logu hosta). Baza oraz poprzedni kod zostały zachowane lokalnie poza Git.
- NOT RUN: pełny scenariusz komunikatu konfliktu w UI hosta — okno powitalne IronCAD poza obszarem głównego okna blokowało Computer Use. Kompilacja/formularzowe testy offline nie zastępują tej kontroli.

Raporty lokalne: artifacts/verification/20261021T113017680230Z oraz artifacts/native_versions.json (nie publikować ścieżek klientów i modeli w Git). Testy jednostkowe obejmują prawdziwe równoczesne transakcje SQLite, ale symulują CAD; wyżej wymieniona próba natywna została wykonana oddzielnie.
''';p.write_text(s,encoding='utf-8')
