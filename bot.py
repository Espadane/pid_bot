import hashlib
import aioschedule
import asyncio
from config import BOT_TOKEN, ADMIN_ID
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineQuery, \
    InputTextMessageContent, InlineQueryResultArticle
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from db import *


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# keyboards
add_task_kb = [
    [types.KeyboardButton(text='Добавить вопрос')],
    [types.KeyboardButton(text='Добавить действие')],
    [types.KeyboardButton(text='Играть')],
]
add_task_keyboard = types.ReplyKeyboardMarkup(keyboard=add_task_kb,
                                              resize_keyboard=True
                                              )

category_task_kb = [
    [types.KeyboardButton(text='Для всех')],
    [types.KeyboardButton(text='18+')],
]
category_task_keyboard = types.ReplyKeyboardMarkup(keyboard=category_task_kb,
                                                   resize_keyboard=True)

type_task_kb = [
    [types.KeyboardButton(text='Правда')],
    [types.KeyboardButton(text='Действие')]
]

type_task_keyboard = types.ReplyKeyboardMarkup(keyboard=type_task_kb,
                                               resize_keyboard=True)

approve_task_kb = [
    [types.KeyboardButton(text='Подтвердить')],
    [types.KeyboardButton(text='Отвергнуть')]
]
approve_task_keyboard = types.ReplyKeyboardMarkup(keyboard=approve_task_kb,
                                                  resize_keyboard=True)

# States


class AddTask(StatesGroup):
    """
    Состояния добавления задач
    """
    task_category = State()
    task_body = State()


class ApproveTaks(StatesGroup):
    """
        Состояния подтверждения задач
    """
    choose_status = State()
    write_comment = State()


class PlayGame(StatesGroup):
    """
        Состояния игры
    """
    choose_category = State()
    choose_type = State()


@dp.message_handler(commands=['start', 'help'])
async def start_command(msg: types.Message) -> None:
    """
    Обработка комманд start и help
    """

    await msg.answer('Бот создан для игры в "Правда или Действие". Правила \
просты: участники по очереди выбирают "правда" (ответить на вопрос) или \
"действие" (выполнить задание других участников). Остальные детали правил \
уточняются участниками. Бот работает в inline режиме, то есть в любом чате \
или группе надо написать"@pradelbot ...", на месте точек - правда или \
действие. Бот пришлет задание. Либо в чате с ботом можно нажать кнопку \
"Играть". Есть возможность придумывать свои вопросы и \
задания, для этого надо нажать на соответствующую кнопку и ответить на \
вопросы. После одобрения администратора, вопрос/задание добавится в бота \
, а вам придет уведомление. Для отмены добавления напишите в чат "отмена" \
или команду "\\cancel".', reply_markup=add_task_keyboard)


@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(Text(equals='отмена', ignore_case=True), state='*')
async def cancel_handler(msg: types.Message, state: FSMContext) -> None:
    """
        Сброс состояний, по команде или сообещению в чате.
    """
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await msg.answer('Процедура добавляения отменена.',
                     reply_markup=add_task_keyboard)


@dp.message_handler(commands=['new_tasks'])
async def new_tasks_command(msg: types.Message) -> None:
    """
        Обработка команды на получение всех не подтвержденных задач
    """
    new_tasks_count = await get_new_tasks_count()
    if msg.from_id != ADMIN_ID:
        await msg.answer('Ты не админ, не для тебя комманда росла')
    elif new_tasks_count <= 0:
        await msg.answer('Новых заданий для подтверждения нет.')
    else:
        new_task = get_new_task_from_db()
        await ApproveTaks.choose_status.set()
        await msg.answer(f'Пользователь: {new_task.user_name} \
        ({new_task.user_id})\n\
Группа: {new_task.task_type} - Категория: {new_task.task_category}\n\
Задача: {new_task.task_body}\n\
Подтвердить?', reply_markup=approve_task_keyboard)


@dp.message_handler(state=ApproveTaks.choose_status)
async def process_task_type(msg: types.Message, state=FSMContext) -> None:
    """
        Выбираем статус
    """
    if msg.text == 'Подтвердить':
        new_tasks_count = await get_new_tasks_count()
        new_task = get_new_task_from_db()
        user_id = new_task.user_id
        task_body = new_task.task_body
        approve_task()
        await bot.send_message(user_id, f'Спасибо, ваше задание \n\
"{task_body}"\nпринято!')
        await msg.answer(f'Принято', reply_markup=add_task_keyboard)
        await state.finish()
    elif msg.text == 'Отвергнуть':
        await ApproveTaks.next()
        await msg.answer('Напишите коментарий почему не подходит',
                         reply_markup=types.ReplyKeyboardRemove())


@dp.message_handler(state=ApproveTaks.write_comment)
async def process_write_comment(msg: types.Message, state=FSMContext) -> None:
    """
        Пишем комментарий почему нам не понравилось задание
    """
    comment = msg.text
    new_task = get_new_task_from_db()
    chat_id = new_task.user_id
    task_body = new_task.task_body
    await bot.send_message(chat_id, f'Ваше задание:\n"{task_body}" не подходит.\
    \nПричина: {comment}\nПожалуйта исправьте недочеты, спасибо.')
    delete_task()
    await state.finish()
    await msg.answer(f'Отвергнуто. Комментарий отправлен.',
                     reply_markup=add_task_keyboard)


@dp.message_handler(lambda msg: msg.text not in ['Для всех', '18+'],
                    state=AddTask.task_category)
async def process_category_invalid(msg: types.Message) -> None:
    """
        Проверка на правильность выбора категории задачи
    """
    return await msg.answer('Выберите пожалуйста категорию из списка')


@dp.message_handler(Text)
async def text_answer(msg: types.Message, state=FSMContext) -> None:
    """
    Обработка сообщений пользователя
    """
    if 'Добавить' in msg.text:
        if 'вопрос' in msg.text:
            task_type = 'правда'
        elif 'действие' in msg.text:
            task_type = 'действие'
        await AddTask.task_category.set()
        async with state.proxy() as data:
            data['task_type'] = task_type
        await msg.answer('Выберите категорию',
                         reply_markup=category_task_keyboard)
    elif 'Играть' in msg.text:
        await PlayGame.choose_category.set()
        await msg.answer('Выберите категорию',
                         reply_markup=category_task_keyboard)
    else:
        await msg.answer('Я не текст сообщения, да и не должен. \
        Воспользуйтесь пожалуйста коммандами. Для справки напишите "\\help"')


@dp.message_handler(state=AddTask.task_category)
async def process_task_category(msg: types.Message, state=FSMContext) -> None:
    """
        Получение категории задачи
    """
    async with state.proxy() as data:
        data['task_category'] = msg.text.lower()

    await AddTask.next()
    await msg.answer('Напишите задание',
                     reply_markup=types.ReplyKeyboardRemove()
                     )


@dp.message_handler(state=PlayGame.choose_category)
async def process_game_category(msg: types.Message, state=FSMContext) -> None:
    """
        Выбор категории для игры
    """
    async with state.proxy() as data:
        data['task_category'] = msg.text.lower()

    await PlayGame.next()
    await msg.answer('Правда или дело?', reply_markup=type_task_keyboard)


@dp.message_handler(state=PlayGame.choose_type)
async def process_game_type(msg: types.Message, state=FSMContext) -> None:
    """
        Выбор типа для игры
    """
    async with state.proxy() as data:
        data['task_type'] = msg.text.lower()

    random_task = get_random_task(data['task_category'], data['task_type'])

    await state.finish()
    await msg.answer(random_task, reply_markup=add_task_keyboard)


@dp.message_handler(state=AddTask.task_body)
async def process_tsk_body(msg: types.Message, state=FSMContext) -> None:
    """
        Получаем тело задачи
    """
    async with state.proxy() as data:
        data['task_body'] = msg.text
        data['user_id'] = msg.from_id
        data['user_name'] = msg.from_user.username
    task_data = await state.get_data()
    await state.finish()

    insert_request_to_db(task_data)
    await msg.answer('Запрос отправлен администратору. Как только он его\
 подтвердит вы получите сообщение, а задание будет добавленно в базу\
 данных.', reply_markup=add_task_keyboard)


@dp.inline_handler()
async def inline_answer(inline_query: InlineQuery) -> None:
    """
        Инлайн кнопки
    """
    request = inline_query.query.lower()
    result_id: str = hashlib.md5(request.encode()).hexdigest()

    if request in ['правда', 'действие']:
        title = request.capitalize()
        item_all = InlineQueryResultArticle(
            id=result_id + 'to_all',
            title=title + ' для всех',
            input_message_content=InputTextMessageContent(
                get_random_task('для всех', request))
        )

        item_18plus = InlineQueryResultArticle(
            id=result_id + '18plus',
            title=title + ' 18+',
            input_message_content=InputTextMessageContent(
                get_random_task('18+', request))
        )

        await bot.answer_inline_query(inline_query.id, results=[item_all,
                                                                item_18plus],
                                      cache_time=1)

    else:
        title = 'Введите "Правда" или "Действие"'
        item = InlineQueryResultArticle(
            id=result_id,
            title=title,
            input_message_content=InputTextMessageContent('я не умею читать')
        )

        await bot.answer_inline_query(inline_query.id, results=[item],
                                      cache_time=1)


async def check_new_tasks_count() -> None:
    """
        уведомление о неподтвержденных задачах
    """
    new_tasks_count = await get_new_tasks_count()
    if new_tasks_count > 0:
        await bot.send_message(ADMIN_ID,
                               f'У вас есть {new_tasks_count} новых задач')


async def scheduller() -> None:
    """
        каждые 30 минут уведомление о неподтвержденных задачах
    """
    aioschedule.every(30).minutes.do(check_new_tasks_count)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(_) -> None:
    asyncio.create_task(scheduller())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
