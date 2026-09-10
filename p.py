import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = "8808164211:AAHgw9a1GD97uKjVa9kI0S3bo5N7GtHb-lg"
BS_API_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiIsImtpZCI6IjI4YTMxOGY3LTAwMDAtYTFlYi03ZmExLTJjNzQzM2M2Y2NhNSJ9.eyJpc3MiOiJzdXBlcmNlbGwiLCJhdWQiOiJzdXBlcmNlbGw6Z2FtZWFwaSIsImp0aSI6IjFmYjllOWFhLTAzZWUtNGE1My1hMzNhLWRkYzI1ZGVlYzA4YyIsImlhdCI6MTc4OTA1NzkyNCwic3ViIjoiZGV2ZWxvcGVyLzg1YzE2MGJhLWIzYTctNGRjOS04MDExLWU5YjUzZmI1ZDVhZiIsInNjb3BlcyI6WyJicmF3bHN0YXJzIl0sImxpbWl0cyI6W3sidGllciI6ImRldmVsb3Blci9zaWx2ZXIiLCJ0eXBlIjoidGhyb3R0bGluZyJ9LHsiY2lkcnMiOlsiMTc4LjIxNi4yMjUuNzEiXSwidHlwZSI6ImNsaWVudCJ9XX0.rKRWHiE_9NqrGUjHbQg0ZRZDPVyAlTaEy4tGa5mDOTqEQEN6drdXX1wVs2sUEyuT6ojZEkzBtECb-GpbAEwgKA"

# Вкажи свій Telegram ID для доступу до /admin
ADMIN_ID = 123456789 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

users_db = set()

class ProfileState(StatesGroup):
    language = State()
    waiting_for_tag = State()
    broadcast_text = State()

lang_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ]
    ]
)

def calculate_price(trophies, brawlers_count, p11_count, hypercharges):
    price_uah = (trophies * 0.015) + (brawlers_count * 5) + (p11_count * 15) + (hypercharges * 20)
    price_rub = price_uah * 2.4
    return int(price_uah), int(price_rub)

@dp.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    users_db.add(message.from_user.id)
    await message.answer("Обери мову / Выберите язык:", reply_markup=lang_keyboard)
    await state.set_state(ProfileState.language)

@dp.callback_query(ProfileState.language, F.data.startswith("lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    await state.update_data(lang=lang)
    
    text = "Введіть тег гравця Brawl Stars (наприклад, #2UY90GV8Q0):" if lang == "ua" else "Введите тег игрока Brawl Stars (например, #2UY90GV8Q0):"
    await callback.message.edit_text(text)
    await state.set_state(ProfileState.waiting_for_tag)

@dp.message(ProfileState.waiting_for_tag)
async def get_brawl_profile(message: Message, state: FSMContext):
    user_data = await state.get_data()
    lang = user_data.get("lang", "ua")
    
    tag = message.text.strip().upper().replace("O", "0")
    if not tag.startswith("#"):
        tag = "#" + tag
    
    encoded_tag = tag.replace("#", "%23")
    url = f"https://api.brawlstars.com/v1/players/{encoded_tag}"
    headers = {
        "Authorization": f"Bearer {BS_API_TOKEN}",
        "Accept": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                
                name = data.get("name", "Невідомо")
                trophies = data.get("trophies", 0)
                highest_trophies = data.get("highestTrophies", 0)
                v_3vs3 = data.get("3vs3Victories", 0)
                v_solo = data.get("soloVictories", 0)
                v_duo = data.get("duoVictories", 0)
                brawlers = data.get("brawlers", [])
                club_name = data.get("club", {}).get("name", "Немає / Нет")
                icon_id = data.get("icon", {}).get("id", 28000000)
                
                sorted_brawlers = sorted(brawlers, key=lambda x: x.get("trophies", 0), reverse=True)
                top_3 = sorted_brawlers[:3]
                top_str = ", ".join([f"**{b.get('name')}** ({b.get('trophies')}🏆)" for b in top_3])
                
                next_goal = ((trophies // 5000) + 1) * 5000
                to_goal = next_goal - trophies

                p11_count = sum(1 for b in brawlers if b.get("power", 1) == 11)
                star_powers = sum(len(b.get("starPowers", [])) for b in brawlers)
                gadgets = sum(len(b.get("gadgets", [])) for b in brawlers)
                hypercharges = sum(1 for b in brawlers if any("HYPERCHARGE" in g.get("name", "").upper() for g in b.get("gears", [])))

                price_uah, price_rub = calculate_price(trophies, len(brawlers), p11_count, hypercharges)
                icon_url = f"https://cdn.brawlify.com/profile-icons/regular/{icon_id}.png"
                
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(text="📜 Список бійців" if lang == "ua" else "📜 Список бойцов", callback_data=f"brawlers_{encoded_tag}"),
                            InlineKeyboardButton(text="⚔️ Останні бої" if lang == "ua" else "⚔️ Последние бои", callback_data=f"battles_{encoded_tag}")
                        ]
                    ]
                )
                
                if lang == "ua":
                    caption = (
                        f"👤 **Гравець:** {name}\n"
                        f"🏷 **Тег:** {tag}\n\n"
                        f"🏆 **Кубки:** {trophies} (Рекорд: {highest_trophies})\n"
                        f"🎯 **До {next_goal} 🏆 залишилось:** {to_goal}\n\n"
                        f"🔥 **Топ-3 Мейни:** {top_str}\n"
                        f"🥊 **Перемоги:** 3v3: {v_3vs3} | Соло: {v_solo} | Дуо: {v_duo}\n\n"
                        f"🤖 **Бійці:** {len(brawlers)}/107\n"
                        f"⚡ **11 Сила:** {p11_count} | 🟣 **Гіперзаряди:** ~{hypercharges}\n"
                        f"⭐ **Пасивки:** {star_powers} | 🟢 **Ґаджети:** {gadgets}\n"
                        f"🛡 **Клуб:** {club_name}\n\n"
                        f"💰 **Оцінка вартості:** ~{price_uah} грн / ~{price_rub} руб"
                    )
                else:
                    caption = (
                        f"👤 **Игрок:** {name}\n"
                        f"🏷 **Тег:** {tag}\n\n"
                        f"🏆 **Кубки:** {trophies} (Рекорд: {highest_trophies})\n"
                        f"🎯 **До {next_goal} 🏆 осталось:** {to_goal}\n\n"
                        f"🔥 **Топ-3 Мейны:** {top_str}\n"
                        f"🥊 **Победы:** 3v3: {v_3vs3} | Соло: {v_solo} | Дуо: {v_duo}\n\n"
                        f"🤖 **Бойцы:** {len(brawlers)}/107\n"
                        f"⚡ **11 Сила:** {p11_count} | 🟣 **Гиперзаряды:** ~{hypercharges}\n"
                        f"⭐ **Пассивки:** {star_powers} | 🟢 **Гаджеты:** {gadgets}\n"
                        f"🛡 **Клуб:** {club_name}\n\n"
                        f"💰 **Оценка стоимости:** ~{price_uah} грн / ~{price_rub} руб"
                    )
                    
                await message.answer_photo(photo=icon_url, caption=caption, reply_markup=kb, parse_mode="Markdown")
            elif response.status == 404:
                err_msg = "❌ Тег не знайдено." if lang == "ua" else "❌ Тег не найден."
                await message.answer(err_msg)
            else:
                err_msg = f"❌ Помилка API Supercell ({response.status})" if lang == "ua" else f"❌ Ошибка API Supercell ({response.status})"
                await message.answer(err_msg)
                
    await state.clear()

@dp.callback_query(F.data.startswith("brawlers_"))
async def show_brawlers(callback: CallbackQuery):
    encoded_tag = callback.data.split("_")[1]
    url = f"https://api.brawlstars.com/v1/players/{encoded_tag}"
    headers = {"Authorization": f"Bearer {BS_API_TOKEN}", "Accept": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                brawlers = sorted(data.get("brawlers", []), key=lambda x: x.get("trophies", 0), reverse=True)
                
                text_lines = [f"🤖 **Список бійців ({len(brawlers)}):**\n"]
                for b in brawlers:
                    text_lines.append(f"• **{b.get('name')}** — 🏆 {b.get('trophies')} (Power {b.get('power')})")
                
                full_text = "\n".join(text_lines)
                if len(full_text) > 4000:
                    for i in range(0, len(full_text), 4000):
                        await callback.message.answer(full_text[i:i+4000], parse_mode="Markdown")
                else:
                    await callback.message.answer(full_text, parse_mode="Markdown")
                await callback.answer()

@dp.callback_query(F.data.startswith("battles_"))
async def show_battlelog(callback: CallbackQuery):
    encoded_tag = callback.data.split("_")[1]
    url = f"https://api.brawlstars.com/v1/players/{encoded_tag}/battlelog"
    headers = {"Authorization": f"Bearer {BS_API_TOKEN}", "Accept": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                items = data.get("items", [])[:5]
                
                if not items:
                    await callback.answer("Історія боїв порожня", show_alert=True)
                    return

                text = "⚔️ **Останні 5 боїв:**\n\n"
                for item in items:
                    battle = item.get("battle", {})
                    mode = battle.get("mode", "Режим").capitalize()
                    result = battle.get("result", battle.get("rank", "Н/Д"))
                    
                    res_icon = "🟢 Перемога" if result == "victory" else "🔴 Поразка" if result == "defeat" else f"🏅 Місце: {result}"
                    trophy_change = battle.get("trophyChange", 0)
                    tr_str = f"({'+' if trophy_change > 0 else ''}{trophy_change} 🏆)" if trophy_change != 0 else ""
                    
                    text += f"🎮 **{mode}** | {res_icon} {tr_str}\n"
                
                await callback.message.answer(text, parse_mode="Markdown")
                await callback.answer()

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer(f"👑 **Адмін-панель**\n\n👥 Користувачів у боті: **{len(users_db)}**\n\nДля розсилки введи `/broadcast`", parse_mode="Markdown")

@dp.message(Command("broadcast"))
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await message.answer("Введи текст повідомлення для розсилки:")
    await state.set_state(ProfileState.broadcast_text)

@dp.message(ProfileState.broadcast_text)
async def broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    count = 0
    for u_id in users_db:
        try:
            await bot.send_message(u_id, message.text)
            count += 1
        except Exception:
            pass
    await message.answer(f"✅ Розсилку завершено! Отримали {count} користувачів.")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())