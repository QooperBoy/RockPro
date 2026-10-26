# Odczytowy raport możliwości ICAPI

`scripts/report_icapi_capabilities.py` czyta zapisane JSON-y refleksji SDK i lokalne pliki
wyłącznie w celu SHA256. Nie ładuje DLL, nie aktywuje COM/CAD i nie podmienia adaptera.
Tło: [rozpoznanie SDK](IRONCAD_EXTENSION_OPTIONS_20261026.md).

Jawne wejścia dla każdego roku: `--metadata-2023`, `--evidence-2023`,
`--metadata-2027`, `--evidence-2027`. `--output-dir` musi wskazywać nowy katalog.
Powstają `capabilities.json` i `capabilities.md`; stare wyniki nie są nadpisywane.
Każdy JSON ma limit 16 MiB. Metadane i evidence są parsowane oraz hashowane
z tego samego pojedynczego odczytu, więc późniejsza podmiana pliku nie zmienia
treści raportu. DLL/TLB są hashowane strumieniowo. Raport dotyczy odczytanych
bajtów; nie gwarantuje, że pliki pozostają niezmienne po zakończeniu odczytu.

Plik evidence ma `schema_version: 1`, `host_year`, `api_major`, `metadata_sha256`,
`interop_path`, `interop_sha256`, `tlb_path`, `tlb_sha256`.
Ścieżki mogą być absolutne albo względem evidence; wszystkie pliki muszą istnieć.
Skróty należy obliczyć z rzeczywistych plików, nigdy uzupełniać przykładowymi wartościami.
Raport sprawdza spójność metadanych, interop, roku/API i skrótów; dodatkowo rozpoznaje
wyłącznie dwa faktycznie odczytane snapshoty TLB z 26.10.2026. Inny build/service pack
wymaga nowego odczytu i jawnego przeglądu listy `TLB_SNAPSHOTS`, nie automatycznego obejścia.

`methods_present` oznacza komplet dokładnych sygnatur z zamkniętej listy.
`missing_metadata` oznacza brak dowodu w wejściu, również gdy typu w ogóle nie zapisano.
Nie dowodzi braku API i nie uruchamia fallbacku. Nieznane pola JSON, w tym `supported`
lub `native_status`, nie mogą nadać wsparcia. W każdym wyniku `native_status=NOT RUN`
i `runtime_supported=null`, nawet jeśli wejście twierdzi inaczej.

Grupy: parametry/transformacje, odejmowanie, rysunki, BOM, PDF, odtwarzanie animacji,
oraz metody bulk dostępne w odczytanym API 29. Porównanie pokazuje wspólny komplet,
komplet zapisany tylko dla 25/29 oraz niekompletność obu. Każda grupa wymaga testu hosta.
Probe zapisywał interfejsy, nie wartości enum: obecność metod `subtract` nie jest
dowodem zapisanego `Z_SUBTRACT`. Odtwarzanie animacji nie potwierdza tworzenia ścieżek.

SHA256 potwierdza integralność wskazanych bajtów. Raport nie potwierdza podpisu producenta,
nie odtwarza importu TLB i nie dowodzi kryptograficznie pochodzenia DLL z danego TLB.
Własnoręcznie podmieniony komplet metadanych i skrótów nie staje się zaufanym pomiarem.
Zapisane historyczne `interop-generation.json` pozostaje dodatkowym dowodem procesu.

Wynik lokalnego uruchomienia: `artifacts/night-research-20261026/capabilities-v1/`.
Evidence wejść: `artifacts/night-research-20261026/capability-inputs-v1/`.
Powtórzenie z tych wejść (użyć nowego katalogu docelowego):

```powershell
python scripts/report_icapi_capabilities.py `
  --metadata-2023 artifacts/night-research-20261026/sdk-2023-installed-metadata.json `
  --evidence-2023 artifacts/night-research-20261026/capability-inputs-v1/host-2023.json `
  --metadata-2027 artifacts/night-research-20261026/sdk-2027-installed-metadata.json `
  --evidence-2027 artifacts/night-research-20261026/capability-inputs-v1/host-2027.json `
  --output-dir artifacts/night-research-20261026/capabilities-v2
```

Testy bez SDK: `python scripts/test_icapi_capabilities.py` (syntetyczne wejścia w katalogu tymczasowym).
Nie wykonują żadnej próby natywnej i nie zmieniają danych produkcyjnych.
Końcowy zestaw: 20 testów, w tym podmiana JSON po odczycie i odmowa przy limicie.
