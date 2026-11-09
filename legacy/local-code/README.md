# Archiwum własnego kodu lokalnego

Stan kopii: 09.11.2026. Nie jest aktywnym runtime ani nowym planem rozwoju.

- `preserved-deployment/`: różniące się źródła zachowanego starszego wdrożenia.
- `generated-diagnostics/`: własne skrypty i sondy z ignorowanych dawnych
  katalogów wynikowych. Mogą zawierać jednorazowe ścieżki, stare kontrakty,
  nieudane eksperymenty i celowo wycofane mechanizmy.

Nie nakładaj tych plików na `Integracja/rockpro_cad`, nie importuj ich podczas
startu aplikacji i nie wykonuj zbiorczo. Część skryptów wykonuje operacje CAD lub
zapis już podczas importu. Najpierw czytaj kod i jego zależności; ewentualną
promocję do aktywnego narzędzia wykonuj jako osobną sprawdzoną zmianę.

Nie przywracaj parametryzacji liczby okuć z dawnych eksperymentów TV.
Duplikaty identyczne z bieżącym kodem pominięto według SHA. Manifest pochodzenia:
[CODE_INVENTORY.json](../../tools/workspace/CODE_INVENTORY.json).
Nie dołączono danych wejściowych, modeli CAD, baz, instalatorów ani bibliotek
zewnętrznych. Samo zachowanie kodu nie oznacza potwierdzenia jego działania.
