# WG-Abrechnung als Programm bauen

PyInstaller kann nicht für ein anderes System mitbauen: die Windows-Version
muss auf Windows, die Mac-Version auf einem Mac gebaut werden.

## Variante A: Auf dem eigenen Rechner
- **Windows:** Python von python.org installieren, dann `build_windows.bat`
  doppelklicken. Ergebnis: `dist\WG-Abrechnung.exe`
- **Mac:** Python von python.org installieren, im Terminal `./build_mac.sh`
  ausführen. Ergebnis: `WG-Abrechnung-mac.zip`

## Variante B: Beide Versionen automatisch über GitHub (kostenlos)
1. Kostenloses (privates) Repository auf github.com anlegen.
2. Alle Dateien hochladen, inklusive Ordner `.github/workflows/`.
3. Reiter "Actions" > "Build" > "Run workflow".
4. Nach ca. 3 Minuten unten bei "Artifacts" `WG-Abrechnung-windows` und
   `WG-Abrechnung-mac` herunterladen.

Hinweis: Der GitHub-Mac-Build läuft nur auf Macs mit Apple-Chip (M1 und neuer).
Für ältere Intel-Macs muss das Programm auf einem Intel-Mac gebaut werden.

## Erster Start bei den Mitbewohnern
Das Programm ist nicht signiert, daher warnen die Systeme einmalig:
- **Windows:** "Der Computer wurde durch Windows geschützt" >
  "Weitere Informationen" > "Trotzdem ausführen".
- **Mac:** ZIP entpacken, Rechtsklick auf die App > "Öffnen" > "Öffnen".
  Falls die App als "beschädigt" gemeldet wird, im Terminal:
  `xattr -dr com.apple.quarantine /Pfad/zu/WG-Abrechnung.app`

Die zuletzt eingegebenen Werte merkt sich das Programm in `~/.wg_abrechnung.json`.
