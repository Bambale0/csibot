from __future__ import annotations

import html
import logging
from datetime import date, datetime, time
from io import BytesIO

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from csibot.bot_helpers import (
    format_bazi,
    format_comparison,
    format_vision_summary,
    image_bytes_to_data_url,
    parse_location_input,
)
from csibot.config import Settings
from csibot.domain.bazi import BaZiCalculator
from csibot.domain.qimen import (
    TrueSolarTimeCalculator,
    calculate_comparison,
    extract_json_object,
    validate_vision_data,
)
from csibot.prompts import VISION_PROMPT
from csibot.services.neironych import NeironychAPIError, NeironychClient
from csibot.sessions import SessionStore

logger = logging.getLogger(__name__)


class QiMenStates(StatesGroup):
    main_menu = State()
    bazi_awaiting_birthdate = State()
    bazi_awaiting_birthtime = State()
    qimen_awaiting_map = State()
    qimen_awaiting_question = State()
    qimen_awaiting_datetime = State()
    qimen_awaiting_location = State()
    qimen_vision_analysis = State()
    qimen_verify = State()
    qimen_result = State()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎋 Рассчитать Ба Цзы", callback_data="start_bazi")],
            [InlineKeyboardButton(text="🔮 Анализ Ци Мэнь", callback_data="start_qimen")],
            [InlineKeyboardButton(text="⚡ Ба Цзы + Ци Мэнь", callback_data="start_combined")],
            [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        ]
    )


def menu_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]]
    )


def vision_verification_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Оцифровка верна", callback_data="qimen_confirm_vision")],
            [
                InlineKeyboardButton(
                    text="📸 Отправить другую карту", callback_data="qimen_replace_map"
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
        ]
    )


def qimen_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Детальный разбор", callback_data="qimen_details")],
            [InlineKeyboardButton(text="🔄 Новый анализ", callback_data="start_qimen")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
        ]
    )


def _main_menu_text(settings: Settings) -> str:
    return (
        "🔮 <b>МАСТЕРСКИЙ АНАЛИЗ ЦИ МЭНЬ И БА ЦЗЫ</b>\n\n"
        "<i>Без постоянного хранения данных · Алгоритм v2.1</i>\n"
        f"<i>Vision/AI: {html.escape(settings.model)} · Нейроныч API</i>\n\n"
        "Выберите тип анализа:"
    )


async def _show_main_menu(target: Message, state: FSMContext, settings: Settings) -> None:
    await target.answer(
        _main_menu_text(settings),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(),
    )
    await state.set_state(QiMenStates.main_menu)


def _bazi_keyboard(combined: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if combined:
        rows.append(
            [InlineKeyboardButton(text="➡️ Перейти к Ци Мэнь", callback_data="bazi_to_qimen")]
        )
    else:
        rows.append([InlineKeyboardButton(text="🔄 Новый Ба Цзы", callback_data="start_bazi")])
    rows.append([InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _api_error_text(exc: NeironychAPIError) -> str:
    if exc.status_code == 402:
        return "❌ Недостаточно баланса Нейроныч API для анализа."
    if exc.status_code == 401:
        return "❌ Ключ Нейроныч API не принят. Проверьте конфигурацию сервера."
    if exc.status_code == 404:
        return "❌ Модель GLM сейчас недоступна в Нейроныч API."
    if exc.status_code == 429:
        return "⏳ Провайдер ограничил частоту запросов. Попробуйте позже."
    return (
        "❌ Не удалось получить результат от GLM. Новый платный запрос автоматически не запускался."
    )


async def _run_vision_analysis(
    message: Message,
    state: FSMContext,
    *,
    client: NeironychClient,
    sessions: SessionStore,
) -> None:
    session = sessions.get(message.from_user.id)
    if not session.map_image_data_url:
        await message.answer(
            "❌ Карта не найдена. Отправьте фото ещё раз.",
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_map)
        return

    await state.set_state(QiMenStates.qimen_vision_analysis)
    status = await message.answer(
        "🔍 <b>Оцифровываю карту через GLM…</b>\n"
        "<i>Сначала только распознавание 9 дворцов — без интерпретации.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=menu_only_keyboard(),
    )
    try:
        raw = await client.analyze_image(session.map_image_data_url, VISION_PROMPT)
        parsed = validate_vision_data(extract_json_object(raw))
    except NeironychAPIError as exc:
        session.map_image_data_url = None
        logger.warning(
            "GLM vision request failed user_id=%s status=%s request_id=%s",
            message.from_user.id,
            exc.status_code,
            exc.request_id,
        )
        await status.edit_text(
            _api_error_text(exc),
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_map)
        return
    except (ValueError, TypeError) as exc:
        session.map_image_data_url = None
        logger.warning(
            "GLM vision parse failed user_id=%s error=%s",
            message.from_user.id,
            exc,
        )
        await status.edit_text(
            "❌ GLM не смог надёжно оцифровать все 9 дворцов. "
            "Расчёт не выполнялся. Пришлите более чёткое фото.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_map)
        return

    session.vision_data = parsed
    session.map_image_data_url = None
    session.qimen_comparison = None
    await status.edit_text(
        format_vision_summary(parsed),
        parse_mode=ParseMode.HTML,
        reply_markup=vision_verification_keyboard(),
    )
    await state.set_state(QiMenStates.qimen_verify)


def create_router(
    *,
    client: NeironychClient,
    settings: Settings,
    sessions: SessionStore | None = None,
) -> Router:
    router = Router(name="csibot")
    store = sessions or SessionStore()

    @router.message(Command("start"))
    async def cmd_start(message: Message, state: FSMContext) -> None:
        store.reset(message.from_user.id)
        await state.clear()
        await _show_main_menu(message, state, settings)

    @router.message(Command("menu"))
    async def cmd_menu(message: Message, state: FSMContext) -> None:
        store.reset(message.from_user.id)
        await state.clear()
        await _show_main_menu(message, state, settings)

    @router.callback_query(F.data == "back_main")
    async def back_main(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        store.reset(callback.from_user.id)
        await state.clear()
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                _main_menu_text(settings),
                parse_mode=ParseMode.HTML,
                reply_markup=main_menu_keyboard(),
            )
        await state.set_state(QiMenStates.main_menu)

    @router.callback_query(F.data == "help")
    async def help_handler(callback: CallbackQuery) -> None:
        await callback.answer()
        if not isinstance(callback.message, Message):
            return
        await callback.message.edit_text(
            "❓ <b>ПОМОЩЬ</b>\n\n"
            "<b>Ба Цзы (八字)</b> — восстановленный расчёт четырёх столпов из версии проекта 2026 года.\n\n"
            "<b>Ци Мэнь (奇门遁甲)</b> — фото карты → GLM оцифровывает 9 дворцов → "
            "вы подтверждаете распознавание → бот считает Хозяина и Гостя.\n\n"
            "<b>Алгоритм v2.1:</b>\n"
            "• истинное солнечное время\n"
            "• S_base\n"
            "• K_empty\n"
            "• W_struct\n"
            "• C_inter\n"
            "• итог: (S_base × K_empty) + W_struct + C_inter\n\n"
            f"<b>AI:</b> <code>{html.escape(settings.model)}</code> через Нейроныч API\n"
            "<b>Команды:</b> /start, /menu",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )

    @router.callback_query(F.data.in_({"start_bazi", "start_combined"}))
    async def start_bazi(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        mode = "combined" if callback.data == "start_combined" else "bazi"
        store.reset(callback.from_user.id, mode=mode)
        if not isinstance(callback.message, Message):
            return
        heading = (
            "⚡ <b>КОМБИНИРОВАННЫЙ АНАЛИЗ</b>"
            if mode == "combined"
            else "🎋 <b>РАСЧЁТ БА ЦЗЫ (八字)</b>"
        )
        await callback.message.edit_text(
            f"{heading}\n\nВведите <b>дату рождения</b>:\n<i>Формат: ДД.ММ.ГГГГ</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.bazi_awaiting_birthdate)

    @router.message(StateFilter(QiMenStates.bazi_awaiting_birthdate))
    async def bazi_birthdate(message: Message, state: FSMContext) -> None:
        raw = (message.text or "").strip()
        try:
            day, month, year = (int(part) for part in raw.split("."))
            date(year, month, day)
        except (ValueError, TypeError):
            await message.answer(
                "❌ Неверный формат. Введите дату как <code>ДД.ММ.ГГГГ</code>.",
                parse_mode=ParseMode.HTML,
                reply_markup=menu_only_keyboard(),
            )
            return
        store.get(message.from_user.id).user_birthdate = raw
        await message.answer(
            "Введите <b>время рождения</b> в формате <code>ЧЧ:ММ</code>.\n"
            "Если неизвестно — напишите <code>неизвестно</code>.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.bazi_awaiting_birthtime)

    @router.message(StateFilter(QiMenStates.bazi_awaiting_birthtime))
    async def bazi_birthtime(message: Message, state: FSMContext) -> None:
        session = store.get(message.from_user.id)
        raw = (message.text or "").strip()
        if not session.user_birthdate:
            await state.set_state(QiMenStates.bazi_awaiting_birthdate)
            await message.answer("Сначала введите дату рождения.")
            return

        if raw.lower() == "неизвестно":
            hour = 12
        else:
            try:
                hour_value, minute_value = (int(part) for part in raw.split(":"))
                hour = time(hour_value, minute_value).hour
            except (ValueError, TypeError):
                await message.answer(
                    "❌ Неверный формат. Введите <code>ЧЧ:ММ</code> или <code>неизвестно</code>.",
                    parse_mode=ParseMode.HTML,
                    reply_markup=menu_only_keyboard(),
                )
                return

        day, month, year = (int(part) for part in session.user_birthdate.split("."))
        birthdate = date(year, month, day)
        result = BaZiCalculator.calculate(birthdate.year, birthdate.month, birthdate.day, hour)
        session.user_birthtime = raw
        session.user_bazi = result
        await message.answer(
            format_bazi(result),
            parse_mode=ParseMode.HTML,
            reply_markup=_bazi_keyboard(session.mode == "combined"),
        )
        await state.set_state(QiMenStates.main_menu)

    @router.callback_query(F.data == "start_qimen")
    async def start_qimen(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        store.reset(callback.from_user.id, mode="qimen")
        if not isinstance(callback.message, Message):
            return
        await callback.message.edit_text(
            "🔮 <b>АНАЛИЗ ЦИ МЭНЬ</b>\n\n"
            "Отправьте <b>фото карты</b>. Все 9 дворцов должны быть видны и читаться.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_map)

    @router.callback_query(F.data == "bazi_to_qimen")
    async def bazi_to_qimen(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        session = store.get(callback.from_user.id)
        session.mode = "combined"
        session.map_image_data_url = None
        session.question = None
        session.event_datetime = None
        session.true_solar_time = None
        session.vision_data = None
        session.qimen_comparison = None
        if not isinstance(callback.message, Message):
            return
        await callback.message.edit_text(
            "🔮 <b>ЭТАП 2 — ЦИ МЭНЬ</b>\n\n"
            "Ба Цзы рассчитан. Теперь отправьте <b>фото карты Ци Мэнь</b>.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_map)

    @router.message(F.photo, StateFilter(QiMenStates.qimen_awaiting_map))
    async def qimen_receive_map(message: Message, state: FSMContext) -> None:
        photo = message.photo[-1]
        telegram_file = await message.bot.get_file(photo.file_id)
        if not telegram_file.file_path:
            await message.answer("❌ Telegram не вернул путь к файлу. Пришлите фото ещё раз.")
            return
        buffer = BytesIO()
        await message.bot.download_file(telegram_file.file_path, buffer)
        session = store.get(message.from_user.id)
        session.map_image_data_url = image_bytes_to_data_url(buffer.getvalue())
        session.vision_data = None
        session.qimen_comparison = None

        if session.question and session.event_datetime and session.true_solar_time:
            await _run_vision_analysis(message, state, client=client, sessions=store)
            return

        await message.answer(
            "✅ <b>Карта получена.</b>\n\nВведите <b>один конкретный вопрос</b> для анализа.",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_question)

    @router.message(StateFilter(QiMenStates.qimen_awaiting_map))
    async def qimen_map_requires_photo(message: Message) -> None:
        await message.answer(
            "📸 На этом шаге нужно отправить именно фотографию карты.",
            reply_markup=menu_only_keyboard(),
        )

    @router.message(StateFilter(QiMenStates.qimen_awaiting_question))
    async def qimen_question(message: Message, state: FSMContext) -> None:
        question = (message.text or "").strip()
        if len(question) < 3:
            await message.answer("Введите конкретный вопрос текстом.")
            return
        store.get(message.from_user.id).question = question
        await message.answer(
            "Введите <b>дату и время события</b>:\n<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=menu_only_keyboard(),
        )
        await state.set_state(QiMenStates.qimen_awaiting_datetime)

    @router.message(StateFilter(QiMenStates.qimen_awaiting_datetime))
    async def qimen_datetime(message: Message, state: FSMContext) -> None:
        raw = (message.text or "").strip()
        try:
            raw_date, raw_time = raw.split()
            day, month, year = (int(part) for part in raw_date.split("."))
            hour, minute = (int(part) for part in raw_time.split(":"))
            event_datetime = datetime.combine(
                date(year, month, day),
                time(hour, minute),
            )
        except (ValueError, TypeError):
            await message.answer(
                "❌ Неверный формат. Используйте <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>.",
                parse_mode=ParseMode.HTML,
                reply_markup=menu_only_keyboard(),
            )
            return
        store.get(message.from_user.id).event_datetime = event_datetime
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Москва (37.6173, UTC+3)", callback_data="location_moscow"
                    )
                ],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")],
            ]
        )
        await message.answer(
            "Введите <b>долготу</b> места события.\n"
            "Можно также указать UTC-смещение через пробел.\n\n"
            "Примеры: <code>37.6173</code> или <code>11.5 1</code>.\n"
            f"Без второго числа будет использовано UTC{settings.default_utc_offset:+g}.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
        )
        await state.set_state(QiMenStates.qimen_awaiting_location)

    async def finish_location(
        message: Message,
        state: FSMContext,
        *,
        longitude: float,
        utc_offset: float,
    ) -> None:
        session = store.get(message.from_user.id)
        if session.event_datetime is None:
            await message.answer("Дата события потеряна. Запустите анализ заново.")
            return
        session.longitude = longitude
        session.utc_offset = utc_offset
        session.true_solar_time = TrueSolarTimeCalculator.calculate(
            session.event_datetime,
            longitude=longitude,
            utc_offset_hours=utc_offset,
        )
        correction = (session.true_solar_time - session.event_datetime).total_seconds() / 60
        await message.answer(
            "🌞 <b>Истинное солнечное время:</b> "
            f"<code>{session.true_solar_time.strftime('%H:%M')}</code> "
            f"(<code>{correction:+.0f} мин</code>)",
            parse_mode=ParseMode.HTML,
        )
        await _run_vision_analysis(message, state, client=client, sessions=store)

    @router.callback_query(F.data == "location_moscow")
    async def location_moscow(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        if isinstance(callback.message, Message):
            await finish_location(
                callback.message,
                state,
                longitude=37.6173,
                utc_offset=3.0,
            )

    @router.message(StateFilter(QiMenStates.qimen_awaiting_location))
    async def qimen_location(message: Message, state: FSMContext) -> None:
        try:
            longitude, utc_offset = parse_location_input(
                message.text or "",
                default_utc_offset=settings.default_utc_offset,
            )
        except ValueError:
            await message.answer(
                "❌ Введите долготу от -180 до 180. "
                "При необходимости добавьте UTC-смещение: <code>37.6 3</code>.",
                parse_mode=ParseMode.HTML,
                reply_markup=menu_only_keyboard(),
            )
            return
        await finish_location(
            message,
            state,
            longitude=longitude,
            utc_offset=utc_offset,
        )

    @router.callback_query(F.data == "qimen_replace_map")
    async def qimen_replace_map(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        session = store.get(callback.from_user.id)
        session.map_image_data_url = None
        session.vision_data = None
        session.qimen_comparison = None
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "📸 Отправьте другую фотографию карты. "
                "Вопрос, время и место уже сохранены в текущей сессии.",
                reply_markup=menu_only_keyboard(),
            )
        await state.set_state(QiMenStates.qimen_awaiting_map)

    @router.callback_query(F.data == "qimen_confirm_vision")
    async def qimen_confirm_vision(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        session = store.get(callback.from_user.id)
        if (
            session.vision_data is None
            or session.event_datetime is None
            or session.true_solar_time is None
            or not session.question
        ):
            if isinstance(callback.message, Message):
                await callback.message.answer(
                    "❌ Данные текущего анализа потеряны. Запустите анализ заново.",
                    reply_markup=menu_only_keyboard(),
                )
            return

        try:
            comparison = calculate_comparison(session.vision_data)
        except (ValueError, TypeError) as exc:
            logger.warning(
                "Confirmed vision data is not calculable user_id=%s error=%s",
                callback.from_user.id,
                exc,
            )
            if isinstance(callback.message, Message):
                await callback.message.answer(
                    "⚠️ В оцифровке остались нераспознанные или недопустимые символы. "
                    "Расчёт не выполнен. Пришлите более чёткую карту.",
                    reply_markup=menu_only_keyboard(),
                )
            await state.set_state(QiMenStates.qimen_awaiting_map)
            return

        session.qimen_comparison = comparison
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                format_comparison(
                    comparison,
                    question=session.question,
                    event_time=session.event_datetime.strftime("%d.%m.%Y %H:%M"),
                    solar_time=session.true_solar_time.strftime("%d.%m.%Y %H:%M"),
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=qimen_result_keyboard(),
            )
        await state.set_state(QiMenStates.qimen_result)

    @router.callback_query(F.data == "qimen_details")
    async def qimen_details(callback: CallbackQuery) -> None:
        await callback.answer()
        session = store.get(callback.from_user.id)
        comparison = session.qimen_comparison
        if comparison is None:
            if isinstance(callback.message, Message):
                await callback.message.answer("Нет рассчитанных данных.")
            return

        host = comparison.host
        guest = comparison.guest
        text = (
            "📊 <b>ДЕТАЛЬНЫЙ РАЗБОР v2.1</b>\n\n"
            f"<b>Хозяин — {comparison.host_palace}</b>\n"
            f"База: <code>{host['s_base']:+.1f}</code>\n"
            f"Пустота: <code>{host['k_empty']:.1f}</code>\n"
            f"После пустоты: <code>{host['s_base_corrected']:+.1f}</code>\n"
            f"Структуры: <code>{host['w_struct']:+d}</code>\n"
            f"Взаимодействие: <code>{host['c_inter']:+d}</code>\n\n"
            f"<b>Гость — {comparison.guest_palace}</b>\n"
            f"База: <code>{guest['s_base']:+.1f}</code>\n"
            f"Пустота: <code>{guest['k_empty']:.1f}</code>\n"
            f"После пустоты: <code>{guest['s_base_corrected']:+.1f}</code>\n"
            f"Структуры: <code>{guest['w_struct']:+d}</code>\n"
            f"Взаимодействие: <code>{guest['c_inter']:+d}</code>\n\n"
            "<b>Формула:</b> <code>(S_base × K_empty) + W_struct + C_inter</code>"
        )
        if isinstance(callback.message, Message):
            await callback.message.answer(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=qimen_result_keyboard(),
            )

    return router
