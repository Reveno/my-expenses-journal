# 💰 My Expenses Journal Bot

Telegram-бот для обліку витрат та доходів. Підтримує 4 мови (UK/RU/EN/DE).

## Функції
- ➕ Додавання витрат за категоріями
- 📈 Облік доходів + 💰 Баланс (дохід − витрати)
- ⚡ Шаблони для частих витрат
- 📅📆🗓 Звіти по днях/тижнях/місяцях
- ⚠️ Ліміти з попередженнями (80% і 100%)
- 🔁 Регулярні витрати (авто-запис по даті)
- 🔔 Нагадування (неактивність, щоденні, тижневі)
- 📊 Порівняння місяць/місяць
- 🔄 Конвертер валют (160+ валют)
- 📊 Excel-звіт (3 листи)
- ⚙️ Власні категорії
- 💬 Зворотній зв'язок з відповідями
- 📖 Вбудована інструкція

## Деплой на Railway (рекомендовано)

### 1. Підготовка
```bash
git init
git add bot.py requirements.txt .gitignore README.md .env.example
git commit -m "Initial release"
git remote add origin https://github.com/YOUR_USERNAME/my-expenses-journal.git
git push -u origin main
```

### 2. Railway
1. railway.app → New Project → Deploy from GitHub repo
2. `+ New` → Database → **Add PostgreSQL** (Railway сам додасть `DATABASE_URL`)
3. Settings → Variables → додай:

| Змінна | Значення |
|--------|----------|
| `BOT_TOKEN` | токен від @BotFather |
| `ADMIN_ID` | твій Telegram ID (@userinfobot) |
| `DONATE_URL` | посилання для донатів |

### 3. Готово
Railway автоматично запустить бота при кожному `git push`.

## Локальний запуск
```bash
pip install -r requirements.txt
# заповни .env (скопіюй з .env.example)
python bot.py
```

## Команди адміністратора
- `/reply USER_ID текст` — відповісти на фідбек користувача

## Змінні середовища
| Змінна | Обов'язкова | Опис |
|--------|-------------|------|
| `BOT_TOKEN` | ✅ | Токен від @BotFather |
| `DATABASE_URL` | ❌ | PostgreSQL (Railway). Без нього — SQLite |
| `ADMIN_ID` | ❌ | Твій Telegram ID для фідбеку |
| `DONATE_URL` | ❌ | Посилання для донатів |
| `ALLOWED_USERS` | ❌ | Whitelist ID (порожньо = публічний) |
