# WG-Kassenabrechnung

Kleines Programm, das die gemeinsame WG-Kasse fair abrechnet: Jede Person trägt
ein, wie viel sie für die WG ausgegeben hat und an wie vielen Tagen sie da war.
Das Programm berechnet, wer wie viel zahlen muss, und wer wem wie viel
überweisen soll, mit der **kleinstmöglichen Anzahl an Überweisungen**.

Läuft offline, braucht keine Anmeldung und sendet keine Daten irgendwohin.

## Herunterladen und starten

1. Auf der Seite [**Releases**](../../releases/latest) die passende Datei laden:
   - **Windows:** `WG-Abrechnung.exe`
   - **Mac:** `WG-Abrechnung-mac.zip` (Apple-Chip, M1 oder neuer), danach entpacken
2. Doppelklick auf das Programm. Installation ist nicht nötig.

### Beim ersten Start kommt eine Warnung. Das ist normal.
Das Programm ist nicht bei Microsoft oder Apple registriert, deshalb warnen
die Systeme einmalig vor Programmen aus dem Internet.

- **Windows:** Meldung "Der Computer wurde durch Windows geschützt" →
  **Weitere Informationen** → **Trotzdem ausführen**.
- **Mac:** Rechtsklick auf `WG-Abrechnung.app` → **Öffnen** → nochmal **Öffnen**.
  Wird die App als "beschädigt" gemeldet, im Terminal ausführen
  (Pfad anpassen): `xattr -dr com.apple.quarantine ~/Downloads/WG-Abrechnung.app`

Wer dem Programm nicht traut, kann den Quellcode (`wg_abrechnung.py`, eine
einzige Datei) lesen oder es selbst bauen, siehe unten.

## Bedienung

1. Pro Person eine Zeile ausfüllen:
   - **Name**
   - **Ausgaben (€):** Summe dessen, was die Person für die WG bezahlt hat
     (Klopapier, Putzmittel, Internet, ...)
   - **Tage:** Wie viele Tage die Person im Abrechnungszeitraum in der WG war
2. Mit **+ Person hinzufügen** weitere Zeilen anlegen, mit **Entfernen** löschen.
3. **Berechnen** klicken (oder Enter drücken).
4. Unten steht, wer wem wie viel überweisen muss.
5. Optional: **Ergebnis kopieren** (zum Einfügen in den WG-Chat) oder
   **CSV exportieren** (für Excel).

Beträge werden mit Komma eingegeben, z. B. `12,50` oder `1.234,56`.
Mehrdeutige Eingaben wie `1.234` lehnt das Programm ab, damit sich kein
Zahlendreher einschleicht. Die Eingaben werden beim Schließen gespeichert und beim
nächsten Start wieder geladen (Datei `.wg_abrechnung.json` im Benutzerordner).

## So wird gerechnet

Die Gesamtausgaben werden nach **Personentagen** verteilt: Wer länger da war,
trägt einen größeren Anteil.

> **Beispiel:** Anna hat 120 € ausgegeben (30 Tage), Ben 0 € (30 Tage),
> Clara 60 € (15 Tage).
> Gesamt 180 € bei 75 Personentagen, also 2,40 € pro Tag.
> Fairer Anteil: Anna 72 €, Ben 72 €, Clara 36 €.
> Saldo: Anna bekommt 48 €, Clara bekommt 24 €, Ben muss 72 € zahlen.
> **Ergebnis:** Ben → Anna 48 €, Ben → Clara 24 €.

- Es wird in ganzen Cent gerechnet. Bleiben durch Rundung Cent übrig, werden sie
  nach größtem Rest verteilt, sodass die Summe der Anteile exakt den
  Gesamtausgaben entspricht.
- Die Überweisungen werden exakt minimiert: Das Programm sucht Gruppen von
  Personen, deren Salden sich gegenseitig aufheben, denn jede Gruppe aus *k*
  Personen braucht nur *k − 1* Überweisungen. Bei mehr als 16 Personen mit
  offenem Saldo wird ein einfacheres Näherungsverfahren verwendet.

## Selbst bauen (für Entwickler)

Voraussetzung: Python 3.10+ von [python.org](https://www.python.org/downloads/)
(unter macOS nicht die Homebrew-Version, sie hat oft kein funktionierendes Tk).
Das Programm nutzt nur die Standardbibliothek.

```bash
python wg_abrechnung.py          # direkt starten
python -m unittest -v            # Tests ausführen
```

Ein eigenständiges Programm erzeugen (PyInstaller baut nur für das System, auf dem
es läuft):

- **Windows:** `build_windows.bat` doppelklicken → `dist\WG-Abrechnung.exe`
- **Mac:** `./build_mac.sh` → `WG-Abrechnung-mac.zip`

### Automatisch über GitHub Actions
Der Workflow `.github/workflows/build.yml` baut Windows- und Mac-Version.

- **Testlauf:** Reiter **Actions** → **Build** → **Run workflow**. Die Dateien
  liegen danach unter **Artifacts**.
- **Neue Version veröffentlichen:** **Releases** → **Draft a new release** →
  neuen Tag wie `v1.0.0` anlegen → **Publish release**. Nach etwa drei Minuten
  hängen die fertigen Programme automatisch am Release.

## Lizenz
[MIT](LICENSE): frei nutzbar und veränderbar.
