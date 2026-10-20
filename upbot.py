# -*- coding: utf-8 -*-
import os
import telebot
from telebot import types
from dotenv import load_dotenv
# Загружаем токен
load_dotenv()
TOKEN = os.getenv("8839559401:AAGk52ypE-mMDXFmDqh4AAftbcFUWqAEgxs")
bot = telebot.TeleBot(TOKEN)
# База данных бота
db = {
    "super_admin": "lytixx",  # Главный админ
    "admins": set(),          # ID дополнительных админов
    "users": {},              # Статистика сообщений и наград
    "rp_commands": {          # Базовые РП-команды
        "обнять": "🤗 {user1} крепко обнял {user2}",
        "поцеловать": "😘 {user1} нежно поцеловал {user2}",
        "ударить": "👊 {user1} дал леща {user2}",
        "укусить": "🦷 {user1} сделал кусь {user2}"
    }
}

user_states = {}

def is_admin(user):
    """Проверяет, является ли пользователь администратором бота."""
    is_super = user.username and user.username.lower() == db["super_admin"].lower()
    return is_super or user.id in db["admins"]

def init_user(user):
    """Создает запись о пользователе, если её нет."""
    if user.id not in db["users"]:
        db["users"][user.id] = {
            "username": f"@{user.username}" if user.username else user.first_name,
            "messages": 0,
            "rewards": []
        }

# --- АДМИН-ПАНЕЛЬ В ЛС БОТА ---
@bot.message_handler(chats_types=['private'])
def private_menu(message):
    if not is_admin(message.from_user):
        bot.reply_to(message, "❌ У вас нет доступа к админ-панели.")
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Назначить админа", "📜 Список РП-команд")
    bot.send_message(message.chat.id, "👑 **Админ-панель открыта:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(chats_types=['private'], func=lambda m: m.text in ["➕ Назначить админа", "📜 Список РП-команд"])
def admin_actions(message):
    if not is_admin(message.from_user): return
    if message.text == "📜 Список РП-команд":
        text = "📝 **РП-команды:**\n" + "\n".join([f"• *{k}*" for k in db["rp_commands"].keys()])
        bot.send_message(message.chat.id, text, parse_mode="Markdown")
    elif message.text == "➕ Назначить админа":
        user_states[message.from_user.id] = "wait_admin_id"
        bot.send_message(message.chat.id, "Отправьте числовой **Telegram ID** нового администратора:")

@bot.message_handler(chats_types=['private'], func=lambda m: m.from_user.id in user_states)
def handle_admin_input(message):
    state = user_states[message.from_user.id]
    if state == "wait_admin_id":
        try:
            new_id = int(message.text.strip())
            db["admins"].add(new_id)
            bot.send_message(message.chat.id, f"✅ Админ с ID `{new_id}` добавлен!", parse_mode="Markdown")
        except ValueError:
            bot.send_message(message.chat.id, "❌ Ошибка! Введите числовой ID.")
        del user_states[message.from_user.id]

# --- РАБОТА В ГРУППАХ ---
@bot.message_handler(chats_types=['group', 'supergroup'])
def handle_group(message):
    init_user(message.from_user)
    db["users"][message.from_user.id]["messages"] += 1
    
    text = message.text.strip() if message.text else ""
    if not text: return
    text_lower = text.lower()

    # 1. Административная команда !Закреп
    if text_lower == "!закреп":
        if not message.reply_to_message:
            bot.reply_to(message, "❌ Ответьте этой командой на сообщение, которое нужно закрепить.")
            return
        try:
            bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
            bot.reply_to(message, "📌 Сообщение успешно закреплено!")
        except Exception:
            bot.reply_to(message, "❌ Ошибка закрепления. Проверьте права бота.")
        return

    # 2. Награждение !наградить [название]
    if text_lower.startswith("!наградить"):
        if not is_admin(message.from_user):
            bot.reply_to(message, "❌ Только админы могут выдавать награды.")
            return
        if not message.reply_to_message:
            bot.reply_to(message, "❌ Ответьте на сообщение пользователя.")
            return
        reward = text[10:].strip()
        if not reward:
            bot.reply_to(message, "❌ Укажите название награды после команды.")
            return
        target = message.reply_to_message.from_user
        init_user(target)
        db["users"][target.id]["rewards"].append(reward)
        bot.reply_to(message, f"🏅 {db['users'][target.id]['username']} получил награду: **{reward}**!", parse_mode="Markdown")
        return

    # 3. Команда Профиль / Стата
    if text_lower in ["стата", "профиль"]:
        data = db["users"][message.from_user.id]
        rewards = ", ".join(data["rewards"]) if data["rewards"] else "Отсутствуют"
        info = f"👤 **Профиль:** {data['username']} | 📊 **Сообщений:** `{data['messages']}` | 🏅 **Награды:** {rewards}"
        bot.reply_to(message, info, parse_mode="Markdown")
        return

    # 4. Команда Топ
    if text_lower == "топ":
        if not db["users"]:
            bot.send_message(message.chat.id, "📊 Статистика пуста.")
            return
        sorted_users = sorted(db["users"].items(), key=lambda x: x["messages"], reverse=True)[:10]
        top_text = "📊 **Топ-10 актива чата:**\n\n"
        for i, (u_id, u_data) in enumerate(sorted_users, 1):
            top_text += f"{i}. {u_data['username']} — `{u_data['messages']}` собщ.\n"
        bot.send_message(message.chat.id, top_text, parse_mode="Markdown")
        return

    # 5. Интерактивные РП-команды
    cmd = text_lower.split()[0]
    if cmd in db["rp_commands"]:
        if not message.reply_to_message:
            bot.reply_to(message, f"❌ Ответьте командой `{cmd}` на чьё-то сообщение!")
            return
        u1 = db["users"][message.from_user.id]["username"]
        target = message.reply_to_message.from_user
        init_user(target)
        u2 = db["users"][target.id]["username"]
        
        response = db["rp_commands"][cmd].format(user1=u1, user2=u2)
        bot.send_message(message.chat.id, response)

print("Бот с админкой и закрепом успешно запущен!")
bot.infinity_polling()
