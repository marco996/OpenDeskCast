(() => {
  const I18N = {
    it: { name: "Italiano", setup: "Setup dispositivo", v1: "1 spettatore collegato", vN: "{0} spettatori collegati", qr: "QR Sicurezza Sessione", copied: "Link sicuro copiato!", rotate: "Rigenera QR / Disconnetti", src: "Sorgente", scr: "Schermo", pri: "Principale", sec: "Secondario", fps: "Fluidità", qual: "Qualità", scale: "Risoluzione", cur: "Mostra cursore del mouse", aud: "Trasmetti audio del PC", lock: "Blocca nuovi dispositivi (Rete Pubblica)", lockSub: "Impedisce nuovi collegamenti anche conoscendo l'IP" },
    en: { name: "English", setup: "Device setup", v1: "1 viewer connected", vN: "{0} viewers connected", qr: "Session Security QR", copied: "Secure link copied!", rotate: "Regenerate QR / Disconnect", src: "Source", scr: "Screen", pri: "Primary", sec: "Secondary", fps: "Frame Rate", qual: "Quality", scale: "Resolution", cur: "Show mouse cursor", aud: "Stream PC audio", lock: "Block new devices (Public Network)", lockSub: "Prevents new connections even if IP is known" },
    es: { name: "Español", setup: "Configurar dispositivo", v1: "1 espectador conectado", vN: "{0} espectadores conectados", qr: "QR de Seguridad", copied: "¡Enlace copiado!", rotate: "Regenerar QR / Desconectar", src: "Fuente", scr: "Pantalla", pri: "Principal", sec: "Secundaria", fps: "Fluidez", qual: "Calidad", scale: "Resolución", cur: "Mostrar cursor del ratón", aud: "Transmitir audio del PC", lock: "Bloquear nuevos dispositivos (Red Pública)", lockSub: "Impide nuevas conexiones aunque conozcan la IP" },
    fr: { name: "Français", setup: "Config. appareil", v1: "1 spectateur connecté", vN: "{0} spectateurs connectés", qr: "QR de Sécurité", copied: "Lien sécurisé copié !", rotate: "Régénérer QR / Déconnecter", src: "Source", scr: "Écran", pri: "Principal", sec: "Secondaire", fps: "Fluidité", qual: "Qualité", scale: "Résolution", cur: "Afficher le curseur de la souris", aud: "Diffuser l'audio du PC", lock: "Bloquer les nouveaux appareils (Réseau Public)", "lockSub": "Empêche toute nouvelle connexion même avec l'IP" },
    de: { name: "Deutsch", setup: "Gerät einrichten", v1: "1 Zuschauer verbunden", vN: "{0} Zuschauer verbunden", qr: "Sitzungs-QR-Code", copied: "Link kopiert!", rotate: "QR erneuern / Trennen", src: "Quelle", scr: "Bildschirm", pri: "Primär", sec: "Sekundär", fps: "Bildrate", qual: "Qualität", scale: "Auflösung", cur: "Mauszeiger anzeigen", aud: "PC-Audio übertragen", lock: "Neue Geräte blockieren (Öffentliches Netz)", lockSub: "Verhindert neue Verbindungen trotz bekannter IP" },
    pt: { name: "Português", setup: "Configurar dispositivo", v1: "1 espectador conectado", vN: "{0} espectadores conectados", qr: "QR de Segurança", copied: "Link copiado!", rotate: "Regenerar QR / Desconectar", src: "Fonte", scr: "Tela", pri: "Principal", sec: "Secundária", fps: "Fluidez", qual: "Qualidade", scale: "Resolução", cur: "Mostrar cursor do rato", aud: "Transmitir áudio do PC", lock: "Bloquear novos dispositivos (Rede Pública)", lockSub: "Impede novas conexões mesmo conhecendo o IP" },
    nl: { name: "Nederlands", setup: "Apparaat instellen", v1: "1 kijker verbonden", vN: "{0} kijkers verbonden", qr: "Sessiebeveiliging QR", copied: "Link gekopieerd!", rotate: "QR vernieuwen / Verbreken", src: "Bron", scr: "Scherm", pri: "Primair", sec: "Secundair", fps: "Soeplesse", qual: "Kwaliteit", scale: "Resolutie", cur: "Muisaanwijzer tonen", aud: "PC-audio streamen", lock: "Nieuwe apparaten blokkeren (Openbaar Netwerk)", lockSub: "Voorkomt nieuwe verbindingen zelfs met bekend IP" },
    pl: { name: "Polski", setup: "Konfig. urządzenia", v1: "1 widz połączony", vN: "{0} widzów połączonych", qr: "Kod QR Sesji", copied: "Link skopiowany!", rotate: "Odnowić QR / Rozłącz", src: "Źródło", scr: "Ekran", pri: "Główny", sec: "Dodatkowy", fps: "Płynność", qual: "Jakość", scale: "Rozdzielczość", cur: "Pokaż kursor myszy", aud: "Przesyłaj dźwięk z PC", lock: "Blokuj nowe urządzenia (Sieć Publiczna)", lockSub: "Uniemożliwia nowe połączenia nawet znając IP" },
    ro: { name: "Română", setup: "Config. dispozitiv", v1: "1 spectator conectat", vN: "{0} spectatori conectați", qr: "QR Securitate Sesiune", copied: "Link copiat!", rotate: "Regenerare QR / Deconectare", src: "Sursă", scr: "Ecran", pri: "Principal", sec: "Secundar", fps: "Fluiditate", qual: "Calitate", scale: "Rezoluție", cur: "Afișează cursorul mouse-ului", aud: "Transmite sunetul PC-ului", lock: "Blochează dispozitive noi (Rețea Publică)", lockSub: "Previene conexiuni noi chiar dacă IP-ul este cunoscut" },
    cs: { name: "Čeština", setup: "Nastavení zařízení", v1: "1 divák připojen", vN: "{0} diváků připojeno", qr: "Bezpečnostní QR", copied: "Odkaz zkopírován!", rotate: "Obnovit QR / Odpojit", src: "Zdroj", scr: "Obrazovka", pri: "Hlavní", sec: "Vedlejší", fps: "Plynulost", qual: "Kvalita", scale: "Rozlišení", cur: "Zobrazit kurzor myši", aud: "Přehrávat zvuk z PC", lock: "Blokovat nová zařízení (Veřejná síť)", lockSub: "Zabrání novým připojením i při znalosti IP" },
    hu: { name: "Magyar", setup: "Eszköz beállítása", v1: "1 néző csatlakozva", vN: "{0} néző csatlakozva", qr: "Munkamenet QR-kód", copied: "Hivatkozás másolva!", rotate: "Új QR / Szétkapcsolás", src: "Forrás", scr: "Képernyő", pri: "Elsődleges", sec: "Másodlagos", fps: "Képfrissítés", qual: "Minőség", scale: "Felbontás", cur: "Egérmutató megjelenítése", aud: "PC hangjának átvitele", lock: "Új eszközök tiltása (Nyilvános hálózat)", lockSub: "Megakadályozza az új kapcsolatokat ismert IP esetén is" },
    sv: { name: "Svenska", setup: "Enhetsinställning", v1: "1 tittare ansluten", vN: "{0} tittare anslutna", qr: "Sessions-QR-kod", copied: "Länk kopierad!", rotate: "Förnya QR / Koppla från", src: "Källa", scr: "Skärm", pri: "Primär", sec: "Sekundär", fps: "Bildfrekvens", qual: "Kvalitet", scale: "Upplösning", cur: "Visa muspekare", aud: "Strömma PC-ljud", lock: "Blockera nya enheter (Offentligt nät)", lockSub: "Förhindrar nya anslutningar även om IP är känt" },
    da: { name: "Dansk", setup: "Enhedsopsætning", v1: "1 seer forbundet", vN: "{0} seere forbundet", qr: "Sessions-QR-kode", copied: "Link kopieret!", rotate: "Forny QR / Afbryd", src: "Kilde", scr: "Skærm", pri: "Primær", sec: "Sekundær", fps: "Billedhastighed", qual: "Kvalitet", scale: "Opløsning", cur: "Vis musemarkør", aud: "Stream PC-lyd", lock: "Bloker nye enheder (Offentligt netværk)", lockSub: "Forhindrer nye forbindelser selv med kendt IP" },
    no: { name: "Norsk", setup: "Enhetsoppsett", v1: "1 seer tilkoblet", vN: "{0} seere tilkoblet", qr: "Øktsikkerhet QR", copied: "Lenke kopiert!", rotate: "Forny QR / Koble fra", src: "Kilde", scr: "Skjerm", pri: "Primær", sec: "Sekundær", fps: "Bildefrekvens", qual: "Kvalitet", scale: "Oppløsning", cur: "Vis musepeker", aud: "Strøm PC-lyd", lock: "Blokker nye enheter (Offentlig nettverk)", lockSub: "Hindrer nye tilkoblinger selv om IP er kjent" },
    fi: { name: "Suomi", setup: "Laitteen asennus", v1: "1 katsoja yhdistetty", vN: "{0} katsojaa yhdistetty", qr: "Istunnon QR-koodi", copied: "Linkki kopioitu!", rotate: "Uusi QR / Katkaise", src: "Lähde", scr: "Näyttö", pri: "Ensisijainen", sec: "Toissijainen", fps: "Sulavuus", qual: "Laatu", scale: "Tarkkuus", cur: "Näytä hiiren osoitin", aud: "Toista PC-ääni", lock: "Estä uudet laitteet (Julkinen verkko)", lockSub: "Estää uudet yhteydet vaikka IP tiedettäisiin" },
    el: { name: "Ελληνικά", setup: "Ρύθμιση συσκευής", v1: "1 θεατής συνδεδεμένος", vN: "{0} θεατές συνδεδεμένοι", qr: "QR Ασφαλείας", copied: "Ο σύνδεσμος αντιγράφηκε!", rotate: "Ανανέωση QR / Αποσύνδεση", src: "Πηγή", scr: "Οθόνη", pri: "Κύρια", sec: "Δευτερεύουσα", fps: "Ρυθμός καρέ", qual: "Ποιότητα", scale: "Ανάλυση", cur: "Εμφάνιση δείκτη ποντικιού", aud: "Μετάδοση ήχου PC", lock: "Φραγή νέων συσκευών (Δημόσιο Δίκτυο)", lockSub: "Εμποδίζει νέες συνδέσεις ακόμα κι αν είναι γνωστή η IP" },
    tr: { name: "Türkçe", setup: "Cihaz kurulumu", v1: "1 izleyici bağlı", vN: "{0} izleyici bağlı", qr: "Oturum Güvenlik QR", copied: "Bağlantı kopyalandı!", rotate: "QR Yenile / Bağlantıyı Kes", src: "Kaynak", scr: "Ekran", pri: "Birincil", sec: "İkincil", fps: "Akıcılık", qual: "Kalite", scale: "Çözünürlük", cur: "Fare imlecini göster", aud: "PC sesini aktar", lock: "Yeni cihazları engelle (Açık Ağ)", lockSub: "IP bilinse bile yeni bağlantıları engeller" },
    ru: { name: "Русский", setup: "Настройка устр-ва", v1: "1 зритель подключен", vN: "Зрителей подключено: {0}", qr: "QR безопасности сессии", copied: "Ссылка скопирована!", rotate: "Обновить QR / Отключить", src: "Источник", scr: "Экран", pri: "Основной", sec: "Второй", fps: "Плавность", qual: "Качество", scale: "Разрешение", cur: "Показывать курсор мыши", aud: "Передавать звук ПК", lock: "Блокировать новые устройства (Публичная сеть)", lockSub: "Запрещает новые подключения даже при известном IP" },
    uk: { name: "Українська", setup: "Налаштування", v1: "1 глядач підключений", vN: "Глядачів підключено: {0}", qr: "QR безпеки сесії", copied: "Посилання скопійовано!", rotate: "Оновити QR / Відключити", src: "Джерело", scr: "Екран", pri: "Основний", sec: "Другий", fps: "Плавність", qual: "Якість", scale: "Роздільність", cur: "Показувати курсор миші", aud: "Передавати звук ПК", lock: "Блокувати нові пристрої (Публічна мережа)", lockSub: "Забороняє нові підключення навіть за відомого IP" },
    ar: { name: "العربية", setup: "إعداد الجهاز", v1: "مشاهد واحد متصل", vN: "{0} مشاهدين متصلين", qr: "رمز QR لأمان الجلسة", copied: "تم نسخ الرابط!", rotate: "تجديد QR / قطع الاتصال", src: "المصدر", scr: "شاشة", pri: "رئيسية", sec: "ثانوية", fps: "السلاسة", qual: "الجودة", scale: "الدقة", cur: "إظهار مؤشر الفأرة", aud: "بث صوت الكمبيوتر", lock: "حظر الأجهزة الجديدة (شبكة عامة)", lockSub: "يمنع الاتصالات الجديدة حتى مع معرفة عنوان IP" },
    he: { name: "עברית", setup: "הגדרת מכשיר", v1: "צופה 1 מחובר", vN: "{0} צופים מחוברים", qr: "קוד QR לאבטחת הפעלה", copied: "הקישור הועתק!", rotate: "חדש QR / נתק", src: "מקור", scr: "מסך", pri: "ראשי", sec: "משני", fps: "קצב פריימים", qual: "איכות", scale: "רזולוציה", cur: "הצג סמן עכבר", aud: "הזרם שמע מהמחשב", lock: "חסום מכשירים חדשים (רשת ציבורית)", lockSub: "מונע חיבורים חדשים גם אם ה-IP ידוע" },
    hi: { name: "हिन्दी", setup: "डिवाइस सेटअप", v1: "1 दर्शक जुड़ा है", vN: "{0} दर्शक जुड़े हैं", qr: "सत्र सुरक्षा QR", copied: "लिंक कॉपी किया गया!", rotate: "नया QR / डिस्कनेक्ट", src: "स्रोत", scr: "स्क्रीन", pri: "मुख्य", sec: "द्वितीयक", fps: "फ़्रेम दर", qual: "गुणवत्ता", scale: "रेज़ोल्यूशन", cur: "माउस कर्सर दिखाएँ", aud: "पीसी ऑडियो स्ट्रीम करें", lock: "नए उपकरण ब्लॉक करें (सार्वजनिक नेटवर्क)", lockSub: "IP पता होने पर भी नए कनेक्शन रोकता है" },
    zh: { name: "中文 (简体)", setup: "设备连接设置", v1: "1 位观众已连接", vN: "{0} 位观众已连接", qr: "会话安全二维码", copied: "安全链接已复制！", rotate: "刷新二维码 / 断开全部", src: "画面源", scr: "屏幕", pri: "主屏", sec: "副屏", fps: "流畅度", qual: "画质", scale: "分辨率", cur: "显示鼠标指针", aud: "传输电脑音频", lock: "阻止新设备连接 (公共网络保护)", lockSub: "即使他人知道 IP 地址也无法建立新连接" },
    zt: { name: "中文 (繁體)", setup: "裝置連線設定", v1: "1 位觀眾已連線", vN: "{0} 位觀眾已連線", qr: "工作階段安全 QR", copied: "安全連結已複製！", rotate: "更新 QR / 中斷連線", src: "畫面來源", scr: "螢幕", pri: "主螢幕", sec: "副螢幕", fps: "流暢度", qual: "畫質", scale: "解析度", cur: "顯示滑鼠游標", aud: "傳送電腦音訊", lock: "封鎖新裝置 (公共網路保護)", lockSub: "即使知道 IP 位址也無法建立新連線" },
    ja: { name: "日本語", setup: "デバイス設定", v1: "1 人の視聴者が接続中", vN: "{0} 人の視聴者が接続中", qr: "セッション保護 QR", copied: "リンクをコピーしました！", rotate: "QR再生成 / 切断", src: "ソース", scr: "画面", pri: "メイン", sec: "サブ", fps: "フレームレート", qual: "画質", scale: "解像度", cur: "マウスカーソルを表示", aud: "PCの音声を送信", lock: "新規デバイスをブロック (公衆ネットワーク)", lockSub: "IPが知られていても新しい接続を拒否します" },
    ko: { name: "한국어", setup: "기기 연결 설정", v1: "시청자 1명 연결됨", vN: "시청자 {0}명 연결됨", qr: "세션 보안 QR 코드", copied: "보안 링크 복사됨!", rotate: "QR 재생성 / 연결 해제", src: "소스", scr: "화면", pri: "주 모니터", sec: "보조 모니터", fps: "프레임 속도", qual: "화질", scale: "해상도", cur: "마우스 커서 표시", aud: "PC 오디오 전송", lock: "새 기기 차단 (공용 네트워크)", lockSub: "IP를 알아도 새로운 연결을 차단합니다" },
    vi: { name: "Tiếng Việt", setup: "Thiết lập thiết bị", v1: "1 người xem đã kết nối", vN: "{0} người xem đã kết nối", qr: "Mã QR Bảo mật", copied: "Đã sao chép liên kết!", rotate: "Tạo lại QR / Ngắt kết nối", src: "Nguồn phát", scr: "Màn hình", pri: "Chính", sec: "Phụ", fps: "Độ mượt", qual: "Chất lượng", scale: "Độ phân giải", cur: "Hiện con trỏ chuột", aud: "Truyền âm thanh PC", lock: "Chặn thiết bị mới (Mạng công cộng)", lockSub: "Ngăn kết nối mới ngay cả khi biết IP" },
    id: { name: "Bahasa Indonesia", setup: "Setup perangkat", v1: "1 penonton terhubung", vN: "{0} penonton terhubung", qr: "QR Keamanan Sesi", copied: "Tautan disalin!", rotate: "Buat Ulang QR / Putuskan", src: "Sumber", scr: "Layar", pri: "Utama", sec: "Kedua", fps: "Kelancaran", qual: "Kualitas", scale: "Resolusi", cur: "Tampilkan kursor mouse", aud: "Kirim audio PC", lock: "Blokir perangkat baru (Jaringan Publik)", lockSub: "Mencegah koneksi baru meskipun IP diketahui" }
  };

  const qrImage = document.getElementById("qr-image");
  const pinBadge = document.getElementById("pin-badge");
  const primaryUrlBox = document.getElementById("primary-url");
  const viewersBadge = document.getElementById("viewers-badge");
  const statusDot = document.getElementById("status-dot");
  const selLang = document.getElementById("sel-lang");
  const btnHelp = document.getElementById("btn-help");
  const helpModal = document.getElementById("help-modal");
  const btnHelpClose = document.getElementById("btn-help-close");
  const helpTitle = document.getElementById("help-title");
  const helpBody = document.getElementById("help-body");

  const selMonitor = document.getElementById("sel-monitor");
  const selFps = document.getElementById("sel-fps");
  const selQuality = document.getElementById("sel-quality");
  const selScale = document.getElementById("sel-scale");
  const chkCursor = document.getElementById("chk-cursor");
  const chkAudio = document.getElementById("chk-audio");
  const chkLock = document.getElementById("chk-lock");
  const btnRefresh = document.getElementById("btn-refresh");
  const btnRotateToken = document.getElementById("btn-rotate-token");

  let currentLang = localStorage.getItem("opendeskcast_lang") || "it";
  if (!I18N[currentLang]) currentLang = "it";
  let lastCount = 0;
  let lastMonitors = [];
  let lastPin = "----";
  let lastBaseIpUrl = "http://127.0.0.1:8765";

  function renderHelpContent() {
    const isIt = currentLang === "it";
    if (btnHelp) btnHelp.textContent = t().setup;
    if (helpTitle) {
      helpTitle.textContent = isIt
        ? "Come collegare uno Spettatore"
        : "How to Connect a Viewer Device";
    }
    if (!helpBody) return;
    if (isIt) {
      helpBody.innerHTML = `
        <div class="help-step-box">
          <div class="help-step-title">1. Dispositivi con Fotocamera (QR Code)</div>
          <div>Inquadra direttamente il <b>QR Code</b> con la fotocamera del tablet o dello smartphone: lo schermo del PC comparirà subito a tutto schermo senza digitare codici.</div>
        </div>
        <div class="help-step-box">
          <div class="help-step-title">2. Dispositivi SENZA Fotocamera (Indirizzo IP + PIN a 4 cifre)</div>
          <div>• Apri il browser del dispositivo e vai su <b>${lastBaseIpUrl}</b><br/>
          • <i>Consiglio:</i> Salva l'indirizzo nei <b>Preferiti</b> o aggiungilo alla schermata Home per aprirlo con un tocco.<br/>
          • Sullo schermo comparirà un tastierino: inserisci il <b>PIN di 4 cifre</b> mostrato sotto il QR (attuale: <b>${lastPin}</b>) e la trasmissione partirà all'istante.</div>
        </div>
        <div class="help-step-box">
          <div class="help-step-title">3. Sicurezza e Disconnessione</div>
          <div>Il QR Code e il PIN cambiano automaticamente ad ogni avvio del programma o premendo <b>"${t().rotate}"</b>, scollegando subito tutti i dispositivi.</div>
        </div>`;
    } else {
      helpBody.innerHTML = `
        <div class="help-step-box">
          <div class="help-step-title">1. Devices with Camera (QR Code)</div>
          <div>Scan the <b>QR Code</b> with your device camera: the PC screen will appear immediately in fullscreen without typing any code.</div>
        </div>
        <div class="help-step-box">
          <div class="help-step-title">2. Devices WITHOUT Camera (IP Address + 4-Digit PIN)</div>
          <div>• Open the browser on your device and go to <b>${lastBaseIpUrl}</b><br/>
          • <i>Tip:</i> Bookmark this address so you never have to type it again.<br/>
          • Enter the <b>4-digit PIN</b> displayed under the QR code (current: <b>${lastPin}</b>) on the on-screen keypad to start viewing immediately.</div>
        </div>
        <div class="help-step-box">
          <div class="help-step-title">3. Security & Disconnect</div>
          <div>Both the QR Code and the 4-digit PIN automatically rotate every time OpenDeskCast closes or when you click <b>"${t().rotate}"</b>.</div>
        </div>`;
    }
  }

  Object.keys(I18N).forEach((code) => {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = I18N[code].name;
    if (code === currentLang) opt.selected = true;
    selLang.appendChild(opt);
  });

  function t() {
    return I18N[currentLang] || I18N.it;
  }

  function updateViewersBadge(count) {
    lastCount = count;
    const dict = t();
    viewersBadge.textContent = count === 1 ? dict.v1 : dict.vN.replace("{0}", String(count));
    statusDot.classList.toggle("active", count > 0);
  }

  function renderMonitorOptions(currentMon) {
    const dict = t();
    selMonitor.innerHTML = "";
    lastMonitors.forEach((m) => {
      const opt = document.createElement("option");
      opt.value = String(m.id);
      const role = m.is_primary ? dict.pri : dict.sec;
      opt.textContent = `${dict.scr} ${m.id + 1} (${role} - ${m.width}x${m.height})`;
      if (m.id === currentMon) opt.selected = true;
      selMonitor.appendChild(opt);
    });
  }

  function applyTranslations() {
    const dict = t();
    document.getElementById("lbl-qr-title").textContent = dict.qr;
    btnRotateToken.textContent = dict.rotate;
    document.getElementById("lbl-source").textContent = dict.src;
    document.getElementById("lbl-fps").textContent = dict.fps;
    document.getElementById("lbl-quality").textContent = dict.qual;
    document.getElementById("lbl-scale").textContent = dict.scale;
    document.getElementById("lbl-cursor").textContent = dict.cur;
    document.getElementById("lbl-audio").textContent = dict.aud;
    document.getElementById("lbl-lock").textContent = dict.lock;
    document.getElementById("lbl-lock-sub").textContent = dict.lockSub;
    updateViewersBadge(lastCount);
    const curMon = parseInt(selMonitor.value, 10) || 0;
    renderMonitorOptions(curMon);
    renderHelpContent();
  }

  if (btnHelp && helpModal) {
    btnHelp.addEventListener("click", () => {
      renderHelpContent();
      helpModal.classList.remove("hidden");
      btnHelp.blur();
    });
  }
  if (btnHelpClose && helpModal) {
    btnHelpClose.addEventListener("click", () => {
      helpModal.classList.add("hidden");
    });
    helpModal.addEventListener("click", (e) => {
      if (e.target === helpModal) helpModal.classList.add("hidden");
    });
  }

  selLang.addEventListener("change", () => {
    currentLang = selLang.value;
    localStorage.setItem("opendeskcast_lang", currentLang);
    applyTranslations();
    selLang.blur();
  });

  async function loadStatus() {
    try {
      const port = window.location.port || "8765";
      const res = await fetch(`/api/status?port=${port}`);
      if (!res.ok) return;
      const data = await res.json();

      updateViewersBadge(data.connected_viewers || 0);

      lastPin = data.session_pin || "----";
      lastBaseIpUrl = data.base_url || `http://127.0.0.1:${port}`;
      if (pinBadge) pinBadge.textContent = `PIN: ${lastPin}`;

      const primaryUrl = data.urls[0] || `http://127.0.0.1:${port}`;
      primaryUrlBox.textContent = lastBaseIpUrl;
      primaryUrlBox.setAttribute("data-copy", lastBaseIpUrl);
      if (qrImage.getAttribute("data-url") !== primaryUrl) {
        qrImage.src = `/api/qr.svg?url=${encodeURIComponent(primaryUrl)}`;
        qrImage.setAttribute("data-url", primaryUrl);
      }
      renderHelpContent();

      lastMonitors = data.monitors || [];
      renderMonitorOptions(data.settings.monitor_id);

      selFps.value = String(data.settings.fps);
      selQuality.value = String(data.settings.quality);
      selScale.value = String(data.settings.scale);
      chkCursor.checked = Boolean(data.settings.draw_cursor);
      chkAudio.checked = Boolean(data.settings.audio_enabled);
      chkLock.checked = Boolean(data.settings.lock_new_viewers);
    } catch (_) {}
  }

  async function pushSettings() {
    try {
      await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          monitor_id: parseInt(selMonitor.value, 10) || 0,
          fps: parseInt(selFps.value, 10) || 30,
          quality: parseInt(selQuality.value, 10) || 75,
          scale: parseFloat(selScale.value) || 1.0,
          draw_cursor: chkCursor.checked,
          audio_enabled: chkAudio.checked,
          lock_new_viewers: chkLock.checked,
        }),
      });
    } catch (_) {}
  }

  async function rotateToken() {
    try {
      await fetch("/api/rotate-token", { method: "POST" });
      await loadStatus();
    } catch (_) {}
  }

  primaryUrlBox.addEventListener("click", () => {
    const txt = primaryUrlBox.getAttribute("data-copy") || primaryUrlBox.textContent || "";
    if (navigator.clipboard && txt) {
      navigator.clipboard.writeText(txt).catch(() => {});
      const prev = primaryUrlBox.textContent;
      primaryUrlBox.textContent = t().copied;
      setTimeout(() => {
        primaryUrlBox.textContent = prev;
      }, 1000);
    }
  });

  selMonitor.addEventListener("change", pushSettings);
  selFps.addEventListener("change", pushSettings);
  selQuality.addEventListener("change", pushSettings);
  selScale.addEventListener("change", pushSettings);
  chkCursor.addEventListener("change", pushSettings);
  chkAudio.addEventListener("change", pushSettings);
  chkLock.addEventListener("change", pushSettings);
  btnRefresh.addEventListener("click", loadStatus);
  btnRotateToken.addEventListener("click", rotateToken);

  window.addEventListener("pagehide", () => {
    if (navigator.sendBeacon) {
      navigator.sendBeacon("/api/window-closed");
    }
  });

  setInterval(async () => {
    try {
      fetch("/api/heartbeat", { method: "POST" }).catch(() => {});
      const port = window.location.port || "8765";
      const res = await fetch(`/api/status?port=${port}`);
      if (!res.ok) return;
      const data = await res.json();
      updateViewersBadge(data.connected_viewers || 0);

      const newPin = data.session_pin || "----";
      const newBase = data.base_url || `http://127.0.0.1:${port}`;
      const primaryUrl = (data.urls && data.urls[0]) || `http://127.0.0.1:${port}`;

      if (newPin !== lastPin || newBase !== lastBaseIpUrl) {
        lastPin = newPin;
        lastBaseIpUrl = newBase;
        if (pinBadge) pinBadge.textContent = `PIN: ${lastPin}`;
        primaryUrlBox.textContent = lastBaseIpUrl;
        primaryUrlBox.setAttribute("data-copy", lastBaseIpUrl);
        renderHelpContent();
      }
      if (qrImage.getAttribute("data-url") !== primaryUrl) {
        qrImage.src = `/api/qr.svg?url=${encodeURIComponent(primaryUrl)}`;
        qrImage.setAttribute("data-url", primaryUrl);
      }
    } catch (_) {}
  }, 2000);

  applyTranslations();
  loadStatus();
})();
