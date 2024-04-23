import asyncio
import datetime
import logging
import os

import aiofiles
import aiohttp
import cv2
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from dotenv import load_dotenv, find_dotenv
from hdrezka import Search
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from tqdm import tqdm

load_dotenv(find_dotenv())

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
TOKEN = os.getenv("TOKEN")
PASSWORD = os.getenv("PASSWORD")

formatter = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# logging.basicConfig(filename='log.log', level=logging.DEBUG, format=formatter)

telethon_client = TelegramClient('anon', API_ID, API_HASH)
telethon_client.start(phone=PHONE, password=PASSWORD)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


# class Variables:
#     def __init__(self):
#         self.reply_id = None
#         self.query = None
#         self.film = 0
#         self.page = 1
#         self.player = None
#         self.search_results = None
#         self.content_type = None
#
#
# var = Variables()


@dp.message_handler(content_types=['video'])
async def reply_video(message: types.Message):
    video_ = message.video.file_id

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        await bot.send_video(chat_id=reply_id, video=video_, caption=cap_tion)
    else:
        await bot.send_video(chat_id=reply_id, video=video_, caption=cap_tion)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    global reply_id
    await message.answer("Введите название фильма или сериала.")
    logging.info(f"Chat ID: {message.chat.id}")
    reply_id = message.chat.id


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    global player, search_results, film, markup_main, page, reply_id, user_query, content_type_

    reply_id = message.chat.id
    user_query = message.text
    film = 0
    page = 1

    search_results = await Search(user_query).get_page(page)
    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"
    markup_main = await main_markups()
    await message.answer_photo(search_results[film].poster,
                               caption=f'{emoji} {player.post.name}- {search_results[film].info}',
                               reply_markup=markup_main)


@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    choose_markup = await choose_translator_markups()

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"
    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Выберите озвучку\n\n'
                    f'{emoji} {player.post.name}- {search_results[film].info}'),
        reply_markup=choose_markup
    )


@dp.callback_query_handler(lambda query: query.data == 'new_search')
async def new_search_callback_handler(query: types.CallbackQuery):
    await query.message.answer("Введите название фильма или сериала.")


@dp.callback_query_handler(lambda query: query.data == 'next')
async def next_callback_handler(query: types.CallbackQuery):
    await next_film(query.message.chat.id, query.message.message_id)
    await asyncio.sleep(1)


@dp.callback_query_handler(lambda query: query.data == 'back')
async def back_callback_handler(query: types.CallbackQuery):
    await back_film(query.message.chat.id, query.message.message_id)
    await asyncio.sleep(1)


@dp.callback_query_handler(lambda query: query.data == 'back2menu')
async def back_callback_handler(query: types.CallbackQuery):
    await back2menu(query.message.chat.id, query.message.message_id)
    await asyncio.sleep(1)


@dp.callback_query_handler(
    lambda query: query.data in player.post.translators.name_id.keys() or query.data == 'default')
async def translator_callback_handler(query: types.CallbackQuery):
    global translator_id, translator_name

    if query.data == 'default':
        translator_name = query.data
        translator_id = None
    else:
        translator_name = query.data
        translator_id = player.post.translators.name_id[translator_name]  # id'shnik

    if content_type_ == 'movie':
        await process_film(query.message)
    else:
        await process_serial(query.message)


@dp.callback_query_handler(lambda query: query.data.startswith('season_'))
async def choose_season_callback_handler(query: types.CallbackQuery):
    global season_number, chose_episode

    season_number = int(query.data.split('_')[1])  # Получаем номер сезона из callback_data
    chose_episode = await choose_episode_markups()

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"

    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Озвучка - {translator_name}, '
                    f'Сезон - {season_number}\n '
                    f'Выберите серию\n\n'
                    f'{emoji} {player.post.name}- {search_results[film].info}'),
        reply_markup=chose_episode
    )


@dp.callback_query_handler(lambda query: query.data.startswith('episode_'))
async def choose_episode_callback_handler(query: types.CallbackQuery):
    global video, stream, episode_number
    episode_number = int(query.data.split('_')[1])

    await asyncio.sleep(1)
    try:
        stream = await player.get_stream(season=season_number, episode=episode_number, translator_id=translator_id)
        video = stream.video
    except:
        pass

    choose_quality = await choose_quality_markups()

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"

    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Озвучка - {translator_name}, '
                    f'Сезон - {season_number}, '
                    f'Серия {episode_number}\n\n'
                    f'{emoji} {player.post.name}- {search_results[film].info}'),
        reply_markup=choose_quality
    )


@dp.callback_query_handler(lambda query: query.data in video.qualities)
async def choose_quality_callback_handler(query: types.CallbackQuery):
    global chosen_quality, chosen_quality_index

    equal_msg = None

    chosen_quality = query.data
    for i in range(len(video.qualities)):
        if video.qualities[i] == chosen_quality:
            chosen_quality_index = i
            break

    await asyncio.sleep(1)

    if content_type_ == 'movie':
        equal_msg = f'📺📼 {player.post.name}- {search_results[film].info}'

        await bot.edit_message_media(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}, '
                        f'Качество - {chosen_quality}'
                        f'\n\n{equal_msg}'),
            reply_markup=None
        )
    else:
        equal_msg = f'📺🎞 {player.post.name}- {search_results[film].info}'

        await bot.edit_message_media(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}, '
                        f'Сезон - {season_number}, '
                        f'Серия {episode_number}, '
                        f'Качество - {chosen_quality}'
                        f'\n\n{equal_msg}'),
            reply_markup=None
        )

    await asyncio.sleep(1)
    # if await search_in_archive(player.post.name):
    #     pass
    # else:
    video_url = (await video[chosen_quality_index].first_url).mp4
    seconds, width_clip, height_clip = await get_video_params(video_url)
    await send_video(video_url, seconds, width_clip, height_clip, query.message.chat.id)


async def next_film(chat_id, message_id):
    global film, player, page, search_results, content_type_
    results = len(search_results)

    try:
        if film == results - 1 and results >= 36:
            page += 1
            film = -1
            search_results = await Search(user_query).get_page(page)
    except:
        pass
    if film < results - 1:
        film += 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'{emoji} {player.post.name}- {search_results[film].info}'),
            reply_markup=markup_main)
    except:
        pass


async def back_film(chat_id, message_id):
    global film, player, page, search_results, content_type_
    if film > 0:
        film -= 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"
    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'{emoji} {player.post.name}- {search_results[film].info}'),
            reply_markup=markup_main)
    except:
        pass

    if page > 1 and film == 0:
        page -= 1
        film = 36
        search_results = await Search(user_query).get_page(page)


async def back2menu(chat_id, message_id):
    global player
    player = await search_results[film].player

    # meta_tag = player.post._soup_inst.find('meta', property='og:type')
    # content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        emoji = "📺📼"
    else:
        emoji = "📺🎞"
    await bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'{emoji} {player.post.name}- {search_results[film].info}'),
        reply_markup=markup_main)


async def process_film(message):
    global video, stream, choose_quality

    await asyncio.sleep(1)
    try:
        stream = await player.get_stream(translator_id)
        video = stream.video
    except:
        pass

    try:
        await asyncio.sleep(1)
        choose_quality = await choose_quality_markups()

        if content_type_ == "movie":
            emoji = "📺📼"
        else:
            emoji = "📺🎞"
        await bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}'
                        f'\nВыберете качество'
                        f'\n\n {emoji} {player.post.name}- {search_results[film].info}'),
            reply_markup=choose_quality
        )
    except:
        pass


async def process_serial(message):
    global choose_season

    try:
        await asyncio.sleep(1)
        choose_season = await choose_season_markups()

        if content_type_ == "movie":
            emoji = "📺📼"
        else:
            emoji = "📺🎞"
        await bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}\n'
                        f'Выберете сезон'
                        f'\n\n{emoji} {player.post.name}- {search_results[film].info}'),
            reply_markup=choose_season
        )
    except:
        pass


async def get_video_params(video_file):
    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        # Обработка ошибки открытия видеофайла
        print('Ошибка открытия видеофайла')
        return None, None, None

    # Получение общего количества кадров и FPS
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Перематываем видео к началу, чтобы получить размеры кадра
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()

    if not ret:
        # Обработка ошибки чтения кадра
        return None, None, None

    # Получение размеров кадра
    height_clip__, width_clip__ = frame.shape[:2]

    # Расчет длительности видео в секундах
    seconds__ = frames / fps

    # Закрытие видеофайла
    cap.release()

    return seconds__, width_clip__, height_clip__


async def upload_progress_callback(current, total):
    current_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)

    # Получаем текущее время
    now = datetime.datetime.now()
    # Форматируем время в формат чч:мм
    formatted_time = now.strftime("%H:%M")

    print(f"Uploaded {current_mb:.2f} MB out of {total_mb:.2f} MB at {formatted_time}")


async def send_video(video_url_, seconds_, width_clip_, height_clip_, chat_id):
    global const_chat_id, cap_tion

    const_chat_id = -1002112068525
    timeout = aiohttp.ClientTimeout(total=3600)  # Установите подходящее значение таймаута
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(video_url_) as response:
            if response.status == 200:
                await bot.send_message(chat_id, 'Началась загрузка!')
                content_length = int(response.headers.get('Content-Length', 0))

                with tqdm(total=content_length, unit='B', unit_scale=True, desc=video_url_.split('/')[-1]) as pbar:
                    async with aiofiles.open(video_url_.split('/')[-1], mode='wb') as f:
                        while True:
                            chunk = await response.content.read(32768)
                            if not chunk:
                                break
                            await f.write(chunk)
                            pbar.update(len(chunk))

                    pbar.close()
                    await bot.send_message(chat_id, 'Загрузка завершилась, началась отправка!')
                    await upload_progress_callback(pbar.n, content_length)

                    preload_prefix_size = int(0.05 * content_length)

                    if content_type_ == 'movie':
                        cap_tion = f'📺📼 {player.post.name}- {search_results[film].info}({chosen_quality}) - {translator_name}'
                        await telethon_client.send_file(
                            const_chat_id, video_url_.split('/')[-1],
                            caption=cap_tion,
                            supports_streaming=True,
                            use_cache=True,
                            part_size_kb=8192,
                            attributes=[
                                DocumentAttributeVideo(seconds_, width_clip_, height_clip_, supports_streaming=True,
                                                       preload_prefix_size=preload_prefix_size)],
                            progress_callback=upload_progress_callback,
                            file_size=content_length
                        )
                    else:
                        cap_tion = f'📺🎞 {player.post.name}- {search_results[film].info}({chosen_quality})\n{translator_name}, {season_number}, {episode_number}'

                        await telethon_client.send_file(
                            const_chat_id, video_url_.split('/')[-1],
                            caption=cap_tion,
                            supports_streaming=True,
                            use_cache=True,
                            part_size_kb=8192,
                            attributes=[
                                DocumentAttributeVideo(seconds_, width_clip_, height_clip_, supports_streaming=True,
                                                       preload_prefix_size=preload_prefix_size)],
                            progress_callback=upload_progress_callback,
                            file_size=content_length
                        )
                    logging.info("Видео отправлено!")

                    os.remove(video_url_.split('/')[-1])
            else:
                logging.error(f"Failed to download video: {response.status}")


@dp.message_handler()
async def main_markups():
    markup = types.InlineKeyboardMarkup()

    markup.row(
        types.InlineKeyboardButton(text='Назад', callback_data='back'),
        types.InlineKeyboardButton(text='Далее', callback_data='next'))

    markup.row(types.InlineKeyboardButton(text='Выбрать', callback_data='select'))
    markup.row(types.InlineKeyboardButton(text='Новый поиск', callback_data='new_search'))

    return markup


@dp.message_handler()
async def choose_translator_markups():
    markup = types.InlineKeyboardMarkup()

    for name, id_, in player.post.translators.name_id.items():
        if name is None:
            markup.add(types.InlineKeyboardButton('по умолчанию', callback_data='default'))
        else:
            markup.add(types.InlineKeyboardButton(name, callback_data=name))

    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_season_markups():
    global seasons_episodes, seasons

    markup = types.InlineKeyboardMarkup()

    seasons_episodes = await player.get_episodes(translator_id=translator_id)
    seasons = len(seasons_episodes)

    for i in range(1, seasons + 1):
        markup.insert(types.InlineKeyboardButton(f'Сезон {i}', callback_data=f'season_{i}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_episode_markups():
    global series_
    markup = types.InlineKeyboardMarkup()  # Указываем ширину ряда

    series_ = len(seasons_episodes[season_number])

    for i in range(1, series_ + 1):
        markup.insert(types.InlineKeyboardButton(f'Серия {i}', callback_data=f'episode_{i}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_quality_markups():
    markup = types.InlineKeyboardMarkup()

    for i in range(len(video.qualities)):
        markup.add(types.InlineKeyboardButton(video.qualities[i], callback_data=video.qualities[i]))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


# async def search_in_archive(search):
#     chid = -1002112068525
#     meta_tag = player.post._soup_inst.find('meta', property='og:type')
#     content_type_ = meta_tag['content'].removeprefix('video.')
#
#     async for message in telethon_client.iter_messages(entity=chid,search=search, limit=1000):
#         if search in message.text:
#             if content_type_ == "movie":
#                 await bot.send_video(chat_id=reply_id, video=message.video.id, caption=cap_tion)
#             else:
#                 await bot.send_video(chat_id=reply_id, video=message.video.id, caption=cap_tion)
#             return True
#         else:
#             return False


if __name__ == '__main__':
    print(f'Starting bot')
    executor.start_polling(dp, skip_updates=True)
