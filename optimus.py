import asyncio
import logging
import os

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


# Текстовые хэндлеры
@dp.message_handler(commands=['info'])
async def start(message: types.Message):
    await message.answer(f'ID чата {message.chat.id}')


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    global reply_id
    await message.answer(f'ID чата {message.chat.id}')
    await message.answer("Введите название фильма или сериала.")
    logging.info(f"Chat ID: {message.chat.id}")
    reply_id = message.chat.id


@dp.message_handler(commands=['clear'])
async def clear(message: types.Message):
    await message.delete()


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    global player, search_results, film, markup_main, choose_markup, page

    film = 0
    page = 1
    markup_main = await main_markups()

    search_results = await Search(message.text).get_page(page)

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    film = 0

    await message.answer_photo(search_results[film].poster, player.post.name, reply_markup=markup_main)
    choose_markup = await choose_translator_markups()


@dp.message_handler(content_types=['video'])
async def reply_video(message: types.Message):
    video_ = message.video
    await bot.send_video(chat_id=reply_id, video=video_)


# Хэндлеры кнопок
@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    await bot.send_message(query.message.chat.id, 'Выберите озвучку', reply_markup=choose_markup)


@dp.callback_query_handler(lambda query: query.data == 'next')
async def next_callback_handler(query: types.CallbackQuery):
    await next_film(query.message.chat.id)


@dp.callback_query_handler(lambda query: query.data == 'back')
async def back_callback_handler(query: types.CallbackQuery):
    await back_film(query.message.chat.id)


@dp.callback_query_handler(lambda query: query.data in player.post.translators.name_id.keys())
async def translator_callback_handler(query: types.CallbackQuery):
    global translator_id, choose_quality, video, player, translator_name

    translator_name = query.data
    translator_id = player.post.translators.name_id[translator_name]  # id'shnik

    # Далее вы можете выполнить какие-то действия в зависимости от выбранного переводчика
    await asyncio.sleep(5)
    await process_film()
    await asyncio.sleep(5)

    if video is not None:
        choose_quality = await choose_quality_markups()
        await bot.send_message(query.message.chat.id, f'Выберете качество', reply_markup=choose_quality)
    else:
        print("ОШИБКА!!!")


@dp.callback_query_handler(lambda query: query.data.isdigit() and int(query.data) < len(video.qualities))
async def choose_quality_callback_handler(query: types.CallbackQuery):
    global video_url, seconds, width_clip, height_clip, video

    chosen_quality_index = int(query.data)
    chosen_quality = video.qualities[chosen_quality_index]

    await query.message.answer(f"Вы выбрали качество: {chosen_quality}")
    video_url = (await video[chosen_quality_index].last_url).mp4

    seconds, width_clip, height_clip = await get_video_params(video_url)
    print('successfully get video params')
    await send_video(video_url, seconds, width_clip, height_clip, query.message.chat.id)


# Генерация маркапов
@dp.message_handler()
async def main_markups():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='back'),
        types.InlineKeyboardButton('Далее', callback_data='next'))
    markup.add(types.InlineKeyboardButton('Выбрать', callback_data='select'))
    return markup


@dp.message_handler()
async def choose_translator_markups():
    markup = types.InlineKeyboardMarkup()

    for name, id_, in player.post.translators.name_id.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=name))
    return markup


@dp.message_handler()
async def choose_quality_markups():
    global video
    markup = types.InlineKeyboardMarkup()
    for i in range(len(video.qualities)):
        markup.add(types.InlineKeyboardButton(video.qualities[i], callback_data=i))
        print(video.qualities[i])

    return markup


# Методы
async def next_film(chat_id):
    global film, player
    results = len(search_results)

    if film < results - 1:
        film += 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    await bot.send_photo(chat_id, search_results[film].poster, player.post.name,
                         reply_markup=markup_main)


async def back_film(chat_id):
    global film, player

    if film > 0:
        film -= 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    await bot.send_photo(chat_id, search_results[film].poster, player.post.name,
                         reply_markup=markup_main)


async def process_film():
    global video, player, translator_id

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    logging.info(f'Название - {player.post.name}')
    logging.info(f'Переводчик - {player.post.translators.names}')
    logging.info(f'Тип контента - {content}')
    logging.info(f'URL фильма - {player.post.url}')

    for name, id_ in player.post.translators.name_id.items():
        logging.info(f'Переводчик - {name}, ID: {id_}')

    if content == 'movie':
        stream = await player.get_stream(translator_id)
        video = stream.video
    else:
        print('Это сериал, пока не работаем с сериалами')


async def get_video_params(video_file):
    clip = VideoFileClip(video_file)
    seconds__ = clip.duration
    width_clip__ = clip.w
    height_clip__ = clip.h
    clip.close()
    return seconds__, width_clip__, height_clip__


async def upload_progress_callback(current, total):
    current_mb = current / (1024 * 1024)  # Конвертировать текущий размер из байтов в мегабайты
    total_mb = total / (1024 * 1024)  # Конвертировать общий размер из байтов в мегабайты
    print(f"Uploaded {current_mb:.2f} MB out of {total_mb:.2f} MB")


async def send_video(video_url_, seconds_, width_clip_, height_clip_):
    chat_id_ = -1002112068525
    timeout = aiohttp.ClientTimeout(total=3600)  # Установите подходящее значение таймаута
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(video_url_) as response:
            if response.status == 200:
                await bot.send_message(chat_id_, 'Началась загрузка!')
                content_length = int(response.headers.get('Content-Length', 0))
                with tqdm(total=content_length, unit='B', unit_scale=True, desc=video_url_.split('/')[-1]) as pbar:
                    async with aiofiles.open(video_url_.split('/')[-1], mode='wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            await f.write(chunk)
                            pbar.update(len(chunk))
                    pbar.close()
                    await bot.send_message(chat_id_, 'Загрузка завершилась, началась отправка!')
                    await upload_progress_callback(pbar.n, content_length)
                    await telethon_client.send_file(
                        chat_id_, video_url_.split('/')[-1],
                        caption=player.post.name,
                        supports_streaming=True,
                        use_cache=True,
                        part_size_kb=10240,
                        attributes=[DocumentAttributeVideo(seconds_, width_clip_, height_clip_)],
                        progress_callback=upload_progress_callback
                    )
                    logging.info("Видео отправлено!")

                    os.remove(video_url_.split('/')[-1])
            else:
                logging.error(f"Failed to download video: {response.status}")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
