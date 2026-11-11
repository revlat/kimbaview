# kimbaview – Markdown-Beispiel

Dies ist ein **Beispieldokument** mit *verschiedenen* Elementen. Text kann ~~durchgestrichen~~,
`inline code` oder ein [externer Link](https://example.org) sein. Ein Sprung zur
[Tabelle](#tabelle) funktioniert innerhalb des Dokuments. Links zu anderen Dateien
öffnen sie im selben Fenster: [Seite im Unterordner](unterordner/seite.md) oder
[MediaWiki-Beispiel](example.mediawiki).

## Listen

- Erster Punkt
- Zweiter Punkt
  - Unterpunkt A
  - Unterpunkt B
- Dritter Punkt

1. Schritt eins
2. Schritt zwei
3. Schritt drei

### Aufgaben

- [x] Markdown rendern
- [x] Live-Aktualisierung
- [ ] Kaffee holen

## Tabelle

| Format    | Endungen               | Renderer       |
|:----------|:----------------------:|---------------:|
| Markdown  | `.md`, `.markdown`     | markdown-it-py |
| MediaWiki | `.mediawiki`, `.wiki`  | Pandoc         |

## Code

```python
def gruss(name: str) -> str:
    """Begrüßt jemanden."""
    return f"Hallo, {name}!"

print(gruss("Welt"))
```

```text
Eine sehr lange Zeile, die breiter ist als die Textspalte und deshalb in ihrem eigenen Bereich horizontal scrollt, statt das Layout zu sprengen ............
```

## Bild

Ein lokales Bild aus dem Unterordner `bilder/`:

![Beispielgrafik](bilder/beispiel.png)

## Zitat und Fußnote

> Sicherheit ist kein Produkt, sondern ein Prozess.[^1]

[^1]: Bruce Schneier.
