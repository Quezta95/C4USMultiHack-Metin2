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

To nie jest farmbot: program nie przechwytuje obrazu na żywo, nie wysyła klawiszy WASD, nie walczy, nie zbiera przedmiotów i nie obsługuje map ani schowka. Dopasowanie może zawieść po zmianie rozdzielczości, skali UI, języka, grafiki albo przy zasłonięciu napisów. Wynik wymaga sprawdzenia na rzeczywistych klatkach przed użyciem w jakiejkolwiek automatyzacji.
