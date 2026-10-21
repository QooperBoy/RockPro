# Źródła instrukcji i skilli

Sprawdzono 21.10.2026. Repozytorium referencyjne pobrano osobno do `../Research/awesome-copilot`; nie jest zależnością wykonawczą RockPro i jego AGENTS.md nie steruje naszym projektem.

| Źródło | Zastosowanie |
| --- | --- |
| [Microsoft: Prompt Files and Instructions Files Explained](https://devblogs.microsoft.com/dotnet/prompt-files-and-instructions-files-explained/) | Rozdzielenie trwałych instrukcji, instrukcji applyTo i jawnych promptów |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | Repo referencyjne, commit `613efc8c21d9b3ce642dff361d17006cd9967e28`, MIT |
| [bug-reproduction-brief](https://github.com/github/awesome-copilot/tree/613efc8c21d9b3ce642dff361d17006cd9967e28/skills/bug-reproduction-brief) | Zainstalowany bez zmian w .agents/skills przez skill-installer, tylko do briefów diagnostycznych. Zachowano LICENSE oraz źródło wymienione przez upstream |
| [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) | Repozytoryjne .agents/skills, SKILL.md, jawne/automatyczne wywołanie i zakres odkrywania |
| [OpenAI: Using skills to accelerate OSS maintenance](https://developers.openai.com/blog/skills-agents-sdk) | AGENTS jako routing, procedury w skillach, powtarzalne sprawdzenia w skryptach |

## Co zaadaptowano

Lokalne `rockpro-scope-check` i `rockpro-verification`, trzy prompty i trzy instrukcje applyTo są napisane dla RockPro na podstawie powyższych zasad. Nie są kopiami ogólnych instrukcji C#.

Przejrzano też upstream `csharp.instructions.md`, `context-engineering.instructions.md`, `code-review-generic.instructions.md`, skille `refactor`, `refactor-plan`, `breakdown-plan`, `create-specification`. Instrukcji C# nie aktywowano: wymaga najnowszego C# 14/ASP.NET, podczas gdy host budujemy narzędziami .NET Framework. `refactor-plan` wymaga dodatkowej zgody nawet po zleceniu implementacji; nie pasuje to do uprawnionego samodzielnego wykonania w tym projekcie. `breakdown-plan` zakłada rozbudowaną automatyzację zadań GitHub, której użytkownik tu nie zlecił. Materiały pozostają w klonie do późniejszego wyboru.

Pobranie repo nie oznacza aktywacji wszystkich jego skilli lub wykonywania jego skryptów. Upstream jest materiałem referencyjnym. Aktualizacje przypiętego skillu wymagają ponownego przeglądu i aktualizacji tego wpisu, bez automatycznego nadpisywania lokalnych reguł.

## Uruchamianie

- Codex w checkoutcie: `$rockpro-scope-check`, `$rockpro-verification`, `$bug-reproduction-brief`. Nowe skille będą dostępne po odświeżeniu wykrywania, zwykle w kolejnym turnie; w razie braku uruchom klienta ponownie.
- Copilot: instrukcja repozytorium w `.github/copilot-instructions.md` oraz applyTo w `.github/instructions`. Prompty są w `.github/prompts`; uruchamiaj je z listy promptów obsługującego je edytora.
- Ten chat działa z katalogu nadrzędnego. Workspace AGENTS.md kieruje pracę RockPro do checkoutu i bezpośredniego odczytu skilli. Nie instalowano globalnych reguł dla innych projektów.

To instrukcje pracy agenta, nie plugin UI i nie działający w tle monitor. Harness egzekwuje sprawdzenia plików i testy, a interpretacja zakresu pozostaje zadaniem modelu.
