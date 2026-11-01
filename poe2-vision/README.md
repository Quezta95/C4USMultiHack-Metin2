<!-- coderabbit-ai-generated:v1 -->

# PoE 2 — analiza zrzutów ekranu

Prototyp rozpoznaje pasek bossa The Raven Trickster i tekst Map Completed na pełnych zrzutach w proporcjach zbliżonych do 16:9. Zwraca wynik dopasowania i wykrycie dla każdego sygnału. Wzorce pochodzą z dostarczonych zrzutów (interfejs angielski).

## Windows 11

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:73d836623742ffc40625eb930d723bcd25cb6c2685cb5a13cdfb58263d6929e9 -->

Zainstaluj Python 3.11 lub nowszy, a następnie w PowerShell w tym katalogu:

```powershell
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python server.py
```

Otwórz w przeglądarce **http://127.0.0.1:8765/**, wybierz lub przeciągnij zrzut i kliknij **Analizuj zrzut**. Serwer działa lokalnie; zatrzymasz go przez Ctrl+C w PowerShell.

Analiza z wiersza poleceń nadal jest dostępna:

```powershell
.venv\Scripts\python analyze.py C:\sciezka\do\zrzutu.png
```

<!-- /coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated:v1 -->

<!-- coderabbit-ai-generated-section:v1:2914bb8a59bcdb7fcdeca9c4209b0a1a015253aa1c437dd888f345336c7cab3f -->

## Nakładka minimapy (Windows)

Po instalacji zależności uruchom w PowerShell:

```powershell
.venv\Scripts\python overlay.py
```

Włącz nakładkę i przełącz się do widocznego okna Path of Exile 2. W ustawieniach podaj fragment tytułu okna oraz obszar minimapy jako `x, y, szerokość, wysokość` w procentach obszaru gry. Domyślnie używany jest prawy górny fragment znany z dostarczonych zrzutów. Nakładkę można przesunąć, przeciągając jej pasek; wyłącza się ją w oknie ustawień. Gdy gra przestaje być aktywna, nakładka znika. Jeśli zasłoni źródłowy obszar, zatrzyma się; zmień obszar lub uruchom ją ponownie.

Nakładka powiększa jedynie widoczne piksele ekranu. Nie wykrywa przeciwników ani ich pozycji poza widokiem gry. Wymaga Windows i widocznego okna gry; przechwytywanie pełnoekranowe oraz skalowanie Windows wymagają sprawdzenia na docelowym komputerze.

To nie jest farmbot: program nie wysyła klawiszy WASD, nie walczy, nie zbiera przedmiotów i nie obsługuje map ani schowka. Dopasowanie może zawieść po zmianie rozdzielczości, skali UI, języka, grafiki albo przy zasłonięciu napisów. Wynik wymaga sprawdzenia na rzeczywistych klatkach przed użyciem w jakiejkolwiek automatyzacji.

<!-- /coderabbit-ai-generated:v1 -->
