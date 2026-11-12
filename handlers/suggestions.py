import html
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from config import ADMIN_ID
from database.db import (
    create_quest_suggestion,
    approve_quest_suggestion,
    reject_quest_suggestion,
    get_or_create_user
)
from keyboards.inline import (
    get_category_select_keyboard,
    get_admin_moderation_keyboard,
    SUGGESTION_CATEGORIES
)

router = Router()


class SuggestQuestState(StatesGroup):
    waiting_for_category = State()
    waiting_for_text = State()


@router.message(F.text == "💡 Предложить квест")
@router.message(Command("suggest"))
async def start_suggest_quest(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await get_or_create_user(user_id, message.from_user.username, message.from_user.first_name)
    await state.clear()

    text = (
        "💡 <b>Предложи свой квест для Daystep!</b>\n\n"
        "Лучшие задания попадают в общую базу игры, и их выполняют все участники.\n"
        "Если твой квест будет одобрен — ты получишь в награду <b>+1 ❄️ Заморозку стрика</b>!\n\n"
        "<b>Шаг 1 из 2:</b> Выбери категорию задания ниже 👇"
    )
    await state.set_state(SuggestQuestState.waiting_for_category)
    await message.answer(text, reply_markup=get_category_select_keyboard())


@router.callback_query(F.data == "sug_cat:cancel", SuggestQuestState.waiting_for_category)
async def cancel_suggest_cat(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Предложение квеста отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("sug_cat:"), SuggestQuestState.waiting_for_category)
async def handle_category_chosen(callback: CallbackQuery, state: FSMContext):
    cat_idx = int(callback.data.split(":")[1])
    if cat_idx >= len(SUGGESTION_CATEGORIES):
        await callback.answer("Ошибка выбора категории.")
        return

    chosen_category = SUGGESTION_CATEGORIES[cat_idx]
    await state.update_data(category=chosen_category)
    await state.set_state(SuggestQuestState.waiting_for_text)

    text = (
        f"🏷 Выбранная категория: <b>{chosen_category}</b>\n\n"
        "<b>Шаг 2 из 2:</b> Напиши название и краткое описание задания одним сообщением.\n\n"
        "<i>Пример:</i>\n"
        "<b>Приготовить полезный смузи</b>\n"
        "Сделать смузи из банана, шпината и яблока на воде или растительном молоке."
    )
    await callback.message.edit_text(text)
    await callback.answer()


@router.message(SuggestQuestState.waiting_for_text)
async def handle_quest_text(message: Message, state: FSMContext, bot: Bot):
    user_text = message.text.strip()
    if len(user_text) < 10:
        await message.answer("⚠️ Описание слишком короткое. Пожалуйста, напиши подробнее название и суть задания:")
        return

    data = await state.get_data()
    category = data.get("category", "✨ Разное")
    await state.clear()

    # Делим текст на заголовок и описание (первая строка — заголовок, остальное — описание)
    lines = [line.strip() for line in user_text.split("\n") if line.strip()]
    title = lines[0][:100]
    description = "\n".join(lines[1:]) if len(lines) > 1 else lines[0]
    description = description[:500]

    user_id = message.from_user.id
    suggestion_id = await create_quest_suggestion(user_id, category, title, description)

    safe_title = html.escape(title)
    safe_desc = html.escape(description)
    safe_cat = html.escape(category)

    user_confirm = (
        "🎉 <b>Спасибо за идею! Заявка отправлена!</b>\n\n"
        f"🏷 <b>Категория:</b> {safe_cat}\n"
        f"📌 <b>Заголовок:</b> {safe_title}\n"
        f"📝 <b>Описание:</b> {safe_desc}\n\n"
        "Как только админ одобрит квест, ты получишь уведомление и <b>+1 ❄️ заморозку</b>!"
    )
    await message.answer(user_confirm)

    # Если ADMIN_ID настроен — отправляем админу карточку на модерацию
    if ADMIN_ID and ADMIN_ID > 0:
        username_str = f"@{message.from_user.username}" if message.from_user.username else f"ID {user_id}"
        admin_card = (
            f"💡 <b>Новое предложение квеста от {username_str}</b>\n\n"
            f"🏷 <b>Категория:</b> {safe_cat}\n"
            f"📌 <b>Название:</b> <b>{safe_title}</b>\n\n"
            f"📝 <b>Описание:</b>\n{safe_desc}"
        )
        try:
            await bot.send_message(
                ADMIN_ID,
                admin_card,
                reply_markup=get_admin_moderation_keyboard(suggestion_id)
            )
        except Exception as e:
            # Если бот не может написать админу (например, админ еще не нажал /start)
            pass


# --- Кнопки модерации для админа ---

@router.callback_query(F.data.startswith("mod:app:"))
async def handle_admin_approve(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ У вас нет прав модератора.", show_alert=True)
        return

    suggestion_id = int(callback.data.split(":")[2])
    approved = await approve_quest_suggestion(suggestion_id)

    if not approved:
        await callback.answer("Заявка уже была обработана или не найдена.", show_alert=True)
        return

    title_escaped = html.escape(approved['title'])
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"✅ <b>ОДОБРЕНО И ДОБАВЛЕНО В БАЗУ КВЕСТОВ!</b>\n"
        f"<i>(Автору начислена +1 ❄️ заморозка)</i>"
    )
    await callback.answer("Квест одобрен!")

    # Уведомляем автора квеста о победе
    try:
        author_notice = (
            "🎉 <b>Отличная новость! Твой квест одобрен!</b>\n\n"
            f"Задание «<b>{title_escaped}</b>» добавлено в общую базу Daystep!\n"
            "В знак благодарности тебе начислена <b>+1 ❄️ Заморозка стрика</b>!\n\n"
            "Спасибо за помощь в развитии проекта! 🚀"
        )
        await bot.send_message(approved["user_id"], author_notice)
    except Exception:
        pass


@router.callback_query(F.data.startswith("mod:rej:"))
async def handle_admin_reject(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("⛔️ У вас нет прав модератора.", show_alert=True)
        return

    suggestion_id = int(callback.data.split(":")[2])
    rejected = await reject_quest_suggestion(suggestion_id)

    if not rejected:
        await callback.answer("Заявка уже была обработана или не найдена.", show_alert=True)
        return

    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        "❌ <b>ОТКЛОНЕНО.</b>"
    )
    await callback.answer("Квест отклонен.")
