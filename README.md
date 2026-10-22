# OpenDeskCast

> **Trasmetti lo schermo del PC a qualsiasi smartphone, tablet o browser nella stessa rete locale, istantaneamente e senza installare app sul dispositivo ricevente.**

OpenDeskCast è un'applicazione open source multipiattaforma (Windows, Linux, macOS) progettata per la trasmissione ultra-reattiva dello schermo da un computer verso qualsiasi dispositivo dotato di browser web moderno (Chrome, Safari, Edge, Firefox).

---

## Caratteristiche Principali

- **Zero Installazione per lo Spettatore**: Funziona su qualsiasi dispositivo (iOS, Android, Windows, Mac, Linux) tramite un semplice browser web (PWA nativa).
- **Controllo Totale dal PC**: Tutte le impostazioni (scelta del monitor, FPS, qualità, attivazione audio) sono regolate esclusivamente dal PC trasmittente. Lo spettatore è uno schermo passivo tipo cavo HDMI.
- **Supporto Multi-Monitor Reale**: Riconosce e seleziona individualmente ciascun monitor fisico collegato al PC.
- **Streaming Audio Sincronizzato**: Quando l'audio è attivo dal PC, il flusso audio di sistema viene instradato verso la trasmissione e le casse locali del PC vengono silenziate; disattivando l'audio, gli altoparlanti locali tornano immediatamente attivi.
- **Sicurezza Nativa a Doppio Livello**: Accesso protetto tramite QR Code con token crittografico o digitazione manuale di un PIN a 4 cifre.
- **Pannello di Regia Riservato a Localhost**: Le API amministrative e il pannello di controllo sono inaccessibili dalla rete esterna, garantendo la totale riservatezza della regia.
- **Pacchetto Standalone Zero-Dipendenze**: Nessuna necessità di installare Python, .NET o runtime esterni per l'utente finale.

---

## Installazione ed Esecuzione

### Windows
1. Scarica l'installer `.msi` o `.exe` dalla pagina delle [Release](https://github.com/marco996/OpenDeskCast/releases).
2. Avvia l'installer: crea automaticamente il collegamento nel Menu Start e sul Desktop.
3. Fai doppio clic su **OpenDeskCast**: si apre la finestra di regia e viene visualizzato il QR Code per connettere gli spettatori.

### Linux (Ubuntu / Debian / Mint)
1. Scarica il pacchetto **`opendeskcast_1.0.0_amd64.deb`** dalla pagina delle [Release](https://github.com/marco996/OpenDeskCast/releases).
2. Installa con un solo comando da terminale (installa automaticamente anche le dipendenze di sistema):
   ```bash
   sudo apt install ./opendeskcast_1.0.0_amd64.deb
   ```
3. Avvia **OpenDeskCast** dal menù delle applicazioni del tuo computer o digitando `opendeskcast` nel terminale.

*(In alternativa, per avvio rapido da sorgente su qualsiasi distribuzione Linux: `./run_linux.sh`)*

---

## Compilazione dei Pacchetti Autonomi (Release Build)

Per generare i pacchetti autonomi per gli utenti finali dal codice sorgente:

```powershell
# 1. Installa le dipendenze di build
python -m pip install -r requirements.txt

# 2. Genera il pacchetto autonomo per il sistema operativo corrente (in dist/)
python scripts/build_package.py

# 3. Genera il pacchetto installer MSI per Windows (richiede WiX v4)
python scripts/build_msi.py

# 4. Genera il pacchetto Debian (.deb) per Linux
python scripts/build_deb.py
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
│   ├── build_package.py  # Pipeline di compilazione pacchetti autonomi (PyInstaller + C#)
│   └── build_msi.py      # Generatore pacchetto installer nativo Windows (.msi) con WiX v4
├── launcher.cs           # Interfaccia nativa Windows Fluent Dark (OpenDeskCast.exe)
├── install_windows.bat   # Script di installazione automatica per Windows
├── start_windows.bat     # Script di avvio universale per Windows
├── run_linux.sh          # Script di avvio automatico per Linux
├── run.py                # Entrypoint multipiattaforma del server
├── requirements.txt      # Dipendenze Python
├── VERSION               # Versione semantica del rilascio
└── LICENSE               # Licenza MIT
```

---

## Licenza / License

Distribuito sotto licenza **MIT**. Consulta il file [LICENSE](LICENSE) per i dettagli completi.
