import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
import urllib.parse  # Нужно для красивого формирования текста в ссылке

# Токен твоего бота от BotFather
TOKEN = "8755527072:AAH4iXe_o1zHRm7_D0mxm8otePrZihQrYew"
SUPPORT_USERNAME = "rockboostsupport"

# Состояния для FSM
class OrderState(StatesGroup):
    waiting_for_link = State()
    waiting_for_quantity = State()

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База услуг с ценами в грн
SERVICES = {
    "tg": {
        "name": "Telegram", 
        "items": {
            "tg_subs": {"name": "Подписчики в канал", "price_1000": 150},
            "tg_views": {"name": "Просмотры постов", "price_1000": 20},
            "tg_reactions": {"name": "Реакции на посты", "price_1000": 30}
        }
    },
    "insta": {
        "name": "Instagram", 
        "items": {
            "insta_subs": {"name": "Подписчики", "price_1000": 200},
            "insta_likes": {"name": "Лайки", "price_1000": 50},
            "insta_views": {"name": "Просмотры сторис/видео", "price_1000": 15}
        }
    },
    "tiktok": {
        "name": "TikTok", 
        "items": {
            "tt_views": {"name": "Просмотры TikTok", "price_1000": 24},
            "tt_subs": {"name": "Подписчики TikTok", "price_1000": 350},
            "tt_likes": {"name": "Лайки TikTok", "price_1000": 120}
        }
    },
    "youtube": {
        "name": "YouTube", 
        "items": {
            "yt_views": {"name": "Просмотры YouTube", "price_1000": 300},
            "yt_subs": {"name": "Подписчики YouTube", "price_1000": 900}
        }
    }
}

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    start_text = urllib.parse.quote("Здравствуйте! Хочу задать вопрос по накрутке.")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Выбрать услугу (Каталог)", callback_data="make_order")],
        [InlineKeyboardButton(text="💬 Написать поддержке", url=f"https://t.me/{SUPPORT_USERNAME}?text={start_text}")],
        [InlineKeyboardButton(text="🌐 Наш сайт Rock-Boost", url="https://rock-boost.com.ua/ru/")]
    ])
    
    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "🔥 Добро пожаловать в официальный Telegram-бот сервиса накрутки **Rock-Boost**.\n"
        "Выберите нужное действие в меню ниже:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# Главное меню выбора соцсетей
@dp.callback_query(F.data == "make_order")
async def choose_platform(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔵 Telegram", callback_data="plat_tg"),
         InlineKeyboardButton(text="📸 Instagram", callback_data="plat_insta")],
        [InlineKeyboardButton(text="🎵 TikTok", callback_data="plat_tiktok"),
         InlineKeyboardButton(text="📺 YouTube", callback_data="plat_youtube")],
        [InlineKeyboardButton(text="🔙 Главное меню", callback_data="back_to_start")]
    ])
    await callback.message.edit_text("📱 **Выберите социальную сеть из каталога:**", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# Выбор конкретной категории услуг для платформы
@dp.callback_query(F.data.startswith("plat_"))
async def choose_service_type(callback: CallbackQuery, state: FSMContext):
    plat_key = callback.data.split("_")[1]
    await state.update_data(platform=plat_key)
    
    plat_data = SERVICES[plat_key]
    
    buttons = []
    for service_code, s_info in plat_data["items"].items():
        buttons.append([InlineKeyboardButton(text=f"{s_info['name']} ({s_info['price_1000']} грн / 1000 шт)", callback_data=f"srv_{service_code}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад к соцсетям", callback_data="make_order")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(f"⚙️ **Услуги для {plat_data['name']}:**\nВыберите интересующую позицию:", reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# Сохранение услуги и запрос ссылки
@dp.callback_query(F.data.startswith("srv_"))
async def ask_for_link(callback: CallbackQuery, state: FSMContext):
    service_code = callback.data.split("_", 1)[1]
    
    selected_service = None
    for plat in SERVICES.values():
        if service_code in plat["items"]:
            selected_service = plat["items"][service_code]
            break
            
    await state.update_data(service_name=selected_service["name"], price_1000=selected_service["price_1000"])
    
    await callback.message.edit_text(
        f"🔗 Вы выбрали: <b>{selected_service['name']}</b>\n\n"
        "Отправьте в чат ссылку на ваш профиль, видео или пост:",
        parse_mode="HTML"
    )
    await state.set_state(OrderState.waiting_for_link)
    await callback.answer()

# Получение ссылки -> запрос количества
@dp.message(OrderState.waiting_for_link)
async def process_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await message.answer("🔢 Введите количество (минимальный заказ от 100 шт, например: 500, 1000, 5000):")
    await state.set_state(OrderState.waiting_for_quantity)

# Получение количества -> расчет и вывод реквизитов менеджера с авто-текстом
@dp.message(OrderState.waiting_for_quantity)
async def process_quantity(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Введите корректное число (например, 1000):")
        return
    
    quantity = int(message.text)
    if quantity < 100:
        await message.answer("⚠️ Минимальное количество для заказа — 100 штук. Попробуйте ввести большее число:")
        return
        
    data = await state.get_data()
    price_1000 = data['price_1000']
    
    total_price = round((quantity / 1000) * price_1000, 2)
    
    order_message = (
        f"Здравствуйте! Я хочу оплатить заказ:\n\n"
        f"🛠 Услуга: {data['service_name']}\n"
        f"🔗 Ссылка: {data['link']}\n"
        f"📊 Количество: {quantity} шт.\n"
        f"💰 Сумма: {total_price} грн\n\n"
        f"Жду реквизиты для оплаты!"
    )
    
    encoded_text = urllib.parse.quote(order_message)
    
    summary_text = (
        f"📝 <b>Ваш заказ успешно сформирован!</b>\n\n"
        f"🛠 Услуга: <b>{data['service_name']}</b>\n"
        f"🔗 Ссылка: <code>{data['link']}</code>\n"
        f"📊 Количество: <b>{quantity} шт.</b>\n"
        f"💰 <b>Сумма к оплате: {total_price} грн</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <b>Инструкция по оплате:</b>\n"
        f"Нажмите кнопку ниже — у вас автоматически откроется чат с менеджером <b>@{SUPPORT_USERNAME}</b> и вставится готовое сообщение с деталями заказа. Вам останется только отправить его и получить реквизиты!"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить / Отправить заказ менеджеру", url=f"https://t.me/{SUPPORT_USERNAME}?text={encoded_text}")],
        [InlineKeyboardButton(text="🔄 Сделать новый заказ", callback_data="make_order")]
    ])
    
    await message.answer(summary_text, reply_markup=keyboard, parse_mode="HTML")
    await state.clear()

# Возврат в начало через callback
@dp.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    start_text = urllib.parse.quote("Здравствуйте! Хочу задать вопрос по накрутке.")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Выбрать услугу (Каталог)", callback_data="make_order")],
        [InlineKeyboardButton(text="💬 Написать поддержке", url=f"https://t.me/{SUPPORT_USERNAME}?text={start_text}")],
        [InlineKeyboardButton(text="🌐 Наш сайт Rock-Boost", url="https://rock-boost.com.ua/ru/")]
    ])
    await callback.message.edit_text(
        "👋 Главное меню бота <b>Rock-Boost</b>. Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот Rock-Boost запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())