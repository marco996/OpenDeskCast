# OpenDeskCast

OpenDeskCast è un'applicazione open source multipiattaforma (Windows, Linux, macOS) pensata per la trasmissione dello schermo da un computer verso qualsiasi dispositivo dotato di browser web moderno (Chrome, Safari, Edge, Firefox, Brave).

---

## Caratteristiche Principali

- **Zero installazione per lo spettatore**: Lo spettatore deve solo inquadrare il QR oppure raggiungere l'indirizzo IP locale indicato nell'interfaccia.
- **Controllo Totale dal PC**: Tutte le impostazioni (scelta del monitor, FPS, qualità, attivazione audio) sono regolate esclusivamente dal PC trasmittente. Lo spettatore è uno schermo passivo come quando si utilizza un cavo HDMI.
- **Supporto Multi-Monitor Reale**: Riconosce e seleziona individualmente ciascun monitor fisico collegato al PC.
- **Streaming Audio Sincronizzato**: Quando l'audio è attivo dal PC, il flusso audio di sistema viene instradato verso la trasmissione e le casse locali del PC vengono silenziate; disattivando l'audio, gli altoparlanti locali tornano immediatamente attivi.
- **Sicurezza dagli spettatori non desiderati**: Accesso protetto tramite QR Code con token crittografico o digitazione manuale di un PIN a 4 cifre.
- **Pannello di Regia Riservato a Localhost**: Le API amministrative e il pannello di controllo sono inaccessibili dalla rete esterna, garantendo la totale riservatezza della regia.
- **Pacchetto Standalone Zero-Dipendenze**: Nessuna necessità di installare Python, .NET o runtime esterni per l'utente finale.

---

## Installazione ed Esecuzione

### Windows
1. Scarica direttamente l'installer [**`OpenDeskCast-v1.0.0-windows-x64.msi`**](https://github.com/marco996/OpenDeskCast/releases/download/v1.0.0/OpenDeskCast-v1.0.0-windows-x64.msi) (oppure consulta la pagina delle [Release](https://github.com/marco996/OpenDeskCast/releases)).
2. Avvia l'installer: crea automaticamente il collegamento nel Menu Start e sul Desktop.
3. Fai doppio clic su **OpenDeskCast**: si apre la finestra di regia e viene visualizzato il QR Code per connettere gli spettatori.

### Linux (Ubuntu / Debian / Mint)
1. Scarica direttamente il pacchetto [**`opendeskcast_1.0.0_amd64.deb`**](https://github.com/marco996/OpenDeskCast/releases/download/v1.0.0/opendeskcast_1.0.0_amd64.deb) (oppure consulta la pagina delle [Release](https://github.com/marco996/OpenDeskCast/releases)).
2. Installa con un solo comando da terminale (installa automaticamente anche le dipendenze di sistema):
   ```bash
   sudo apt install ./opendeskcast_1.0.0_amd64.deb
   ```
3. Avvia **OpenDeskCast** dal menù delle applicazioni del tuo computer o digitando `opendeskcast` nel terminale.

*(In alternativa, per avvio rapido da sorgente su qualsiasi distribuzione Linux: `./run_linux.sh`)*

### macOS
1. Scarica direttamente il pacchetto [**`OpenDeskCast-v1.0.0-macos.zip`**](https://github.com/marco996/OpenDeskCast/releases/download/v1.0.0/OpenDeskCast-v1.0.0-macos.zip) (oppure consulta la pagina delle [Release](https://github.com/marco996/OpenDeskCast/releases)).
2. Estrai il file zip e trascina **OpenDeskCast.app** nella cartella **Applicazioni**.
3. Avvia **OpenDeskCast** dal Launchpad o da Applicazioni.

*(In alternativa, per avvio rapido da sorgente su macOS: `./run_macos.sh`)*

---

## Licenza / License

Distribuito sotto licenza **MIT**. Consulta il file [LICENSE](LICENSE) per i dettagli completi.
