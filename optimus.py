import asyncio
import logging
import os
import random
import datetime
import aiofiles
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from dotenv import load_dotenv, find_dotenv
from hdrezka import Search
from moviepy.editor import VideoFileClip
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo
from tqdm import tqdm

load_dotenv(find_dotenv())

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
TOKEN = os.getenv("TOKEN")
PASSWORD = os.getenv("PASSWORD")

logging.basicConfig(level=logging.INFO)
telethon_client = TelegramClient('anon', API_ID, API_HASH)
telethon_client.start(phone=PHONE, password=PASSWORD)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(content_types=['video'])
async def reply_video(message: types.Message):
    video_ = message.video.file_id
    await bot.send_video(chat_id=reply_id, video=video_,
                         caption=f'{player.post.name} - {search_results[film].info}({chosen_quality})\n'
                                 f'{translator_name}, {season_number}, {episode_number}')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    global reply_id
    await message.answer("Введите название фильма или сериала.")
    logging.info(f"Chat ID: {message.chat.id}")
    reply_id = message.chat.id


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    global player, search_results, film, markup_main, page, reply_id, del_msg_id, query

    reply_id = message.chat.id
    query = message.text
    film = 0
    page = 1

    search_results = await Search(query).get_page(page)
    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    del_msg_id = message.message_id

    markup_main = await main_markups()

    await message.answer_photo(search_results[film].poster, caption=f'{player.post.name} - {search_results[film].info}',
                               reply_markup=markup_main)


@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    choose_markup = await choose_translator_markups()

    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Выберите озвучку\n\n'
                    f'{player.post.name} - {search_results[film].info}'),
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

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    if content == 'movie':
        await process_film(query.message)
    else:
        await process_serial(query.message)


@dp.callback_query_handler(lambda query: query.data.startswith('season_'))
async def choose_season_callback_handler(query: types.CallbackQuery):
    global season_number, chose_episode

    season_number = int(query.data.split('_')[1])  # Получаем номер сезона из callback_data
    chose_episode = await choose_episode_markups()

    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Озвучка - {translator_name}, '
                    f'Сезон - {season_number}\n '
                    f'Выберите серию\n\n'
                    f'{player.post.name} - {search_results[film].info}'),
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

    await bot.edit_message_media(
        chat_id=query.message.chat.id,
        message_id=query.message.message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'Озвучка - {translator_name}, '
                    f'Сезон - {season_number}, '
                    f'Серия {episode_number}\n\n'
                    f'{player.post.name} - {search_results[film].info}'),
        reply_markup=choose_quality
    )


@dp.callback_query_handler(lambda query: query.data in video.qualities)
async def choose_quality_callback_handler(query: types.CallbackQuery):
    global chosen_quality, chosen_quality_index

    chosen_quality = query.data
    for i in range(len(video.qualities)):
        if video.qualities[i] == chosen_quality:
            chosen_quality_index = i
            break
    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    await asyncio.sleep(1)
    if content == 'movie':
        await bot.edit_message_media(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}, '
                        f'Качество - {chosen_quality}'
                        f'\n\n{player.post.name} - {search_results[film].info}'),
            reply_markup=None
        )
    else:
        await bot.edit_message_media(
            chat_id=query.message.chat.id,
            message_id=query.message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}, '
                        f'Сезон - {season_number}, '
                        f'Серия {episode_number}, '
                        f'Качество - {chosen_quality}'
                        f'\n\n{player.post.name} - {search_results[film].info}'),
            reply_markup=None
        )

    await asyncio.sleep(1)
    video_url = (await video[chosen_quality_index].last_url).mp4
    seconds, width_clip, height_clip = await get_video_params(video_url)
    await send_video(video_url, seconds, width_clip, height_clip, query.message.chat.id)


async def next_film(chat_id, message_id):
    global film, player, page, search_results
    results = len(search_results)

    try:
        if film == results - 1 and results >= 36:
            page += 1
            film = -1
            search_results = await Search(query).get_page(page)
    except:
        pass
    if film < results - 1:
        film += 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'{player.post.name} - {search_results[film].info}'),
            reply_markup=markup_main)
    except:
        pass


async def back_film(chat_id, message_id):
    global film, player, page, search_results
    if film > 0:
        film -= 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    try:
        await bot.edit_message_media(
            chat_id=chat_id,
            message_id=message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'{player.post.name} - {search_results[film].info}'),
            reply_markup=markup_main)
    except:
        pass

    if page > 1 and film == 0:
        page -= 1
        film = 36
        search_results = await Search(query).get_page(page)


async def back2menu(chat_id, message_id):
    global player
    player = await search_results[film].player

    await bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=types.InputMediaPhoto(
            media=search_results[film].poster,
            caption=f'{player.post.name} - {search_results[film].info}'),
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

        await bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}'
                        f'\nВыберете качество'
                        f'\n\n {player.post.name} - {search_results[film].info}'),
            reply_markup=choose_quality
        )
    except:
        pass


async def process_serial(message):
    global choose_season

    try:
        await asyncio.sleep(1)
        choose_season = await choose_season_markups()

        await bot.edit_message_media(
            chat_id=message.chat.id,
            message_id=message.message_id,
            media=types.InputMediaPhoto(
                media=search_results[film].poster,
                caption=f'Озвучка - {translator_name}\n'
                        f'Выберете сезон'
                        f'\n\n{player.post.name} - {search_results[film].info}'),
            reply_markup=choose_season
        )
    except:
        pass


async def get_video_params(video_file):
    clip = VideoFileClip(video_file)
    seconds__ = clip.duration
    width_clip__ = clip.w
    height_clip__ = clip.h
    clip.close()
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
    global const_chat_id

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
                    meta_tag = player.post._soup_inst.find('meta', property='og:type')
                    content = meta_tag['content'].removeprefix('video.')

                    if content == 'movie':
                        await telethon_client.send_file(
                            const_chat_id, video_url_.split('/')[-1],
                            caption=f'{player.post.name} - {search_results[film].info}({chosen_quality}) - {translator_name}',
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
                        await telethon_client.send_file(
                            const_chat_id, video_url_.split('/')[-1],
                            caption=f'{player.post.name} - {search_results[film].info}({chosen_quality})\n'
                                    f'{translator_name}, {season_number}, {episode_number}',
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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
