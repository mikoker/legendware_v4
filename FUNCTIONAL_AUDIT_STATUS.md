# Audyt funkcjonalny Legendware — stan 2026-10-02

## Zakres i sposób weryfikacji

Zmiany dotyczą wyłącznie Legendware. `Fatality.win-Source/` jest źródłem porównawczym i nie było modyfikowane. Przedmiotem audytu są kontrakty funkcji i zachowanie kodu dla Source 1 CS:GO, nie aktualizacja offsetów.

Weryfikacja obejmuje niezależny review agenta, analizę istniejących programów w Ghidra, odczyty pamięci działającej gry przez Cheat Engine MCP, testy rzeczywistych fragmentów produkcyjnego C++ z atrapami silnika oraz kompilację `Debug|Win32`. Nie wykonywano zapisu pamięci gry, wstrzykiwania DLL ani zakładania breakpointów.

**Audyt pozostaje otwarty.** Przechodzący build i testy poniżej nie potwierdzają jeszcze całego działania w rozgrywce.

## Zidentyfikowana wersja gry

- Steam app 730, branch `csgo_legacy`, manifest build ID `12426195`.
- `csgo/steam.inf`: `ClientVersion=1575`, `ServerVersion=1575`, `PatchVersion=1.38.8.1`, `SourceRevision=8413246`, data `Oct 12 2023`, czas `09:57:39`.
- Działający proces: `csgo.exe`, PID 13568, architektura x86. Lista modułów odczytana z limitem 500 zawierała 204 pozycje.
- Istniejące programy Ghidra `/csgo_v2026/client.dll` i `/csgo_v2026/engine.dll` mają MD5 zgodne z plikami lokalnej instalacji, mimo nazwy folderu projektu: klient `d93600568b38277269c212ef494105a3`, silnik `9887428753ab685594450a742ec3c87d`.
- Ponowny odczyt `engine.dll + 0x59F19C` wskazał clientstate `0xFC6A0010`; `clientstate + 0x108` miało `signon_state=0`. W chwili odczytu gra nie znajdowała się w aktywnej sesji. Nie potwierdzono działania zmienionej DLL w rozgrywce.

## Potwierdzone kontrakty w rzeczywistej binarce

Adresy poniżej są RVA względem badanego modułu; służą dokumentacji dowodów, nie nowym offsetom produkcyjnym.

| Obszar | Dowód | Wniosek dla implementacji |
|---|---|---|
| `SetupBones`, client RVA `0x1D3140` | Normalizacja masek i sprawdzanie readable mask przed przebudową; końcówka `0x1D3DF4..0x1D3E66` | Wynik jest bool. Null output może pominąć kopiowanie, za mały bufor daje false, sukces kopiuje liczbę kości cache × 48 bajtów. |
| Maska `SetupBones` | RVA `0x1D3218..0x1D34B3` | Silnik dodaje flagi, rozwija LOD i obsługuje maskę `-1`. Zwykłe wywołania muszą delegować do silnika; historyczna macierz ma tylko jawnie obsługiwaną maskę. |
| Headshot multiplier | Attribute getter `0x4394A0`, loader `0x43825B..0x438270` | Dane broni zawierają multiplier przy `+0xF4`; stała 4 nie jest pełnym kontraktem wszystkich broni. Nie zweryfikowano całego serwerowego przepływu obrażeń. |
| AnimState update | `UpdateClientSideAnimation` RVA `0x3E7A80` → `0x43E9E0`; `0x43EA93..0x43EACF` | Równość czasu lub klatki pomija update; przyrost to `max(curtime-last_update_time, 0)`. Poprzedni czas w przyszłości zeruje postęp. |
| Knife | RTTI `C_Knife`, wspólna funkcja RVA `0x6AED50`; geometria `0x6AEDBF..0x6AEFAF` | Zwykły swing: 48, stab: 32, kierunek jednostkowy. Najpierw ray `MASK_SOLID`, potem hull `(-16,-16,-18)..(16,16,18)` wyłącznie po pudle ray. |
| Backstab i cooldown noża | RVA `0x6AF05F..0x6AF0EF`, `0x6AF195..0x6AF1E3` | Behind test: poziomy kierunek graczy dot forward celu > 0,475. Primary i secondary mają osobne czasy gotowości. Tabela damage pochodzi nadal z Fatality, nie z analizy serwera. |
| Stan sesji | `VEngineClient014`: v12 `0xB6800`, v26 `0xB6D40`, v27 `0x260F0`, v52 `0xB7340`, v53 `0xB7370` | `IsInGame`: signon==6, `IsConnected`: signon>=2. Pozorne pole local player przy signon0 nie dowodzi aktywnego gracza. |

## Wdrożone poprawki

| Commit | Zakres |
|---|---|
| `dc6d125` | Bool kontraktu setup bones, obsługa niepowodzenia i silnikowy fallback. |
| `c223855` | Geometria clippingu pocisku, headshot multiplier i zabezpieczenia penetracji. |
| `11f8ef6` | Przywracanie pozycji i flag encji dormant po tymczasowych sprawdzeniach peek. |
| `c235d1c` | Ważność pomiaru dormant oddzielona od wartości flag, odrzucenie niepoprawnych trace. |
| `383add3` | Historyczny cache kości izolowany od normalnych przebudów silnika, jawne maski. |
| `300222a` | Skanowanie przerywane lub pomijane, gdy historyczny rekord nie może być zastosowany. |
| `dea1188` | Wizualne macierze publikowane dopiero po udanym setup, poprawna liczba kości i translacja. |
| `be240e3` | Poprawny próg hitchance, brak nadpisywania ustawień tasera w każdej komendzie. |
| `eba5dd4` | Rekordy oraz feedback resolvera sprawdzają encję, spawn i model; brak odczytu starej macierzy po zmianie tożsamości. |
| `acc4865` | Bezpieczna historia komend prediction, identity snapshotów i serial handle rewolweru. |
| `9bfdc33` | Dodatni krok czasu replay animacji i zachowanie flagi zewnętrznego update. |
| `b72b7e1` | Poprawne strony kończyn w nazwach i hitboxach `player_hurt`. |
| `219a383` | Granice VMT `< count`, ograniczone wyszukiwanie hashy, obsługa pustego obiektu. |
| `4a549ec` | Usunięcie hooka `Shutdown`, który przerywał natywny lifecycle przez zabicie procesu. |
| `9ba9a1d` | Heap corruption przekazywane do dalszej obsługi systemowej zamiast wznowienia wykonania na uszkodzonej stercie. |
| `0ed280b` | Gotowość i identity shooting pose, bezpieczny fallback po błędzie setup, odtworzenie kątów/pose/layers i unieważnienie tymczasowego cache. |
| `b606354` | Geometria obu ataków nożem, ray przed hull, właściwy cooldown ataku, wybór na podstawie tabeli referencyjnej, zachowanie ręcznych przycisków. |

## Walidacja

Wszystkie 12 zestawów `tests/check_*.py` przeszło razem po ostatniej poprawce noża:

- `check_animation_update`, `check_bone_cache`, `check_command_history`, `check_dormant`;
- `check_finalists`, `check_hitchance`, `check_knife`, `check_prediction`;
- `check_shoot_position`, `check_shots`, `check_vfunc_bounds`, `check_visual_bones`.

Testy kompilują rzeczywiste funkcje albo fragmenty produkcyjne z atrapami wymaganych interfejsów. Sprawdzają konkretne kontrakty i przypadki brzegowe; nie zastępują testu całego klienta z serwerem.

Po każdej grupie zmian wykonano build `Rise.sln /p:Configuration=Debug /p:Platform=Win32`. Końcowy build zakończył się powodzeniem. Przy pełnym linkowaniu pozostaje wcześniejsze ostrzeżenie LNK4099 o brakującym PDB biblioteki MinHook.

## Pozostałe prace, według priorytetu

1. **Rekonstrukcja animacji przy choke.** W `Animations::update` pozostają dzielenia przez playback rate warstw 4, 5 i 11 bez pełnej ochrony przed zerem/NaN. Granica 18 oraz zamiana dużego delta na 1 wymagają sprawdzenia metodologii. Pozycja i kąty nie są rekonstruowane tak samo jak velocity/duck. Duża różnica local tick–simulation tick nie dowodzi sama w sobie exploita.
2. **Lokalne macierze renderowania.** Tablice SIDE_REAL/SIDE_FAKE mogą być użyte przed pierwszą udaną aktualizacją. `LocalAnimations::render` wciąż wymaga obsługi błędu setup i gotowości obu macierzy, niezależnie od poprawionego shooting pose.
3. **Budżet komend i exploitów.** Stałe 6/14/7/16 oraz patch limitu komend należy skonfrontować z rzeczywistą polityką serwera i `sv_maxusrcmdprocessticks`. Sama zgodność z Fatality nie jest potwierdzeniem poprawności.
4. **Walidacja lag compensation.** `AnimationData::valid` miesza tolerancję 0,2 s, dodatkowy choke i lerp. Oddzielić dopuszczalność komendy od retencji rekordów `sv_maxunlag`. Nie usuwać zaokrągleń wyłącznie na podstawie intuicji: publiczny Source SDK ma również całkowitoliczbowy deadtime, a nie jest dokładnym kodem CS:GO.
5. **Prediction restore.** `RestoreData` wymaga osobnego przeglądu abs origin, collision bounds, gracza/spawn i identity broni po symulowanych komendach. Bieżące poprawki historii NetvarsData nie zamykają tego obszaru.
6. **Instalacja hooków.** Statusy MinHook nadal nie są systematycznie sprawdzane; potrzebna kontrola błędów i spójne wycofanie częściowo zainstalowanych hooków. Poprawka granic VMT tego nie zastępuje.
7. **Shot matching i resolver.** Sprawdzić okno czasowe eventów, occlusion względem faktycznego odcinka strzału i ruchomych przeszkód oraz pewność przypisywania miss do kandydata. Trend velocity powinien uwzględniać delta czasu; heuristic confidence nie jest skalibrowanym prawdopodobieństwem.
8. **Knife target scan i dane serwera.** Zweryfikować tabelę obrażeń w rzeczywistym serwerze oraz wybór kolejnego celu, gdy najbliższy jest zasłonięty. Client potwierdza geometrię i timing, nie serwerowe zadawanie damage. Specjalny client path z range64 nie został dodany do zwykłego noża.
9. **Extrapolation.** Sprawdzić horyzont symulacji, kolizje i stan ground; translacja macierzy może dotyczyć tylko gotowych kości w prawidłowych granicach.
10. **Niekompletne funkcje.** Puste lub nieinicjalizowane części grenade warning/skins trzeba oddzielnie ocenić pod kątem faktycznej implementacji. Build nie potwierdza, że deklarowana funkcja działa.

Do zamknięcia audytu potrzebna jest także weryfikacja zachowania zmienionej DLL w aktywnej mapie. Obecne odczyty procesu przy signon0 nie mogą jej zastąpić.
