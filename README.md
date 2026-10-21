# OpenDeskCast

**OpenDeskCast** è un software leggero, autonomo e ad altissime prestazioni per trasmettere in tempo reale lo schermo del PC verso qualsiasi dispositivo sulla rete locale (tablet, smartphone, altri computer o smart TV) tramite un comune browser web, senza installare alcuna app sugli spettatori.

**OpenDeskCast** is a lightweight, standalone, ultra-low-latency local screen-casting utility that streams your PC display to any device on your local network (tablets, phones, laptops, smart TVs) over a standard web browser — zero client apps required.

---

## Caratteristiche Principali / Key Features

- **Latenza Ultra-Bassa (Real-Time Delta Streaming)**:
  - Cattura nativa Win32 GDI con `HBITMAP` persistente su Windows (e fallback `mss` su Linux/macOS).
  - Codifica differenziale **Delta Bounding-Box** (`<HHHH`): trasmette solo il rettangolo dello schermo effettivamente cambiato, riducendo fino al 90% il traffico Wi-Fi durante la scrittura o l'uso di presentazioni.
  - Controllo di flusso adattivo **Client-Paced (`1-frame-in-flight`)**: zero code TCP o ritardi cumulativi anche su tablet meno recenti, fino a **60 FPS** e **Qualità 100% (4:4:4)**.
- **Doppio Metodo di Collegamento Sicuro**:
  1. **Dispositivi con Fotocamera (QR Code)**: inquadra il QR Code mostrato nella finestra di OpenDeskCast per aprire istantaneamente lo schermo a tutto schermo con token crittografico effimero.
  2. **Dispositivi senza Fotocamera (IP Base + PIN a 4 cifre)**: apri l'indirizzo IP base mostrato sotto il QR Code (es. `http://192.168.1.x:8765`, salvabile nei Preferiti) e digita sul tastierino a schermo il **PIN a 4 cifre**.
- **Sicurezza per Reti Pubbliche / Universitarie**:
  - Pulsante **Rigenera QR / Disconnetti** per invalidare istantaneamente il QR e il PIN correnti ed espellere tutti gli spettatori.
  - Interruttore **Blocca nuovi dispositivi (Rete Pubblica)** per rifiutare qualsiasi nuovo accesso una volta collegati i propri dispositivi.
  - Aggiornamento dinamico automatico dell'indirizzo IP e del QR Code in tempo reale se il PC cambia rete Wi-Fi o hotspot.
- **28 Lingue Integrate**: interfaccia tradotta in 28 lingue selezionabili al volo.
- **100% Standalone (Zero Dipendenza da Python)**: i pacchetti precompilati includono già il runtime isolato (`engine/`) e non richiedono Python installato sul PC dell'utente.

---

## Utilizzo Rapido / Quick Start

### 1. Da Pacchetto Standalone (Consigliato / Recommended)
1. Scarica ed estrai l'archivio per il tuo sistema operativo dalla sezione **Releases** (`OpenDeskCast-v1.0.0-windows-x64.zip`, `linux-x64.tar.gz`, `macos.zip`).
2. Avvia **`OpenDeskCast.exe`** (su Windows) o `./OpenDeskCast` (su Linux/macOS).
3. *Nota Firewall Windows*: al primo avvio, consenti l'accesso a `OpenDeskCastEngine` su **Reti private** e **Reti pubbliche** nella finestra di Windows Defender Firewall.
4. Collega uno o più spettatori:
   - **Con fotocamera**: inquadra il QR Code.
   - **Senza fotocamera**: clicca su **Setup dispositivo** per le istruzioni, apri nel browser l'indirizzo `http://<IP>:8765` indicato sotto il QR e inserisci il **PIN a 4 cifre**.

---

## Compilazione da Sorgente / Building from Source

Se desideri eseguire i test o generare i pacchetti standalone autonomi a partire dal codice sorgente:

```powershell
# 1. Installa le dipendenze di compilazione
python -m pip install -r requirements.txt

# 2. Esegui la suite di test unitari
python -m pytest -v

# 3. Genera il pacchetto autonomo per il sistema operativo corrente (in dist/)
python scripts/build_package.py

# 4. Verifica il pacchetto in un ambiente temporaneo isolato privo di Python nel PATH
python scripts/verify_clean_env.py
```

---

## Struttura del Progetto / Project Structure

```text
OpenDeskCast/
├── app/
│   ├── __init__.py
│   ├── audio.py          # Streaming audio PCM a bassa latenza (DirectShow / PulseAudio / AVFoundation)
│   ├── capture.py        # Cattura multi-monitor (Win32 GDI BitBlt / mss) + codifica Delta Bounding-Box
│   ├── qr_svg.py         # Generatore QR Code ISO/IEC 18004 nativo zero-dependency
│   └── server.py         # Server FastAPI + WebSocket binario con controllo di flusso client-paced
├── static/
│   ├── admin.html        # Pannello di controllo web multipiattaforma
│   ├── admin.js          # Logica pannello di controllo e 28 traduzioni
│   ├── client.js         # Motore Canvas 2D ad accelerazione hardware e tastierino PIN per spettatori
│   ├── index.html        # Pagina spettatore fullscreen (PWA)
│   └── style.css         # Stile Fluent Dark
├── scripts/
│   ├── build_package.py  # Pipeline ripetibile di compilazione pacchetti autonomi (PyInstaller + C#)
│   └── verify_clean_env.py # Test automatico del pacchetto su ambiente pulito senza Python nel PATH
├── tests/                # Suite di test automatizzati (pytest)
├── launcher.cs           # Interfaccia nativa Windows Fluent Dark (OpenDeskCast.exe)
├── run.py                # Entrypoint multipiattaforma del server
├── requirements.txt      # Dipendenze per lo sviluppo e il packaging
├── VERSION               # Versione semantica del rilascio
└── LICENSE               # Licenza MIT
```

---

## Licenza / License

Distribuito sotto licenza **MIT**. Consulta il file [LICENSE](LICENSE) per i dettagli completi.
