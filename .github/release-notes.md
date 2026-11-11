**English** · [Deutsch](#deutsch)

## Download

| System | File | Installation |
|---|---|---|
| **Windows 10/11** | `kimbaview-setup-….exe` | Run it and follow the wizard (no admin rights needed). |
| **macOS 11+ (Apple Silicon)** | `kimbaview-…-macos-arm64.dmg` | Open it and drag `kimbaview` to “Applications”. |
| **Linux** | `kimbaview-…-linux.tar.gz` | Extract, then run `./install.sh` in the extracted folder (no root rights needed). |

MediaWiki files additionally need [Pandoc](https://pandoc.org/installing.html); Markdown works without it.

**Unsigned builds:** Windows may show “Windows protected your PC” → *More info → Run anyway*.
macOS reports that the app cannot be opened → *System Settings → Privacy & Security → “Open Anyway”*.

**Verify downloads:** `SHA256SUMS.txt` contains the checksums of all files. With the GitHub CLI you can also verify that a
file was built by this repository: `gh attestation verify <file> --repo <owner>/<repo>`.

---

## Deutsch

| System | Datei | Installation |
|---|---|---|
| **Windows 10/11** | `kimbaview-setup-….exe` | Ausführen und dem Assistenten folgen (keine Adminrechte nötig). |
| **macOS 11+ (Apple Silicon)** | `kimbaview-…-macos-arm64.dmg` | Öffnen und `kimbaview` auf „Programme“ ziehen. |
| **Linux** | `kimbaview-…-linux.tar.gz` | Entpacken, dann `./install.sh` im entpackten Ordner (ohne Root-Rechte). |

Für MediaWiki-Dateien wird zusätzlich [Pandoc](https://pandoc.org/installing.html) benötigt, Markdown geht auch ohne.

**Unsignierte Builds:** Windows zeigt ggf. „Der Computer wurde durch Windows geschützt“ → *Weitere Informationen → Trotzdem ausführen*.
macOS meldet, dass die App nicht geöffnet werden kann → *Systemeinstellungen → Datenschutz & Sicherheit → „Trotzdem öffnen“*.

**Echtheit prüfen:** `SHA256SUMS.txt` enthält die Prüfsummen aller Dateien. Mit der GitHub-CLI lässt sich zusätzlich nachweisen,
dass eine Datei von diesem Repository gebaut wurde: `gh attestation verify <datei> --repo <besitzer>/<repo>`.
