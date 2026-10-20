import logging
from telebot import TeleBot, types

# Токен бота (замените на свой токен от @BotFather)
TOKEN = '8839559401:AAGrbbdaiZ7vTJYWYQComfV0qfJW7JKW8MM'
bot = TeleBot(TOKEN)

# Логирование
logging.basicConfig(level=logging.INFO)

# Инициализация базы данных (в памяти для простоты, в реальном проекте лучше использовать SQLite/PostgreSQL)
db = {
    "admins": [678901234],  # ID главного админа (замените на ваш Telegram ID)
    "admin_usernames": ["lytixx"],  # Юзернейм главного админа
    "rp_commands": {
        "обкашлить": "{user1} обкашлил вопросы с {user2}",
        "трахнуть": "{user1} трахнул {user2}",
        "поцеловать": "{user1} поцеловал {user2} в щёчку",
        "обнять": "{user1} крепко обнял {user2}",
        "ударить": "{user1} дал дружеский подзатыльник {user2}"
    },
    "stats": {},  # {user_id: {"username": str, "messages": int, "rewards": []}}
    "states": {}  # Для отслеживания шагов в ЛС {user_id: state}
}

# Функция для добавления пользователя в статистику, если его там нет
def check_user(user_id, username):
    if user_id not in db["stats"]:
        db["stats"][user_id] = {
            "username": username or f"id{user_id}",
            "messages": 0,
            "rewards": []
        }
    if username and db["stats"][user_id]["username"] != username:
        db["stats"][user_id]["username"] = username

# Функция проверки прав администратора
def is_admin(user):
    return user.id in db["admins"] or (user.username and user.username.lower() in [u.lower() for u in db["admin_usernames"]])

# --- ОБРАБОТКА КОМАНД В ГРУППАХ ---

# Закрепление сообщений
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text and m.text.startswith('!Закреп'))
def pin_message(message):
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Эта команда должна быть ответом на сообщение, которое нужно закрепить.")
        return
    
    # Проверяем, является ли отправитель админом чата или бота
    chat_member = bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status in ['creator', 'administrator'] or is_admin(message.from_user):
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Сообщение успешно закреплено!")
        except Exception as e:
            bot.reply_to(message, f"❌ Не удалось закрепить сообщение. Проверьте мои права администратора.")
    else:
        bot.reply_to(message, "❌ У вас нет прав для использования этой команды в чате.")

# Профиль пользователя
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text and m.text.lower() in ['профиль', '!профиль'])
def show_profile(message):
    target_user = message.from_user
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        
    check_user(target_user.id, target_user.username)
    user_data = db["stats"][target_user.id]
    
    rewards_str = ", ".join(user_data["rewards"]) if user_data["rewards"] else "Отсутствуют"
    
    text = (
        f"👤 *Профиль пользователя:* {target_user.first_name}
"
        f"📊 *Сообщений отправлено:* {user_data['messages']}
"
        f"🏆 *Награды:* {rewards_str}"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

# Статистика актива (Топ)
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text and m.text.lower() in ['стата', 'топ'])
def show_top(message):
    if not db["stats"]:
        bot.reply_to(message, "📊 Статистика пока пуста.")
        return
        
    sorted_users = sorted(db["stats"].items(), key=lambda x: x[1]["messages"], reverse=True)[:10]
    
    text = "🏆 *Топ-10 активных участников:* 

"
    for i, (user_id, data) in enumerate(sorted_users, 1):
        text += f"{i}. @{data['username']} — {data['messages']} соотв.
"
        
    bot.reply_to(message, text, parse_mode="Markdown")

# Награждение участников
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text and m.text.startswith('!наградить'))
def reward_user(message):
    if not is_admin(message.from_user):
        bot.reply_to(message, "❌ Эта команда доступна только администраторам бота.")
        return
        
    if not message.reply_to_message:
        bot.reply_to(message, "⚠️ Ответьте этой командой на сообщение пользователя, которого хотите наградить.")
        return
        
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "⚠️ Укажите название награды после команды. Пример: `!наградить Медаль за актив`")
        return
        
    reward_name = parts[1]
    target_user = message.reply_to_message.from_user
    
    check_user(target_user.id, target_user.username)
    db["stats"][target_user.id]["rewards"].append(reward_name)
    
    bot.reply_to(message, f"🏅 Пользователь {target_user.first_name} успешно награжден: *{reward_name}*", parse_mode="Markdown")

# РП команды
@bot.message_handler(func=lambda m: m.chat.type in ['group', 'supergroup'] and m.text)
def handle_rp_and_counter(message):
    # Учет статистики сообщений
    check_user(message.from_user.id, message.from_user.username)
    db["stats"][message.from_user.id]["messages"] += 1
    
    # Проверка РП команд
    text_lower = message.text.lower().strip()
    if text_lower in db["rp_commands"]:
        if not message.reply_to_message:
            bot.reply_to(message, f"⚠️ Команда `{message.text}` должна быть ответом на сообщение другого участника.")
            return
            
        user1 = f"[{message.from_user.first_name}](tg://user?id={message.from_user.id})"
        user2 = f"[{message.reply_to_message.from_user.first_name}](tg://user?id={message.reply_to_message.from_user.id})"
        
        template = db["rp_commands"][text_lower]
        response = template.format(user1=user1, user2=user2)
        
        bot.send_message(message.chat.id, response, parse_mode="Markdown")


# --- АДМИН-ПАНЕЛЬ В ЛС БОТА ---

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def admin_private_panel(message):
    if not is_admin(message.from_user):
        bot.reply_to(message, "👋 Привет! Я бот-администратор для ваших групп. Добавьте меня в чат и дайте права, чтобы я мог управлять им.")
        return

    user_id = message.from_user.id
    text = message.text.strip()

    # Сброс состояний по команде /start или отмена
    if text in ['/start', 'отмена', 'Отмена']:
        db["states"].pop(user_id, None)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("➕ Назначить админа", "🛠 Добавить РП-команду")
        markup.row("📋 Список РП-команд", "👑 Список админов")
        bot.send_message(user_id, f"👑 *Добро пожаловать в админ-панель, {message.from_user.first_name}!*", 
                         reply_markup=markup, parse_mode="Markdown")
        return

    # Обработка состояний (ввод данных)
    if user_id in db["states"]:
        state = db["states"][user_id]
        
        if state == 'wait_admin_id':
            try:
                new_admin_id = int(text)
                if new_admin_id not in db["admins"]:
                    db["admins"].append(new_admin_id)
                db["states"].pop(user_id, None)
                bot.send_message(user_id, f"✅ Пользователь с ID `{new_admin_id}` успешно назначен администратором бота.", parse_mode="Markdown")
            except ValueError:
                if text.startswith('@'):
                    username = text.replace('@', '')
                    if username not in db["admin_usernames"]:
                        db["admin_usernames"].append(username)
                    db["states"].pop(user_id, None)
                    bot.send_message(user_id, f"✅ Администратор @{username} добавлен в список.")
                else:
                    bot.send_message(user_id, "⚠️ Некорректный формат. Введите ID (цифрами) или @username. Для отмены напишите 'отмена'.")
            return
            
        elif state == 'wait_rp_name':
            db["states"][user_id] = {'step': 'wait_rp_template', 'name': text.lower()}
            bot.send_message(user_id, "Шаг 2: Введите текст ответа для этой команды.
 Используйте переменные `{user1}` для вызывающего и `{user2}` для того, на кого направлено действие.

*Пример:* `{user1} пожал руку {user2}`", parse_mode="Markdown")
            return
            
        elif isinstance(state, dict) and state.get('step') == 'wait_rp_template':
            cmd_name = state['name']
            db["rp_commands"][cmd_name] = text
            db["states"].pop(user_id, None)
            bot.send_message(user_id, f"✅ РП-команда `{cmd_name}` успешно добавлена!", parse_mode="Markdown")
            return

    # Обработка кликов по кнопкам меню
    if text == "➕ Назначить админа":
        db["states"][user_id] = 'wait_admin_id'
        bot.send_message(user_id, "Перешлите сообщение нового админа, введите его Telegram ID цифрами или укажите его @username (например, @username):
Для отмены напишите 'отмена'.")
        
    elif text == "🛠 Добавить РП-команду":
        db["states"][user_id] = 'wait_rp_name'
        bot.send_message(user_id, "Шаг 1: Введите триггерное слово для команды (одним словом, например: *ударить* или *кусь*):", parse_mode="Markdown")
        
    elif text == "📋 Список РП-команд":
        cmds = "
".join([f"• *{k}* — {v}" for k, v in db["rp_commands"].items()])
        bot.send_message(user_id, f"📋 *Текущие РП-команды:*

{cmds}", parse_mode="Markdown")
        
    elif text == "👑 Список админов":
        admins_list = "
".join([f"• ID: `{a}`" for a in db["admins"]])
        usernames_list = "
".join([f"• @{u}" for u in db["admin_usernames"]])
        bot.send_message(user_id, f"👑 *Администраторы бота:*

*По ID:*
{admins_list}

*По юзернеймам:*
{usernames_list}", parse_mode="Markdown")

# Запуск бота
if __name__ == '__main__':
    print("Бот успешно запущен...")
    bot.infinity_polling()
