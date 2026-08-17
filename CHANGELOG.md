# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.0.0/).

## [0.2.0] - 2026-08-16
### Añadido
- Panel de ajustes con sliders: tempo, pulsación, pausa por línea, humanización, transposición y cuenta atrás.
- Tempo modificable en vivo mientras se reproduce.
- Transposición cromática en semitonos (descarta notas fuera de rango).
- Humanización: jitter aleatorio por nota.
- Botones Pegar / Limpiar / Abrir .txt y contador de notas en tiempo real.
- Guardado y carga de configuración (`autoplayer_config.json`).

## [0.1.0] - 2026-08-16
### Añadido
- Parser del formato Virtual Piano (acordes, notas pegadas, símbolos con Shift).
- Envío de teclas por SendInput con scancodes físicos.
- Interfaz tkinter básica con tempo, pulsación, pausa y cuenta atrás.
- Hotkeys globales F5 / F6 / F7.
- Script de compilación a .exe con PyInstaller.
