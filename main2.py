import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot
import asyncio

from hooks import send_to_ai

API_TOKEN = "8009070541:AAEZNsDkGA9tBd5JheaMHrbytzI3jLyFVW8"
bot = AsyncTeleBot(API_TOKEN)

# Создаем позиции меню в виде словарей
menu_data = {
    "Пицца": {"Маргарита": 400, "Пепперони": 450, "Четыре сыра": 500, "Ветчина грибы": 550},
    "Суши": {"Филадельфия": 600, "Калифорния": 550, "Унаги": 650},
    "Суп": {"Борщ": 300, "Солянка": 350, "Грибной": 250},
    "Напитки": {"Кола": 100, "Вода": 80, "Сок": 120, "Чай": 100}
}

# Используем словарь для хранения состояния каждого пользователя
user_states = {}

def get_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = {
            "current_section": None,
            "cart": {},
            "last_message": None
        }
    return user_states[user_id]

# Формируем разделы меню
def build_menu_keyboard(items, prices):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in items:
        price = prices[item]
        text = f"{item} - {price}₽"
        markup.add(types.InlineKeyboardButton(text=text, callback_data=f"add:{item}"))
    markup.add(types.InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_categories"))
    return markup

# Формируем внешний вид корзины
# Реализуем функции удаления и добавления объектов в корзине
def build_cart_keyboard(cart):
    markup = types.InlineKeyboardMarkup(row_width=1)

    for item, qty in cart.items():
        price = None
        for section in menu_data.values():
            if item in section:
                price = section[item]
                break

        if price is None:
            continue

        row = []
        row.append(types.InlineKeyboardButton(
            text=f"➖ {item}",
            callback_data=f"remove_one:{item}"
        ))
        row.append(types.InlineKeyboardButton(
            text=f"{qty} шт",
            callback_data=f"show_item:{item}"
        ))
        row.append(types.InlineKeyboardButton(
            text=f"➕ {item}",
            callback_data=f"add_one:{item}"
        ))
        markup.row(*row)

    markup.add(types.InlineKeyboardButton(
        text="❌ Очистить корзину",
        callback_data="clear_cart"
    ))
    markup.add(types.InlineKeyboardButton(
        text="✅ Оформить заказ",
        callback_data="checkout"
    ))
    markup.add(types.InlineKeyboardButton(
        text="⬅ Назад в меню",
        callback_data="menu"
    ))
    return markup

# Формируем информацию о стоимости позиций в корзине и итоговую стоимость заказа
def get_cart_text(cart):
    if not cart:
        return "🛒 Ваша корзина пуста."

    cart_text = "🛒 Ваша корзина:\n\n"
    total = 0

    for item, qty in cart.items():
        price = None
        for section in menu_data.values():
            if item in section:
                price = section[item]
                break

        if price is None:
            continue

        item_total = price * qty
        cart_text += f"▪ {item} - {qty} × {price}₽ = {item_total}₽\n"
        total += item_total

    cart_text += f"\n💰 Итого: {total}₽"
    return cart_text

# Формируем обновление корзины пользователя
async def update_cart_message(chat_id, message_id, user_state):
    cart = user_state["cart"]
    cart_text = get_cart_text(cart)
    markup = build_cart_keyboard(cart)

    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=cart_text,
            reply_markup=markup
        )
    # Обработчик ошибок
    except Exception as e:
        if "message is not modified" in str(e):
            pass
        else:
            print(f"Error updating cart message: {e}")

# Формируем кнопки главного меню
@bot.message_handler(commands=["start"])
async def start_message(message):
    user_state = get_user_state(message.from_user.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🍽 Меню", callback_data="menu"))
    markup.add(types.InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
    markup.add(types.InlineKeyboardButton("❓ Помощь", callback_data="help"))
    sent_message = await bot.send_message(
        message.chat.id,
        "Привет, я Рестобот! Выбери действие:",
        reply_markup=markup
    )
    user_state["last_message"] = sent_message.message_id

# Обработчик событий при нажатии на кнопки
@bot.callback_query_handler(func=lambda call: True)
async def handle_callback(call):
    user_id = call.from_user.id
    user_state = get_user_state(user_id)
    data = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    try:
        if data == "help":
            await bot.answer_callback_query(call.id)
            await bot.send_message(
                chat_id,
                "Я помогу тебе заказать еду!\n\n"
                "1. Нажми 'Меню' для выбора блюд\n"
                "2. Добавляй товары в корзину\n"
                "3. Перейди в корзину для оформления заказа\n"
                "4. А еще я умею искать позиции в меню. Отправь в чат '/find борщ' (или любое другое блюдо) и я постараюсь его найти!\n\n"
                "А если тебе нужна консультация или просто захочется поболтать, то пиши в чат всё, что хочешь! Я постараюсь ответить)"
            )

        elif data == "menu":
            user_state["current_section"] = None
            markup = types.InlineKeyboardMarkup(row_width=1)
            for section in menu_data.keys():
                markup.add(types.InlineKeyboardButton(
                    text=section,
                    callback_data=f"section:{section}"
                ))
            markup.add(types.InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="back"
            ))
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🍽 Выберите категорию:",
                reply_markup=markup
            )

        elif data.startswith("section:"):
            section = data.split(":")[1]
            user_state["current_section"] = section
            items = list(menu_data[section].keys())
            prices = menu_data[section]
            markup = build_menu_keyboard(items, prices)
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"🍴 {section}: Выберите блюдо",
                reply_markup=markup
            )

        elif data == "back_to_categories":
            user_state["current_section"] = None
            markup = types.InlineKeyboardMarkup(row_width=1)
            for section in menu_data.keys():
                markup.add(types.InlineKeyboardButton(
                    text=section,
                    callback_data=f"section:{section}"
                ))
            markup.add(types.InlineKeyboardButton(
                text="⬅ Назад",
                callback_data="back"
            ))
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🍽 Выберите категорию:",
                reply_markup=markup
            )

        elif data.startswith("add:"):
            item = data.split(":")[1]
            if item in user_state["cart"]:
                user_state["cart"][item] += 1
            else:
                user_state["cart"][item] = 1

            await bot.answer_callback_query(call.id, text=f"Добавлено: {item}")
            section = user_state["current_section"]
            items = list(menu_data[section].keys())
            prices = menu_data[section]
            markup = build_menu_keyboard(items, prices)

            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"🍴 {section}: Выберите блюдо",
                    reply_markup=markup
                )
            except Exception as e:
                if "message is not modified" not in str(e):
                    raise e

        elif data == "cart":
            await update_cart_message(chat_id, message_id, user_state)

        elif data.startswith("add_one:"):
            item = data.split(":")[1]
            if item in user_state["cart"]:
                user_state["cart"][item] += 1
            await update_cart_message(chat_id, message_id, user_state)
            await bot.answer_callback_query(call.id, text=f"Добавлен 1 {item}")

        elif data.startswith("remove_one:"):
            item = data.split(":")[1]
            if item in user_state["cart"]:
                user_state["cart"][item] -= 1
                if user_state["cart"][item] <= 0:
                    del user_state["cart"][item]

            if user_state["cart"]:
                await update_cart_message(chat_id, message_id, user_state)
            else:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🛒 Ваша корзина пуста."
                )
            await bot.answer_callback_query(call.id, text=f"Удален 1 {item}")

        elif data == "clear_cart":
            user_state["cart"].clear()
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="🛒 Корзина пуста."
            )
            await bot.answer_callback_query(call.id, text="Корзина очищена")

        elif data == "checkout":
            if not user_state["cart"]:
                await bot.answer_callback_query(call.id, text="Корзина пуста!", show_alert=True)
                return

            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="✅ Ваш заказ оформлен! Спасибо за покупку."
            )
            user_state["cart"].clear()

        elif data == "back":
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🍽 Меню", callback_data="menu"))
            markup.add(types.InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
            markup.add(types.InlineKeyboardButton("❓ Помощь", callback_data="help"))
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text="Главное меню:",
                reply_markup=markup
            )

    except Exception as e:
        print(f"Error in callback handler: {e}")
        await bot.answer_callback_query(call.id, text="Произошла ошибка, попробуйте еще раз")

# Реализация поиска по меню
@bot.message_handler(func=lambda m: True)
async def handle_text(message):
    if message.text.startswith('/find '):
        query = message.text[6:].lower()
        results = []

        for section, items in menu_data.items():
            for item, price in items.items():
                if query in item.lower():
                    results.append(f"{item} (В разделе: {section}) - {price}₽")

        if results:
            await bot.send_message(message.chat.id, "🔍 Результаты поиска:\n" + "\n".join(results))
        else:
            await bot.send_message(message.chat.id, "😕 Ничего не найдено")

# Реализация подключения ИИ
@bot.message_handler(func=lambda message: True)
async def fallback(message):
    response = send_to_ai(message.text)
    await bot.send_message(message.chat.id, response, parse_mode="Markdown")

asyncio.run(bot.polling())