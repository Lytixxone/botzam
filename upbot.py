# -*- coding: utf-8 -*-
import os
import telebot
from telebot import types
from dotenv import load_dotenv

# Автоматически загружает переменные из файла .env (если он есть локально)
load_dotenv()

# Безопасное получение токена из переменных окружения хостинга или .env
TOKEN = os.getenv("8839559401:AAGrbbdaiZ7vTJYWYQComfV0qfJW7JKW8MM")

if not TOKEN:
    raise ValueError(
        "❌ Критическая ошибка: Переменная BOT_TOKEN не задана!\n"
        "Пожалуйста, добавьте BOT_TOKEN в переменные окружения на вашем хостинге "
        "или создайте локальный файл .env"
    )

bot = telebot.TeleBot(TOKEN)

# Встроенная база данных в оперативной памяти (ОЗУ)
db = {
    "super_admin": "lytixx",  # Главный админ чата по юзернейму
    "admins": set(),          # ID дополнительных админов чата
    "users": {},              # Статистика: {user_id: {"username": str, "messages": int, "rewards": []}}
    "rp_commands": {          # Базовые РП команды по умолчанию
        "обкашлить": "{user1} обкашлил вопросы с {user2}",
        "трахнуть": "{user1} трахнул {user2}",
        "поцеловать": "{user1} нежно поцеловал {user2} 😘",
        "обнять": "{user1} крепко обнял {user2} 🤗",
        "ударить": "{user1} дал мощного леща {user2} 👊"
    }
}

user_states = {}

def is_admin(user):
    """Проверяет, является ли пользователь администратором бота."""
    is_super = user.username and user.username.lower() == db["super_admin"].lower()
    return is_super or user.id in db["admins"]

def init_user(user):
    """Инициализирует запись пользователя в локальной БД, если её нет."""
    if user.id not in db["users"]:
        db["users"][user.id] = {
            "username": f"@{user.username}" if user.username else user.first_name,
            "messages": 0,
            "rewards": []
        }
    if user.username:
        db["users"][user.id]["username"] = f"@{user.username}"

# --- ОБРАБОТЧИК ЛС БОТА (АДМИН-ПАНЕЛЬ) ---
@bot.message_handler(chats_types=['private'])
def private_menu(message):
    if not is_admin(message.from_user):
        bot.reply_to(message, "❌ У вас нет доступа к админ-панели этого бота.")
        return
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Назначить админа", "➕ Добавить РП-команду")
    markup.row("📜 Список РП-команд", "👑 Список админов")
    bot.send_message(message.chat.id, "👑 **Админ-панель открыта:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(chats_types=['private'], func=lambda m: m.text in ["➕ Назначить админа", "➕ Добавить РП-команду", "📜 Список РП-команд", "👑 Список админов"])
def admin_actions(message):
    if not is_admin(message.from_user): 
        return
        
    if message.text == "👑 Список админов":
        admins_list = ", ".join(map(str, db["admins"])) if db["admins"] else "нет"
        text = f"👑 **Главный админ:** @{db['super_admin']}\n\n**Доп. админы (ID):** {admins_list}"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        
    elif message.text == "📜 Список РП-команд":
        text = "📝 **Доступные РП-команды:**\n" + "\n".join([f"• *{k}*" for k in db["rp_commands"].keys()])
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
        
    elif message.text == "➕ Назначить админа":
        user_states[message.from_user.id] = "wait_admin_id"
        bot.send_message(message.chat.id, "Отправьте числовой **Telegram ID** нового администратора:")
        
    elif message.text == "➕ Добавить РП-команду":
        user_states[message.from_user.id] = "wait_rp_name"
        bot.send_message(message.chat.id, "Введите **слово-команду** (например: `укусить`):", parse_mode="Markdown")

@bot.message_handler(chats_types=['private'], func=lambda m: m.from_user.id in user_states)
def handle_admin_input(message):
    state = user_states[message.from_user.id]
    
    if state == "wait_admin_id":
        try:
            new_id = int(message.text.strip())
            db["admins"].add(new_id)
            bot.send_message(message.chat.id, f"✅ Администратор с ID `{new_id}` успешно добавлен!", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Ошибка! Нужно ввести именно числовой ID.")
        del user_states[message.from_user.id]
        
    elif state == "wait_rp_name":
        cmd_name = message.text.strip().lower()
        user_states[message.from_user.id] = f"wait_rp_template:{cmd_name}"
        bot.send_message(message.chat.id, "Введите шаблон ответа.\nИспользуйте `{user1}` для автора и `{user2}` для цели.\n\n*Пример:* `{user1} сделал кусь {user2}`", parse_mode="Markdown")
        
    elif state.startswith("wait_rp_template:"):
        cmd_name = state.split(":")[1]
        db["rp_commands"][cmd_name] = message.text.strip()
        bot.send_message(message.chat.id, f"✅ Кастомная РП-команда **{cmd_name}** создана!", parse_mode="Markdown")
        del user_states[message.from_user.id]

# --- ОБРАБОТЧИК ДЛЯ ГРУПП И ЧАТОВ ---
@bot.message_handler(chats_types=['group', 'supergroup'])
def group_messages(message):
    init_user(message.from_user)
    db["users"][message.from_user.id]["messages"] += 1
    
    text = message.text.strip() if message.text else ""
    if not text: 
        return

    # 1. Административная команда !Закреп
    if text.lower() == "!закреп":
        if not message.reply_to_message:
            bot.reply_to(message, "❌ Команда должна быть ответом на сообщение, которое нужно закрепить.")
            return
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Сообщение успешно закрепил!")
        except Exception:
            bot.reply_to(message, "❌ Не удалось закрепить. Проверьте, дали ли вы боту права Администратора.")
        return

    # 2. Награждение пользователей !наградить [текст]
    if text.lower().startswith("!наградить"):
        if not is_admin(message.from_user):
            bot.reply_to(message, "❌ Только администраторы бота могут выдавать награды.")
            return
        if not message.reply_to_message:
            bot.reply_to(message, "❌ Ответьте этой командой на сообщение того, кого хотите наградить.")
            return
            
        reward = text[10:].strip()
        if not reward:
            bot.reply_to(message, "❌ Укажите название награды. Пример: `!наградить Активист`")
            return
            
        target = message.reply_to_message.from_user
        init_user(target)
        db["users"][target.id]["rewards"].append(reward)
        bot.reply_to(message, f"🏅 Пользователь {db['users'][target.id]['username']} удостоен награды: **{reward}**!", parse_mode="Markdown")
        return

    # 3. Команды Профиль и Стата
    if text.lower() in ["стата", "профиль"]:
        data = db["users"][message.from_user.id]
        rewards = ", ".join(data["rewards"]) if data["rewards"] else "Отсутствуют"
        info = f"""👤 **Профиль:** {data['username']}\n📊 **Сообщений в чате:** `{data['messages']}`\n🏅 **Награды:** {rewards}"""
        bot.reply_to(message, info, parse_mode="Markdown")
        return

    # 4. Команда Топ актива
    if text.lower() == "топ":
        if not db["users"]:
            bot.send_message(message.chat.id, "📊 Статистика чата пока пуста.")
            return
        sorted_users = sorted(db["users"].items(), key=lambda x: x["messages"], reverse=True)[:10]
        top_text = "📊 **Топ-10 самых активных участников:**\n\n"
        for i, (u_id, data) in enumerate(sorted_users, 1):
            top_text += f"{i}. {data['username']} — `{data['messages']}` собщ.\n"
        bot.send_message(message.chat.id, top_text, parse_mode="Markdown")
        return

    # 5. Интерактивные РП-команды
    cmd = text.lower().split()[0] if text else ""
    if cmd in db["rp_commands"]:
        if not message.reply_to_message:
            bot.reply_to(message, f"❌ РП-команду `{cmd}` нужно использовать ответом на чьё-то сообщение!", parse_mode="Markdown")
            return
            
        u1 = db["users"][message.from_user.id]["username"]
        target = message.reply_to_message.from_user
        init_user(target)
        u2 = db["users"][target.id]["username"]
        
        # Рендерим шаблон
        try:
            response = db["rp_commands"][cmd].format(user1=u1, user2=u2)
            bot.send_message(message.chat.id, response)
        except KeyError:
            bot.send_message(message.chat.id, f"❌ Ошибка шаблона для команды {cmd}. Пересоздайте её через админку.")

print("Бот успешно инициализирован и запускается...")
bot.infinity_polling()
