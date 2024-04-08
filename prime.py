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
from asyncio import Queue

load_dotenv(find_dotenv())

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)
telethon_client = TelegramClient('anon', API_ID, API_HASH)
telethon_client.start(phone=PHONE)
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

video_g = None
video_queue = asyncio.Queue()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    print('начало работ')
    await message.answer(f'ID чата {message.chat.id}')
    await message.answer("Введите название фильма или сериала.")
    logging.info(f"Chat ID: {message.chat.id}")


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    async with aiohttp.ClientSession():
        try:
            markup = await get_markup()
            await process_search_results(message.text, message.chat.id, markup)
        except Exception as e:
            logging.error(f"An error occurred: {e}")


@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    await bot.send_message(query.message.chat.id, "принято в работу")
    await process_video(query.message.chat.id)


async def process_search_results(query, chat_id, markup):
    print('работаем')
    page = 1
    async for film in search_films(query, page):
        await process_film(film, markup, chat_id)


async def search_films(query, start_page):
    while True:
        search_results = await Search(query).get_page(start_page)
        results = len(search_results)
        if results == 0:
            logging.info("No more search results found.")
            break
        for film in range(results):
            yield search_results[film]
        if results < 36:
            logging.info("Reached end of search results.")
            break
        start_page += 1


async def process_film(film, markup, chat_id):
    global video_g
    player = await film.player
    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')
    logging.info(f'Название - {player.post.name}')
    logging.info(f'Тип контента - {content}')
    try:
        await bot.send_photo(chat_id, film.poster, film.name, reply_markup=markup)
    except Exception as e:
        logging.error(f"An error occurred while sending photo: {e}")

    await asyncio.sleep(2)

    translator_id = next((id_ for name, id_ in player.post.translators.name_id.items() if 'Дубляж' in name), None)
    if translator_id:
        stream = await player.get_stream(translator_id)
        video_g = stream.video
        await video_queue.put(video_g)


async def process_video(chat_id):
    print('процесс')
    video = await video_queue.get()
    for i in range(len(video.qualities)):
        if video.qualities[i] == 360:
            video_url = (await video[i].last_url).mp4
            seconds, width_clip, height_clip = await get_video_params(video_url)
            await send_video(video_url, seconds, width_clip, height_clip, chat_id)


async def get_markup():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='back'),
        types.InlineKeyboardButton('Далее', callback_data='next'))
    markup.row(types.InlineKeyboardButton('Выбрать', callback_data='select'))
    return markup


async def get_video_params(video_url):
    async with aiofiles.open(video_url, mode='rb') as f:
        clip = VideoFileClip(f)
        seconds = clip.duration
        width_clip = clip.w
        height_clip = clip.h
        return seconds, width_clip, height_clip


async def send_video(video_url, seconds, width_clip, height_clip, chat_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                content_length = int(response.headers.get('Content-Length', 0))
                with tqdm(total=content_length, unit='B', unit_scale=True, desc=video_url.split('/')[-1]) as pbar:
                    async with aiofiles.open(video_url.split('/')[-1], mode='wb') as f:
                        while True:
                            chunk = await response.content.read(1048576)
                            if not chunk:
                                break
                            await f.write(chunk)
                            pbar.update(len(chunk))
                            print(f'прогресс - {pbar.update(len(chunk))}')
                            print(f'прогресс - {pbar}')
                    await telethon_client.send_file(
                        chat_id, video_url.split('/')[-1],
                        supports_streaming=True,
                        attributes=[DocumentAttributeVideo(seconds, width_clip, height_clip, supports_streaming=True)]
                    )
                    logging.info("Видео отправлено!")
            else:
                logging.error(f"Failed to download video: {response.status}")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
