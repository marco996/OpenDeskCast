using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

[assembly: AssemblyTitle("OpenDeskCast")]
[assembly: AssemblyDescription("OpenDeskCast — High-Performance Local Screen Casting Server")]
[assembly: AssemblyProduct("OpenDeskCast")]
[assembly: AssemblyCopyright("Copyright (c) 2026 OpenDeskCast Contributors — MIT License")]
[assembly: AssemblyVersion("1.0.0.0")]
[assembly: AssemblyFileVersion("1.0.0.0")]

namespace OpenDeskCastLauncher
{
    internal sealed class LangPack
    {
        public string Code;
        public string Name;
        public string SetupBtn;
        public string V1;
        public string VN;
        public string QrTitle;
        public string Copied;
        public string RotateBtn;
        public string Source;
        public string ScreenWord;
        public string PrimaryWord;
        public string SecondaryWord;
        public string Fps;
        public string Quality;
        public string Scale;
        public string Cursor;
        public string Audio;
        public string LockTitle;
        public string LockSub;

        public LangPack(
            string code, string name, string setupBtn, string v1, string vN, string qrTitle, string copied,
            string rotateBtn, string source, string screenWord, string primaryWord, string secondaryWord,
            string fps, string quality, string scale,
            string cursor, string audio, string lockTitle, string lockSub)
        {
            Code = code; Name = name; SetupBtn = setupBtn; V1 = v1; VN = vN; QrTitle = qrTitle; Copied = copied;
            RotateBtn = rotateBtn; Source = source; ScreenWord = screenWord;
            PrimaryWord = primaryWord; SecondaryWord = secondaryWord;
            Fps = fps; Quality = quality;
            Scale = scale; Cursor = cursor; Audio = audio;
            LockTitle = lockTitle; LockSub = lockSub;
        }
    }

    internal sealed class MonitorMeta
    {
        public int Id;
        public int Width;
        public int Height;
        public bool IsPrimary;
    }

    internal sealed class FluentToggle : Control
    {
        private bool _checked;
        public event EventHandler CheckedChanged;

        public bool Checked
        {
            get { return _checked; }
            set
            {
                if (_checked != value)
                {
                    _checked = value;
                    Invalidate();
                    if (CheckedChanged != null) CheckedChanged(this, EventArgs.Empty);
                }
            }
        }

        public void SetCheckedSilent(bool value)
        {
            if (_checked != value)
            {
                _checked = value;
                Invalidate();
            }
        }

        public FluentToggle()
        {
            SetStyle(
                ControlStyles.AllPaintingInWmPaint |
                ControlStyles.OptimizedDoubleBuffer |
                ControlStyles.ResizeRedraw |
                ControlStyles.UserPaint |
                ControlStyles.SupportsTransparentBackColor,
                true
            );
            Size = new Size(42, 20);
            Cursor = Cursors.Hand;
            BackColor = Color.FromArgb(39, 39, 39);
        }

        protected override void OnClick(EventArgs e)
        {
            base.OnClick(e);
            Checked = !Checked;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            g.Clear(BackColor);

            Rectangle rect = new Rectangle(0, 0, Width - 1, Height - 1);
            using (GraphicsPath path = RoundedRect(rect, Height / 2))
            {
                Color fill = _checked ? Color.FromArgb(76, 194, 255) : Color.FromArgb(58, 58, 58);
                Color border = _checked ? Color.FromArgb(76, 194, 255) : Color.FromArgb(98, 98, 98);
                using (SolidBrush b = new SolidBrush(fill))
                {
                    g.FillPath(b, path);
                }
                using (Pen p = new Pen(border, 1f))
                {
                    g.DrawPath(p, path);
                }
            }

            int knobX = _checked ? Width - 16 : 4;
            Color knobColor = _checked ? Color.FromArgb(18, 18, 18) : Color.FromArgb(215, 215, 215);
            using (SolidBrush kb = new SolidBrush(knobColor))
            {
                g.FillEllipse(kb, knobX, 4, 12, 12);
            }
        }

        private static GraphicsPath RoundedRect(Rectangle b, int r)
        {
            int d = r * 2;
            GraphicsPath path = new GraphicsPath();
            path.AddArc(b.X, b.Y, d, d, 180, 90);
            path.AddArc(b.Right - d, b.Y, d, d, 270, 90);
            path.AddArc(b.Right - d, b.Bottom - d, d, d, 0, 90);
            path.AddArc(b.X, b.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    internal sealed class FluentCard : Panel
    {
        public FluentCard()
        {
            SetStyle(
                ControlStyles.AllPaintingInWmPaint |
                ControlStyles.OptimizedDoubleBuffer |
                ControlStyles.ResizeRedraw |
                ControlStyles.UserPaint,
                true
            );
            BackColor = Color.FromArgb(39, 39, 39);
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            using (Pen borderPen = new Pen(Color.FromArgb(56, 56, 56), 1f))
            {
                e.Graphics.DrawRectangle(borderPen, 0, 0, Width - 1, Height - 1);
            }
        }
    }

    internal sealed class MainForm : Form
    {
        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int attrValue, int attrSize);

        private static readonly LangPack[] Languages = new LangPack[]
        {
            new LangPack("it", "Italiano", "Setup dispositivo", "1 spettatore collegato", "{0} spettatori collegati", "QR Sicurezza Sessione", "Link sicuro copiato!", "Rigenera QR / Disconnetti", "Sorgente", "Schermo", "Principale", "Secondario", "Fluidità", "Qualità", "Risoluzione", "Mostra cursore del mouse", "Trasmetti audio del PC", "Blocca nuovi dispositivi (Rete Pubblica)", "Impedisce nuovi collegamenti anche conoscendo l'IP"),
            new LangPack("en", "English", "Device setup", "1 viewer connected", "{0} viewers connected", "Session Security QR", "Secure link copied!", "Regenerate QR / Disconnect", "Source", "Screen", "Primary", "Secondary", "Frame Rate", "Quality", "Resolution", "Show mouse cursor", "Stream PC audio", "Block new devices (Public Network)", "Prevents new connections even if IP is known"),
            new LangPack("es", "Español", "Configurar dispositivo", "1 espectador conectado", "{0} espectadores conectados", "QR de Seguridad", "¡Enlace copiado!", "Regenerar QR / Desconectar", "Fuente", "Pantalla", "Principal", "Secundaria", "Fluidez", "Calidad", "Resolución", "Mostrar cursor del ratón", "Transmitir audio del PC", "Bloquear nuevos dispositivos (Red Pública)", "Impide nuevas conexiones aunque conozcan la IP"),
            new LangPack("fr", "Français", "Config. appareil", "1 spectateur connecté", "{0} spectateurs connectés", "QR de Sécurité", "Lien sécurisé copié !", "Régénérer QR / Déconnecter", "Source", "Écran", "Principal", "Secondaire", "Fluidité", "Qualité", "Résolution", "Afficher le curseur de la souris", "Diffuser l'audio du PC", "Bloquer les nouveaux appareils (Réseau Public)", "Empêche toute nouvelle connexion même avec l'IP"),
            new LangPack("de", "Deutsch", "Gerät einrichten", "1 Zuschauer verbunden", "{0} Zuschauer verbunden", "Sitzungs-QR-Code", "Link kopiert!", "QR erneuern / Trennen", "Quelle", "Bildschirm", "Primär", "Sekundär", "Bildrate", "Qualität", "Auflösung", "Mauszeiger anzeigen", "PC-Audio übertragen", "Neue Geräte blockieren (Öffentliches Netz)", "Verhindert neue Verbindungen trotz bekannter IP"),
            new LangPack("pt", "Português", "Configurar dispositivo", "1 espectador conectado", "{0} espectadores conectados", "QR de Segurança", "Link copiado!", "Regenerar QR / Desconectar", "Fonte", "Tela", "Principal", "Secundária", "Fluidez", "Qualidade", "Resolução", "Mostrar cursor do rato", "Transmitir áudio do PC", "Bloquear novos dispositivos (Rede Pública)", "Impede novas conexões mesmo conhecendo o IP"),
            new LangPack("nl", "Nederlands", "Apparaat instellen", "1 kijker verbonden", "{0} kijkers verbonden", "Sessiebeveiliging QR", "Link gekopieerd!", "QR vernieuwen / Verbreken", "Bron", "Scherm", "Primair", "Secundair", "Soeplesse", "Kwaliteit", "Resolutie", "Muisaanwijzer tonen", "PC-audio streamen", "Nieuwe apparaten blokkeren (Openbaar Netwerk)", "Voorkomt nieuwe verbindingen zelfs met bekend IP"),
            new LangPack("pl", "Polski", "Konfig. urządzenia", "1 widz połączony", "{0} widzów połączonych", "Kod QR Sesji", "Link skopiowany!", "Odnów QR / Rozłącz", "Źródło", "Ekran", "Główny", "Dodatkowy", "Płynność", "Jakość", "Rozdzielczość", "Pokaż kursor myszy", "Przesyłaj dźwięk z PC", "Blokuj nowe urządzenia (Sieć Publiczna)", "Uniemożliwia nowe połączenia nawet znając IP"),
            new LangPack("ro", "Română", "Config. dispozitiv", "1 spectator conectat", "{0} spectatori conectați", "QR Securitate Sesiune", "Link copiat!", "Regenerare QR / Deconectare", "Sursă", "Ecran", "Principal", "Secundar", "Fluiditate", "Calitate", "Rezoluție", "Afișează cursorul mouse-ului", "Transmite sunetul PC-ului", "Blochează dispozitive noi (Rețea Publică)", "Previene conexiuni noi chiar dacă IP-ul este cunoscut"),
            new LangPack("cs", "Čeština", "Nastavení zařízení", "1 divák připojen", "{0} diváků připojeno", "Bezpečnostní QR", "Odkaz zkopírován!", "Obnovit QR / Odpojit", "Zdroj", "Obrazovka", "Hlavní", "Vedlejší", "Plynulost", "Kvalita", "Rozlišení", "Zobrazit kurzor myši", "Přehrávat zvuk z PC", "Blokovat nová zařízení (Veřejná síť)", "Zabrání novým připojením i při znalosti IP"),
            new LangPack("hu", "Magyar", "Eszköz beállítása", "1 néző csatlakozva", "{0} néző csatlakozva", "Munkamenet QR-kód", "Hivatkozás másolva!", "Új QR / Szétkapcsolás", "Forrás", "Képernyő", "Elsődleges", "Másodlagos", "Képfrissítés", "Minőség", "Felbontás", "Egérmutató megjelenítése", "PC hangjának átvitele", "Új eszközök tiltása (Nyilvános hálózat)", "Megakadályozza az új kapcsolatokat ismert IP esetén is"),
            new LangPack("sv", "Svenska", "Enhetsinställning", "1 tittare ansluten", "{0} tittare anslutna", "Sessions-QR-kod", "Länk kopierad!", "Förnya QR / Koppla från", "Källa", "Skärm", "Primär", "Sekundär", "Bildfrekvens", "Kvalitet", "Upplösning", "Visa muspekare", "Strömma PC-ljud", "Blockera nya enheter (Offentligt nät)", "Förhindrar nya anslutningar även om IP är känt"),
            new LangPack("da", "Dansk", "Enhedsopsætning", "1 seer forbundet", "{0} seere forbundet", "Sessions-QR-kode", "Link kopieret!", "Forny QR / Afbryd", "Kilde", "Skærm", "Primær", "Sekundær", "Billedhastighed", "Kvalitet", "Opløsning", "Vis musemarkør", "Stream PC-lyd", "Bloker nye enheder (Offentligt netværk)", "Forhindrer nye forbindelser selv med kendt IP"),
            new LangPack("no", "Norsk", "Enhetsoppsett", "1 seer tilkoblet", "{0} seere tilkoblet", "Øktsikkerhet QR", "Lenke kopiert!", "Forny QR / Koble fra", "Kilde", "Skjerm", "Primær", "Sekundær", "Bildefrekvens", "Kvalitet", "Oppløsning", "Vis musepeker", "Strøm PC-lyd", "Blokker nye enheter (Offentlig nettverk)", "Hindrer nye tilkoblinger selv om IP er kjent"),
            new LangPack("fi", "Suomi", "Laitteen asennus", "1 katsoja yhdistetty", "{0} katsojaa yhdistetty", "Istunnon QR-koodi", "Linkki kopioitu!", "Uusi QR / Katkaise", "Lähde", "Näyttö", "Ensisijainen", "Toissijainen", "Sulavuus", "Laatu", "Tarkkuus", "Näytä hiiren osoitin", "Toista PC-ääni", "Estä uudet laitteet (Julkinen verkko)", "Estää uudet yhteydet vaikka IP tiedettäisiin"),
            new LangPack("el", "Ελληνικά", "Ρύθμιση συσκευής", "1 θεατής συνδεδεμένος", "{0} θεατές συνδεδεμένοι", "QR Ασφαλείας", "Ο σύνδεσμος αντιγράφηκε!", "Ανανέωση QR / Αποσύνδεση", "Πηγή", "Οθόνη", "Κύρια", "Δευτερεύουσα", "Ρυθμός καρέ", "Ποιότητα", "Ανάλυση", "Εμφάνιση δείκτη ποντικιού", "Μετάδοση ήχου PC", "Φραγή νέων συσκευών (Δημόσιο Δίκτυο)", "Εμποδίζει νέες συνδέσεις ακόμα κι αν είναι γνωστή η IP"),
            new LangPack("tr", "Türkçe", "Cihaz kurulumu", "1 izleyici bağlı", "{0} izleyici bağlı", "Oturum Güvenlik QR", "Bağlantı kopyalandı!", "QR Yenile / Bağlantıyı Kes", "Kaynak", "Ekran", "Birincil", "İkincil", "Akıcılık", "Kalite", "Çözünürlük", "Fare imlecini göster", "PC sesini aktar", "Yeni cihazları engelle (Açık Ağ)", "IP bilinse bile yeni bağlantıları engeller"),
            new LangPack("ru", "Русский", "Настройка устр-ва", "1 зритель подключен", "Зрителей: {0}", "QR безопасности сессии", "Ссылка скопирована!", "Обновить QR / Отключить", "Источник", "Экран", "Основной", "Второй", "Плавность", "Качество", "Разрешение", "Показывать курсор мыши", "Передавать звук ПК", "Блокировать новые устройства (Публичная сеть)", "Запрещает новые подключения даже при известном IP"),
            new LangPack("uk", "Українська", "Налаштування", "1 глядач підключений", "Глядачів: {0}", "QR безпеки сесії", "Посилання скопійовано!", "Оновити QR / Відключити", "Джерело", "Екран", "Основний", "Другий", "Плавність", "Якість", "Роздільність", "Показувати курсор миші", "Передавати звук ПК", "Блокувати нові пристрої (Публічна мережа)", "Забороняє нові підключення навіть за відомого IP"),
            new LangPack("ar", "العربية", "إعداد الجهاز", "مشاهد واحد متصل", "{0} مشاهدين متصلين", "رمز QR لأمان الجلسة", "تم نسخ الرابط!", "تجديد QR / قطع الاتصال", "المصدر", "شاشة", "رئيسية", "ثانوية", "السلاسة", "الجودة", "الدقة", "إظهار مؤشر الفأرة", "بث صوت الكمبيوتر", "حظر الأجهزة الجديدة (شبكة عامة)", "يمنع الاتصالات الجديدة حتى مع معرفة عنوان IP"),
            new LangPack("he", "עברית", "הגדרת מכשיר", "צופה 1 מחובר", "{0} צופים מחוברים", "קוד QR לאבטחת הפעלה", "הקישור הועתק!", "חדש QR / נתק", "מקור", "מסך", "ראשי", "משני", "קצב פריימים", "איכות", "רזולוציה", "הצג סמן עכבר", "הזרם שמע מהמחשב", "חסום מכשירים חדשים (רשת ציבורית)", "מונע חיבורים חדשים גם אם ה-IP ידוע"),
            new LangPack("hi", "हिन्दी", "डिवाइस सेटअप", "1 दर्शक जुड़ा है", "{0} दर्शक जुड़े हैं", "सत्र सुरक्षा QR", "लिंक कॉपी किया गया!", "नया QR / डिस्कनेक्ट", "स्रोत", "स्क्रीन", "मुख्य", "द्वितीयक", "फ़्रेम दर", "गुणवत्ता", "रेज़ोल्यूशन", "माउस कर्सर दिखाएँ", "पीसी ऑडियो स्ट्रीम करें", "नए उपकरण ब्लॉक करें (सार्वजनिक नेटवर्क)", "IP पता होने पर भी नए कनेक्शन रोकता है"),
            new LangPack("zh-CN", "中文 (简体)", "设备连接设置", "1 位观众已连接", "{0} 位观众已连接", "会话安全二维码", "安全链接已复制！", "刷新二维码 / 断开全部", "画面源", "屏幕", "主屏", "副屏", "流畅度", "画质", "分辨率", "显示鼠标指针", "传输电脑音频", "阻止新设备连接 (公共网络保护)", "即使他人知道 IP 地址也无法建立新连接"),
            new LangPack("zh-TW", "中文 (繁體)", "裝置連線設定", "1 位觀眾已連線", "{0} 位觀眾已連線", "工作階段安全 QR", "安全連結已複製！", "更新 QR / 中斷連線", "畫面來源", "螢幕", "主螢幕", "副螢幕", "流暢度", "畫質", "解析度", "顯示滑鼠游標", "傳送電腦音訊", "封鎖新裝置 (公共網路保護)", "即使知道 IP 位址也無法建立新連線"),
            new LangPack("ja", "日本語", "デバイス設定", "1 人の視聴者が接続中", "{0} 人の視聴者が接続中", "セッション保護 QR", "リンクをコピーしました！", "QR再生成 / 切断", "ソース", "画面", "メイン", "サブ", "フレームレート", "画質", "解像度", "マウスカーソルを表示", "PCの音声を送信", "新規デバイスをブロック (公衆ネットワーク)", "IPが知られていても新しい接続を拒否します"),
            new LangPack("ko", "한국어", "기기 연결 설정", "시청자 1명 연결됨", "시청자 {0}명 연결됨", "세션 보안 QR 코드", "보안 링크 복사됨!", "QR 재생성 / 연결 해제", "소스", "화면", "주 모니터", "보조 모니터", "프레임 속도", "화질", "해상도", "마우스 커서 표시", "PC 오디오 전송", "새 기기 차단 (공용 네트워크)", "IP를 알아도 새로운 연결을 차단합니다"),
            new LangPack("vi", "Tiếng Việt", "Thiết lập thiết bị", "1 người xem đã kết nối", "{0} người xem đã kết nối", "Mã QR Bảo mật", "Đã sao chép liên kết!", "Tạo lại QR / Ngắt kết nối", "Nguồn phát", "Màn hình", "Chính", "Phụ", "Độ mượt", "Chất lượng", "Độ phân giải", "Hiện con trỏ chuột", "Truyền âm thanh PC", "Chặn thiết bị mới (Mạng công cộng)", "Ngăn kết nối mới ngay cả khi biết IP"),
            new LangPack("id", "Bahasa Indonesia", "Setup perangkat", "1 penonton terhubung", "{0} penonton terhubung", "QR Keamanan Sesi", "Tautan disalin!", "Buat Ulang QR / Putuskan", "Sumber", "Layar", "Utama", "Kedua", "Kelancaran", "Kualitas", "Resolusi", "Tampilkan kursor mouse", "Kirim audio PC", "Blokir perangkat baru (Jaringan Publik)", "Mencegah koneksi baru meskipun IP diketahui")
        };

        private readonly Process _serverProc;
        private readonly Timer _pollTimer;
        private readonly PictureBox _qrBox;
        private readonly Label _lblPin;
        private readonly Label _lblUrl;
        private readonly Label _lblBadge;
        private readonly Button _btnHelp;
        private readonly ComboBox _cmbLang;
        private readonly Label _lblQrTitle;
        private readonly Button _btnRotate;
        private readonly Label _lblSource;
        private readonly Label _lblFps;
        private readonly Label _lblQuality;
        private readonly Label _lblScale;
        private readonly Label _lblCursor;
        private readonly Label _lblAudio;
        private readonly Label _lblAudioSub;
        private readonly Label _lblLock;
        private readonly Label _lblLockSub;
        private readonly ComboBox _cmbMonitor;
        private readonly ComboBox _cmbFps;
        private readonly ComboBox _cmbQuality;
        private readonly ComboBox _cmbScale;
        private readonly FluentToggle _tglCursor;
        private readonly FluentToggle _tglAudio;
        private readonly FluentToggle _tglLock;

        private string _currentQrUrl = "";
        private string _currentPin = "----";
        private string _currentBaseIpUrl = "http://127.0.0.1:8765";
        private Action _refreshGuideDialog = null;
        private int _lastViewersCount = 0;
        private bool _updatingUi = false;
        private readonly List<MonitorMeta> _monitors = new List<MonitorMeta>();

        public MainForm(Process serverProc)
        {
            _serverProc = serverProc;

            Text = "OpenDeskCast";
            ClientSize = new Size(620, 360);
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(30, 30, 30);
            ForeColor = Color.FromArgb(243, 243, 243);
            Font = new Font("Segoe UI", 9F, FontStyle.Regular, GraphicsUnit.Point);

            try
            {
                Icon assocIcon = Icon.ExtractAssociatedIcon(Application.ExecutablePath);
                if (assocIcon != null) Icon = assocIcon;
            }
            catch { }

            int dark = 1;
            try { DwmSetWindowAttribute(Handle, 20, ref dark, sizeof(int)); } catch { }
            try { DwmSetWindowAttribute(Handle, 19, ref dark, sizeof(int)); } catch { }

            // Header: "OpenDeskCast" on left, Language dropdown + Viewers badge on right
            Label lblTitle = new Label
            {
                Text = "OpenDeskCast",
                Font = new Font("Segoe UI Semibold", 11.5F, FontStyle.Bold),
                ForeColor = Color.White,
                AutoSize = true,
                Location = new Point(16, 13)
            };
            Controls.Add(lblTitle);

            _btnHelp = new Button
            {
                Text = "Setup dispositivo",
                Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold),
                Location = new Point(164, 12),
                Size = new Size(134, 24),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(39, 39, 39),
                ForeColor = Color.FromArgb(240, 240, 240),
                TabStop = false,
                Cursor = Cursors.Hand
            };
            _btnHelp.FlatAppearance.BorderColor = Color.FromArgb(64, 64, 64);
            _btnHelp.Click += (s, e) => { ActiveControl = null; ShowGuideDialog(); };
            Controls.Add(_btnHelp);

            _cmbLang = CreateDarkCombo(new Point(304, 12), 132);
            foreach (LangPack lp in Languages)
            {
                _cmbLang.Items.Add(lp.Name);
            }
            _cmbLang.SelectedIndex = 0;
            _cmbLang.SelectedIndexChanged += (s, e) => ApplyLanguage();
            Controls.Add(_cmbLang);

            _lblBadge = new Label
            {
                Text = "0 spettatori collegati",
                Font = new Font("Segoe UI Semibold", 8.5F, FontStyle.Bold),
                ForeColor = Color.FromArgb(76, 194, 255),
                BackColor = Color.FromArgb(39, 39, 39),
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(160, 24),
                Location = new Point(444, 12)
            };
            Controls.Add(_lblBadge);

            // Left Card: QR, 4-Digit PIN & opendeskcast.local (X: 16, Y: 48, W: 196, H: 296)
            FluentCard qrCard = new FluentCard
            {
                Location = new Point(16, 48),
                Size = new Size(196, 296)
            };
            Controls.Add(qrCard);

            _lblQrTitle = new Label
            {
                Text = "QR Sicurezza Sessione",
                Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold),
                ForeColor = Color.FromArgb(228, 228, 228),
                TextAlign = ContentAlignment.MiddleCenter,
                Size = new Size(176, 18),
                Location = new Point(10, 8)
            };
            qrCard.Controls.Add(_lblQrTitle);

            Panel qrWhiteFrame = new Panel
            {
                BackColor = Color.White,
                Location = new Point(30, 30),
                Size = new Size(136, 136)
            };
            qrCard.Controls.Add(qrWhiteFrame);

            _qrBox = new PictureBox
            {
                Location = new Point(2, 2),
                Size = new Size(132, 132),
                SizeMode = PictureBoxSizeMode.StretchImage,
                BackColor = Color.White
            };
            qrWhiteFrame.Controls.Add(_qrBox);

            _lblPin = new Label
            {
                Text = "PIN: ----",
                Font = new Font("Consolas", 10F, FontStyle.Bold),
                ForeColor = Color.FromArgb(76, 194, 255),
                BackColor = Color.FromArgb(20, 34, 44),
                TextAlign = ContentAlignment.MiddleCenter,
                Location = new Point(12, 172),
                Size = new Size(172, 24)
            };
            qrCard.Controls.Add(_lblPin);

            _lblUrl = new Label
            {
                Text = "http://127.0.0.1:8765",
                Font = new Font("Consolas", 8.2F, FontStyle.Regular),
                ForeColor = Color.FromArgb(76, 194, 255),
                BackColor = Color.FromArgb(26, 26, 26),
                TextAlign = ContentAlignment.MiddleCenter,
                Location = new Point(12, 202),
                Size = new Size(172, 36),
                Cursor = Cursors.Hand
            };
            _lblUrl.Click += (s, e) =>
            {
                if (!string.IsNullOrEmpty(_currentBaseIpUrl))
                {
                    Clipboard.SetText(_currentBaseIpUrl);
                    string old = _lblUrl.Text;
                    _lblUrl.Text = CurrentLang().Copied;
                    Timer t = new Timer { Interval = 900 };
                    t.Tick += (ts, te) => { _lblUrl.Text = old; t.Stop(); t.Dispose(); };
                    t.Start();
                }
            };
            qrCard.Controls.Add(_lblUrl);

            _btnRotate = new Button
            {
                Text = "Rigenera QR / Disconnetti",
                Font = new Font("Segoe UI Semibold", 8.2F, FontStyle.Bold),
                Location = new Point(12, 248),
                Size = new Size(172, 34),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(48, 48, 48),
                ForeColor = Color.FromArgb(235, 235, 235),
                TabStop = false,
                Cursor = Cursors.Hand
            };
            _btnRotate.FlatAppearance.BorderColor = Color.FromArgb(76, 76, 76);
            _btnRotate.Click += (s, e) => RotateSessionToken();
            qrCard.Controls.Add(_btnRotate);

            // Right Card: Settings (X: 224, Y: 48, W: 380, H: 296)
            FluentCard ctrlCard = new FluentCard
            {
                Location = new Point(224, 48),
                Size = new Size(380, 296)
            };
            Controls.Add(ctrlCard);

            // Row 1: "Sorgente"
            _lblSource = new Label
            {
                Text = "Sorgente",
                Font = new Font("Segoe UI", 8.2F),
                ForeColor = Color.FromArgb(165, 165, 165),
                Location = new Point(14, 12),
                Size = new Size(320, 16)
            };
            ctrlCard.Controls.Add(_lblSource);

            _cmbMonitor = CreateDarkCombo(new Point(14, 31), 320);
            _cmbMonitor.SelectedIndexChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_cmbMonitor);

            Button btnRefresh = new Button
            {
                Text = "↻",
                Location = new Point(340, 30),
                Size = new Size(26, 25),
                FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(30, 30, 30),
                ForeColor = Color.FromArgb(210, 210, 210),
                Cursor = Cursors.Hand
            };
            btnRefresh.FlatAppearance.BorderColor = Color.FromArgb(68, 68, 68);
            btnRefresh.Click += (s, e) => RefreshMonitorsForce();
            ctrlCard.Controls.Add(btnRefresh);

            // Row 2: FPS, Quality, Scale (Y: 66)
            _lblFps = new Label
            {
                Text = "Fluidità",
                Font = new Font("Segoe UI", 8.2F),
                ForeColor = Color.FromArgb(165, 165, 165),
                Location = new Point(14, 66),
                Size = new Size(110, 16)
            };
            ctrlCard.Controls.Add(_lblFps);

            _cmbFps = CreateDarkCombo(new Point(14, 85), 110);
            _cmbFps.Items.AddRange(new object[] { "15 FPS", "30 FPS", "45 FPS", "60 FPS" });
            _cmbFps.SelectedIndex = 1;
            _cmbFps.SelectedIndexChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_cmbFps);

            _lblQuality = new Label
            {
                Text = "Qualità",
                Font = new Font("Segoe UI", 8.2F),
                ForeColor = Color.FromArgb(165, 165, 165),
                Location = new Point(135, 66),
                Size = new Size(110, 16)
            };
            ctrlCard.Controls.Add(_lblQuality);

            _cmbQuality = CreateDarkCombo(new Point(135, 85), 110);
            _cmbQuality.Items.AddRange(new object[] { "50%", "60%", "80%", "90%", "100%" });
            _cmbQuality.SelectedIndex = 2;
            _cmbQuality.SelectedIndexChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_cmbQuality);

            _lblScale = new Label
            {
                Text = "Risoluzione",
                Font = new Font("Segoe UI", 8.2F),
                ForeColor = Color.FromArgb(165, 165, 165),
                Location = new Point(256, 66),
                Size = new Size(110, 16)
            };
            ctrlCard.Controls.Add(_lblScale);

            _cmbScale = CreateDarkCombo(new Point(256, 85), 110);
            _cmbScale.Items.AddRange(new object[] { "50%", "60%", "80%", "90%", "100%" });
            _cmbScale.SelectedIndex = 4;
            _cmbScale.SelectedIndexChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_cmbScale);

            // Divider (Y: 122)
            Panel div = new Panel
            {
                BackColor = Color.FromArgb(56, 56, 56),
                Location = new Point(14, 122),
                Size = new Size(352, 1)
            };
            ctrlCard.Controls.Add(div);

            // Row 3: Switch Cursor (Y: 136)
            _lblCursor = new Label
            {
                Text = "Mostra cursore del mouse",
                Font = new Font("Segoe UI", 9.2F),
                ForeColor = Color.FromArgb(240, 240, 240),
                Location = new Point(14, 136),
                Size = new Size(295, 22)
            };
            ctrlCard.Controls.Add(_lblCursor);

            _tglCursor = new FluentToggle { Location = new Point(324, 136) };
            _tglCursor.SetCheckedSilent(true);
            _tglCursor.CheckedChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_tglCursor);

            // Row 4: Switch Audio (Y: 172)
            _lblAudio = new Label
            {
                Text = "Trasmetti audio del PC",
                Font = new Font("Segoe UI", 9.2F),
                ForeColor = Color.FromArgb(240, 240, 240),
                Location = new Point(14, 172),
                Size = new Size(295, 20)
            };
            ctrlCard.Controls.Add(_lblAudio);

            _lblAudioSub = new Label
            {
                Text = "Dispositivo: Audio to OpenDeskCast (PC silenziato)",
                Font = new Font("Segoe UI", 7.8F),
                ForeColor = Color.FromArgb(108, 203, 95),
                Location = new Point(14, 193),
                Size = new Size(295, 18)
            };
            ctrlCard.Controls.Add(_lblAudioSub);

            _tglAudio = new FluentToggle { Location = new Point(324, 176) };
            _tglAudio.SetCheckedSilent(true);
            _tglAudio.CheckedChanged += (s, e) => {
                UpdateAudioSubLabel();
                PushSettings();
            };
            ctrlCard.Controls.Add(_tglAudio);

            // Row 5: Switch Lock New Devices on Public Network (Y: 220)
            _lblLock = new Label
            {
                Text = "Blocca nuovi dispositivi (Rete Pubblica)",
                Font = new Font("Segoe UI", 9.2F),
                ForeColor = Color.FromArgb(240, 240, 240),
                Location = new Point(14, 218),
                Size = new Size(295, 20)
            };
            ctrlCard.Controls.Add(_lblLock);

            _lblLockSub = new Label
            {
                Text = "Impedisce nuovi collegamenti anche conoscendo l'IP",
                Font = new Font("Segoe UI", 7.8F),
                ForeColor = Color.FromArgb(148, 148, 148),
                Location = new Point(14, 239),
                Size = new Size(295, 18)
            };
            ctrlCard.Controls.Add(_lblLockSub);

            _tglLock = new FluentToggle { Location = new Point(324, 224) };
            _tglLock.CheckedChanged += (s, e) => PushSettings();
            ctrlCard.Controls.Add(_tglLock);

            _pollTimer = new Timer { Interval = 1500 };
            _pollTimer.Tick += (s, e) => PollStatus(false);
            _pollTimer.Start();
        }

        private LangPack CurrentLang()
        {
            int idx = _cmbLang.SelectedIndex;
            if (idx < 0 || idx >= Languages.Length) idx = 0;
            return Languages[idx];
        }

        private void UpdateBadgeText(int count)
        {
            _lastViewersCount = count;
            LangPack lp = CurrentLang();
            _lblBadge.Text = count == 1 ? lp.V1 : string.Format(lp.VN, count);
            _lblBadge.ForeColor = count > 0 ? Color.FromArgb(108, 203, 95) : Color.FromArgb(76, 194, 255);
        }

        private void RebuildMonitorNames()
        {
            if (_monitors.Count == 0) return;
            LangPack lp = CurrentLang();
            int prevIdx = Math.Max(0, _cmbMonitor.SelectedIndex);
            _updatingUi = true;
            _cmbMonitor.Items.Clear();
            foreach (MonitorMeta m in _monitors)
            {
                string role = m.IsPrimary ? lp.PrimaryWord : lp.SecondaryWord;
                _cmbMonitor.Items.Add(string.Format("{0} {1} ({2} - {3}x{4})", lp.ScreenWord, m.Id + 1, role, m.Width, m.Height));
            }
            if (_cmbMonitor.Items.Count > 0)
            {
                _cmbMonitor.SelectedIndex = Math.Min(prevIdx, _cmbMonitor.Items.Count - 1);
            }
            _updatingUi = false;
        }

        private void ApplyLanguage()
        {
            LangPack lp = CurrentLang();
            _updatingUi = true;

            _btnHelp.Text = lp.SetupBtn;
            _lblQrTitle.Text = lp.QrTitle;
            _btnRotate.Text = lp.RotateBtn;
            _lblSource.Text = lp.Source;
            _lblFps.Text = lp.Fps;
            _lblQuality.Text = lp.Quality;
            _lblScale.Text = lp.Scale;
            _lblCursor.Text = lp.Cursor;
            _lblAudio.Text = lp.Audio;
            _lblLock.Text = lp.LockTitle;
            _lblLockSub.Text = lp.LockSub;

            _updatingUi = false;
            UpdateAudioSubLabel();
            RebuildMonitorNames();
            UpdateBadgeText(_lastViewersCount);
        }

        private void UpdateAudioSubLabel()
        {
            if (_lblAudioSub == null) return;
            LangPack lp = CurrentLang();
            bool isIt = lp.Code == "it";
            if (_tglAudio.Checked)
            {
                _lblAudioSub.Text = isIt
                    ? "Dispositivo: Audio to OpenDeskCast (PC silenziato)"
                    : "Device: Audio to OpenDeskCast (PC muted)";
                _lblAudioSub.ForeColor = Color.FromArgb(108, 203, 95);
            }
            else
            {
                _lblAudioSub.Text = isIt
                    ? "Dispositivo: Altoparlanti PC (Cast disattivato)"
                    : "Device: Local PC Speakers (Cast inactive)";
                _lblAudioSub.ForeColor = Color.FromArgb(148, 148, 148);
            }
        }

        private void ShowGuideDialog()
        {
            LangPack lp = CurrentLang();
            bool isIt = lp.Code == "it";

            using (Form dlg = new Form())
            {
                dlg.Text = isIt ? "OpenDeskCast — Come collegare uno Spettatore" : "OpenDeskCast — Connection Guide";
                dlg.ClientSize = new Size(520, 340);
                dlg.FormBorderStyle = FormBorderStyle.FixedDialog;
                dlg.MaximizeBox = false;
                dlg.MinimizeBox = false;
                dlg.StartPosition = FormStartPosition.CenterParent;
                dlg.BackColor = Color.FromArgb(30, 30, 30);
                dlg.ForeColor = Color.FromArgb(240, 240, 240);
                dlg.Font = new Font("Segoe UI", 9F);
                if (Icon != null) dlg.Icon = Icon;

                int dark = 1;
                try { DwmSetWindowAttribute(dlg.Handle, 20, ref dark, sizeof(int)); } catch { }
                try { DwmSetWindowAttribute(dlg.Handle, 19, ref dark, sizeof(int)); } catch { }

                FluentCard box1 = new FluentCard { Location = new Point(16, 14), Size = new Size(488, 76) };
                Label t1 = new Label
                {
                    Text = isIt ? "1. Dispositivi con Fotocamera (QR Code)" : "1. Devices with Camera (QR Code)",
                    Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold),
                    ForeColor = Color.FromArgb(76, 194, 255),
                    Location = new Point(12, 8),
                    Size = new Size(464, 20)
                };
                Label b1 = new Label
                {
                    Text = isIt
                        ? "Inquadra il QR Code con la fotocamera del tablet o smartphone: lo schermo del PC apparirà subito a tutto schermo senza inserire codici."
                        : "Scan the QR Code with your device camera: the PC screen will immediately open in fullscreen without entering any code.",
                    Font = new Font("Segoe UI", 8.8F),
                    ForeColor = Color.FromArgb(225, 225, 225),
                    Location = new Point(12, 30),
                    Size = new Size(464, 40)
                };
                box1.Controls.Add(t1);
                box1.Controls.Add(b1);
                dlg.Controls.Add(box1);

                FluentCard box2 = new FluentCard { Location = new Point(16, 98), Size = new Size(488, 122) };
                Label t2 = new Label
                {
                    Text = isIt ? "2. Dispositivi SENZA Fotocamera (Indirizzo IP + PIN a 4 cifre)" : "2. Devices WITHOUT Camera (IP Address + 4-Digit PIN)",
                    Font = new Font("Segoe UI Semibold", 9.5F, FontStyle.Bold),
                    ForeColor = Color.FromArgb(76, 194, 255),
                    Location = new Point(12, 8),
                    Size = new Size(464, 20)
                };
                Label b2 = new Label
                {
                    Font = new Font("Segoe UI", 8.6F),
                    ForeColor = Color.FromArgb(225, 225, 225),
                    Location = new Point(12, 30),
                    Size = new Size(464, 86)
                };
                _refreshGuideDialog = () =>
                {
                    b2.Text = isIt
                        ? string.Format(
                            "• Apri il browser del dispositivo e digita l'indirizzo:  {0}\r\n• Consiglio: Salva la pagina nei Preferiti o sulla schermata Home per aprirla con un solo tocco.\r\n• Sul tastierino a schermo inserisci il PIN di 4 cifre mostrato sotto il QR (attuale: {1}).",
                            _currentBaseIpUrl, _currentPin)
                        : string.Format(
                            "• Open the browser on your device and go to:  {0}\r\n• Tip: Bookmark this page so you never have to type it again.\r\n• Enter the 4-digit PIN shown under the QR code (current: {1}) on the keypad.",
                            _currentBaseIpUrl, _currentPin);
                };
                _refreshGuideDialog();
                dlg.FormClosed += (s, e) => { _refreshGuideDialog = null; };
                box2.Controls.Add(t2);
                box2.Controls.Add(b2);
                dlg.Controls.Add(box2);

                FluentCard box3 = new FluentCard { Location = new Point(16, 228), Size = new Size(488, 60) };
                Label t3 = new Label
                {
                    Text = isIt ? "3. Sicurezza e Chiusura" : "3. Security & Disconnect",
                    Font = new Font("Segoe UI Semibold", 9.2F, FontStyle.Bold),
                    ForeColor = Color.FromArgb(108, 203, 95),
                    Location = new Point(12, 7),
                    Size = new Size(464, 18)
                };
                Label b3 = new Label
                {
                    Text = isIt
                        ? "Il QR Code e il PIN cambiano automaticamente a ogni avvio o cliccando \"" + lp.RotateBtn + "\"."
                        : "Both the QR Code and the 4-digit PIN rotate automatically on restart or when clicking \"" + lp.RotateBtn + "\".",
                    Font = new Font("Segoe UI", 8.6F),
                    ForeColor = Color.FromArgb(215, 215, 215),
                    Location = new Point(12, 27),
                    Size = new Size(464, 28)
                };
                box3.Controls.Add(t3);
                box3.Controls.Add(b3);
                dlg.Controls.Add(box3);

                Button btnOk = new Button
                {
                    Text = "OK",
                    Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold),
                    Location = new Point(414, 298),
                    Size = new Size(90, 30),
                    FlatStyle = FlatStyle.Flat,
                    BackColor = Color.FromArgb(52, 52, 52),
                    ForeColor = Color.White,
                    Cursor = Cursors.Hand
                };
                btnOk.FlatAppearance.BorderColor = Color.FromArgb(84, 84, 84);
                btnOk.Click += (s, e) => dlg.Close();
                dlg.Controls.Add(btnOk);

                dlg.ShowDialog(this);
            }
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            ActiveControl = null;
        }

        private ComboBox CreateDarkCombo(Point location, int width)
        {
            ComboBox cmb = new ComboBox
            {
                Location = location,
                Size = new Size(width, 24),
                DropDownStyle = ComboBoxStyle.DropDownList,
                FlatStyle = FlatStyle.Flat,
                DrawMode = DrawMode.OwnerDrawFixed,
                ItemHeight = 18,
                TabStop = false,
                BackColor = Color.FromArgb(28, 28, 28),
                ForeColor = Color.FromArgb(240, 240, 240),
                Font = new Font("Segoe UI", 8.8F)
            };
            cmb.DrawItem += (s, e) =>
            {
                if (e.Index < 0) return;
                ComboBox box = (ComboBox)s;
                bool isEdit = (e.State & DrawItemState.ComboBoxEdit) == DrawItemState.ComboBoxEdit;
                bool isSelected = (e.State & DrawItemState.Selected) == DrawItemState.Selected;
                Color bg = (!isEdit && isSelected) ? Color.FromArgb(56, 56, 56) : Color.FromArgb(28, 28, 28);
                using (SolidBrush bgBrush = new SolidBrush(bg))
                {
                    e.Graphics.FillRectangle(bgBrush, e.Bounds);
                }
                TextRenderer.DrawText(
                    e.Graphics,
                    box.Items[e.Index].ToString(),
                    box.Font,
                    new Rectangle(e.Bounds.X + 4, e.Bounds.Y, e.Bounds.Width - 6, e.Bounds.Height),
                    Color.FromArgb(240, 240, 240),
                    TextFormatFlags.VerticalCenter | TextFormatFlags.Left | TextFormatFlags.EndEllipsis
                );
            };
            cmb.DropDownClosed += (s, e) => { ActiveControl = null; };
            cmb.SelectedIndexChanged += (s, e) => { ActiveControl = null; };
            return cmb;
        }

        private void RefreshMonitorsForce()
        {
            PollStatus(true);
        }

        private void PollStatus(bool forceReload)
        {
            try
            {
                using (WebClient wc = new WebClient())
                {
                    wc.Encoding = Encoding.UTF8;
                    string json = wc.DownloadString("http://127.0.0.1:8765/api/status?port=8765");

                    Match mViewers = Regex.Match(json, "\"connected_viewers\"\\s*:\\s*(\\d+)");
                    if (mViewers.Success)
                    {
                        int count = int.Parse(mViewers.Groups[1].Value);
                        UpdateBadgeText(count);
                    }

                    bool guideNeedsUpdate = false;

                    Match mPin = Regex.Match(json, "\"session_pin\"\\s*:\\s*\"([^\"]+)\"");
                    if (mPin.Success)
                    {
                        string newPin = mPin.Groups[1].Value;
                        if (newPin != _currentPin)
                        {
                            _currentPin = newPin;
                            _lblPin.Text = "PIN: " + _currentPin;
                            guideNeedsUpdate = true;
                        }
                    }

                    Match mBase = Regex.Match(json, "\"base_url\"\\s*:\\s*\"([^\"]+)\"");
                    if (mBase.Success)
                    {
                        string newBase = mBase.Groups[1].Value;
                        if (newBase != _currentBaseIpUrl)
                        {
                            _currentBaseIpUrl = newBase;
                            _lblUrl.Text = _currentBaseIpUrl;
                            guideNeedsUpdate = true;
                        }
                    }

                    if (guideNeedsUpdate && _refreshGuideDialog != null)
                    {
                        _refreshGuideDialog();
                    }

                    Match mUrl = Regex.Match(json, "\"urls\"\\s*:\\s*\\[\\s*\"([^\"]+)\"");
                    if (mUrl.Success)
                    {
                        string primaryUrl = mUrl.Groups[1].Value;
                        if (primaryUrl != _currentQrUrl)
                        {
                            _currentQrUrl = primaryUrl;
                            _lblUrl.Text = _currentBaseIpUrl;
                            byte[] pngBytes = wc.DownloadData("http://127.0.0.1:8765/api/qr.png?url=" + Uri.EscapeDataString(primaryUrl));
                            using (MemoryStream ms = new MemoryStream(pngBytes))
                            {
                                _qrBox.Image = Image.FromStream(ms);
                            }
                        }
                    }

                    MatchCollection mMons = Regex.Matches(
                        json,
                        "\\{\\s*\"id\"\\s*:\\s*(\\d+)[^\\}]*?\"width\"\\s*:\\s*(\\d+)\\s*,\\s*\"height\"\\s*:\\s*(\\d+)\\s*,\\s*\"is_primary\"\\s*:\\s*(true|false)"
                    );

                    if (forceReload || mMons.Count != _monitors.Count)
                    {
                        _monitors.Clear();
                        HashSet<int> seenIds = new HashSet<int>();
                        foreach (Match m in mMons)
                        {
                            int id = int.Parse(m.Groups[1].Value);
                            if (!seenIds.Contains(id))
                            {
                                seenIds.Add(id);
                                MonitorMeta meta = new MonitorMeta();
                                meta.Id = id;
                                meta.Width = int.Parse(m.Groups[2].Value);
                                meta.Height = int.Parse(m.Groups[3].Value);
                                meta.IsPrimary = m.Groups[4].Value == "true";
                                _monitors.Add(meta);
                            }
                        }
                        RebuildMonitorNames();
                    }
                }
            }
            catch { }
        }

        private void RotateSessionToken()
        {
            try
            {
                using (WebClient wc = new WebClient())
                {
                    wc.UploadString("http://127.0.0.1:8765/api/rotate-token", "POST", "");
                }
                _currentQrUrl = "";
                PollStatus(false);
            }
            catch { }
        }

        private void PushSettings()
        {
            if (_updatingUi) return;
            try
            {
                int monId = (_cmbMonitor.SelectedIndex >= 0 && _cmbMonitor.SelectedIndex < _monitors.Count)
                    ? _monitors[_cmbMonitor.SelectedIndex].Id
                    : 0;
                int[] fpsVals = new int[] { 15, 30, 45, 60 };
                int[] qualVals = new int[] { 50, 60, 80, 90, 100 };
                string[] scaleVals = new string[] { "0.5", "0.6", "0.8", "0.9", "1.0" };

                int fps = fpsVals[Math.Max(0, _cmbFps.SelectedIndex)];
                int qual = qualVals[Math.Max(0, _cmbQuality.SelectedIndex)];
                string scale = scaleVals[Math.Max(0, _cmbScale.SelectedIndex)];
                string cursor = _tglCursor.Checked ? "true" : "false";
                string audio = _tglAudio.Checked ? "true" : "false";
                string lockNew = _tglLock.Checked ? "true" : "false";

                string body = string.Format(
                    "{{\"monitor_id\":{0},\"fps\":{1},\"quality\":{2},\"scale\":{3},\"draw_cursor\":{4},\"audio_enabled\":{5},\"lock_new_viewers\":{6}}}",
                    monId, fps, qual, scale, cursor, audio, lockNew
                );

                using (WebClient wc = new WebClient())
                {
                    wc.Headers[HttpRequestHeader.ContentType] = "application/json";
                    wc.UploadString("http://127.0.0.1:8765/api/settings", "POST", body);
                }
            }
            catch { }
        }

        protected override void OnFormClosing(FormClosingEventArgs e)
        {
            _pollTimer.Stop();
            try
            {
                HttpWebRequest req = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:8765/api/shutdown");
                req.Method = "POST";
                req.Timeout = 1200;
                using (WebResponse resp = req.GetResponse()) { }
            }
            catch { }

            try
            {
                if (_serverProc != null && !_serverProc.HasExited)
                {
                    if (!_serverProc.WaitForExit(800))
                    {
                        _serverProc.Kill();
                    }
                }
            }
            catch { }

            base.OnFormClosing(e);
        }
    }

    internal static class Program
    {
        [DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();

        [STAThread]
        private static void Main()
        {
            try { SetProcessDPIAware(); } catch { }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string bundledEngine = Path.Combine(baseDir, "engine", "OpenDeskCastEngine.exe");
            if (!File.Exists(bundledEngine))
            {
                bundledEngine = Path.Combine(baseDir, "OpenDeskCastEngine.exe");
            }

            ProcessStartInfo psi;
            if (File.Exists(bundledEngine))
            {
                psi = new ProcessStartInfo
                {
                    FileName = bundledEngine,
                    Arguments = "--no-window",
                    WorkingDirectory = Path.GetDirectoryName(bundledEngine),
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
            }
            else
            {
                string runScript = Path.Combine(baseDir, "run.py");
                if (!File.Exists(runScript))
                {
                    MessageBox.Show(
                        "Impossibile trovare il motore integrato (OpenDeskCastEngine.exe) o run.py in:\n" + baseDir,
                        "OpenDeskCast",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Error
                    );
                    return;
                }

                string pythonExe = Path.Combine(baseDir, ".venv", "Scripts", "python.exe");
                if (!File.Exists(pythonExe))
                {
                    string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                    string candidate = Path.Combine(localAppData, "Programs", "Python", "Python310", "python.exe");
                    pythonExe = File.Exists(candidate) ? candidate : "python.exe";
                }

                psi = new ProcessStartInfo
                {
                    FileName = pythonExe,
                    Arguments = "\"" + runScript + "\" --no-window",
                    WorkingDirectory = baseDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
            }

            try
            {
                foreach (Process oldProc in Process.GetProcessesByName("OpenDeskCastEngine"))
                {
                    try { oldProc.Kill(); oldProc.WaitForExit(500); } catch { }
                }
            }
            catch { }

            Process serverProc = null;
            try
            {
                serverProc = Process.Start(psi);
                Application.Run(new MainForm(serverProc));
            }
            finally
            {
                try
                {
                    if (serverProc != null && !serverProc.HasExited)
                    {
                        serverProc.Kill();
                    }
                }
                catch { }
            }
        }
    }
}
