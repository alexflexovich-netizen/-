import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import aiosqlite


class CalcStates(StatesGroup):
    waiting_for_number = State()
    waiting_for_tax = State()


API_TOKEN = "8657863182:AAFw2qWdGe7rY3TpVGCnjyAuTwCM5seyLyQ"
bot = Bot(token = API_TOKEN)
dp = Dispatcher()

user_rates = {}

async def init_db():
    async with aiosqlite.connect("itis_freelance.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, income INTEGER, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        await db.commit()


@dp.message(Command("start"))
async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Hello, im calculator. Give me a number.")
    await state.set_state(CalcStates.waiting_for_number)


@dp.message(Command("history"))
async def history_command(message: types.Message, state: FSMContext):
    await state.clear()
    async with aiosqlite.connect("itis_freelance.db") as db:
        cursor = await db.execute("""SELECT income FROM history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5""", (message.from_user.id,))
        rows = await cursor.fetchall()
        if rows:
            his_text = "Последние расчеты: \n\n"
            for row in rows:
                his_text += f"✅ {row[0]} рублей. \n"
            await message.answer(his_text)
        else:
            await message.answer("history is empty, calc something before call history-func)")


@dp.message(CalcStates.waiting_for_number)
async def handler_number(message: types.Message, state: FSMContext):
    user_rate = 500
    try:
        number = int(message.text)
        await state.update_data(dirty = number * user_rate)
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text = "Самозанятый 6%", callback_data = "tax_6"))
        builder.row(types.InlineKeyboardButton(text="Физлицо 13%", callback_data="tax_13"))
        await message.answer("Сумма есть, теперь выбери ставку.", reply_markup = builder.as_markup())
        await state.set_state(CalcStates.waiting_for_tax)
    except ValueError:
        await message.answer("я не понимаю буквы, пришли мне цифры)")


@dp.callback_query(CalcStates.waiting_for_tax, lambda c: c.data == "tax_6")
async def taxing_6(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    money = data.get("dirty", 0)
    result = int(money * 0.94)
    async with aiosqlite.connect("itis_freelance.db") as db:
        await db.execute("INSERT INTO history (user_id, income) VALUES (?, ?)", (callback.from_user.id, result))
        await db.commit()
    await callback.answer()
    await callback.message.answer(f"При ставке 6% чистыми: {result} руб.")
    await state.clear()


@dp.callback_query(CalcStates.waiting_for_tax, lambda c: c.data == "tax_13")
async def taxing_13(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    money = data.get("dirty", 0)
    result = int(money * 0.87)
    async with aiosqlite.connect("itis_freelance.db") as db:
        await db.execute("INSERT INTO history (user_id, last_income) VALUES (?, ?)", (callback.from_user.id, result))
        await db.commit()
    await callback.answer()
    await callback.message.answer(f"При ставке 13% чистыми: {result} руб.")
    await state.clear()


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main( ))