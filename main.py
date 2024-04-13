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
from tqdm import tqdm

load_dotenv(find_dotenv())

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
TOKEN = os.getenv("TOKEN")

logging.basicConfig(level=logging.INFO)
# telethon_client = TelegramClient('anon', API_ID, API_HASH)
# telethon_client.start(phone=PHONE)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

page_queue = asyncio.Queue()
film_queue = asyncio.Queue()
search_results_queue = asyncio.Queue()
markup_queue = asyncio.Queue()


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer(f'ID чата {message.chat.id}')
    await message.answer("Введите название фильма или сериала.")
    logging.info(f"Chat ID: {message.chat.id}")


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    global player

    await markup_queue.put(await markups())
    await page_queue.put(1)
    await film_queue.put(0)

    film = await film_queue.get()
    markup = await markups()

    search_results = await Search(message.text).get_page(page_queue)
    await search_results_queue.put(search_results)

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    await message.answer_photo(search_results[film].poster, player.post.name, reply_markup=markup)

    await film_queue.put(film)
    await markup_queue.put(markup)


@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    print('Выбрано')


@dp.callback_query_handler(lambda query: query.data == 'next')
async def next_callback_handler(query: types.CallbackQuery):
    await next_film(query.message.chat.id)


@dp.callback_query_handler(lambda query: query.data == 'back')
async def back_callback_handler(query: types.CallbackQuery):
    await back_film(query.message.chat.id)


@dp.message_handler()
async def markups():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='back'),
        types.InlineKeyboardButton('Далее', callback_data='next'))
    markup.add(types.InlineKeyboardButton('Выбрать', callback_data='select'))
    return markup


async def next_film(chat_id):
    page = 1
    await bot.send_message(chat_id, 'Следующий фильм')
    search_results = await search_results_queue.get()
    film = await film_queue.get()
    markup = await markup_queue.get()
    results = len(search_results)

    if film < results - 1:
        film += 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    await bot.send_photo(chat_id, search_results[film].poster, player.post.name,
                         reply_markup=markup)

    await film_queue.put(film)
    await markup_queue.put(markup)
    await search_results_queue.put(search_results)

    await asyncio.sleep(2)

async def back_film(chat_id):
    page = 1
    await bot.send_message(chat_id, 'Следующий фильм')
    search_results = await search_results_queue.get()
    film = await film_queue.get()
    markup = await markup_queue.get()

    if film > 0:
        film -= 1

    player = await search_results[film].player

    meta_tag = player.post._soup_inst.find('meta', property='og:type')
    content = meta_tag['content'].removeprefix('video.')

    print(f'Название - {player.post.name}')
    print(f'Тип контента - {content}')

    await bot.send_photo(chat_id, search_results[film].poster, player.post.name,
                         reply_markup=markup)

    await film_queue.put(film)
    await markup_queue.put(markup)
    await search_results_queue.put(search_results)

    await asyncio.sleep(2)


async def get_video_params(video_file):
    clip = VideoFileClip(video_file)
    seconds = clip.duration
    width_clip = clip.w
    height_clip = clip.h
    clip.close()
    return seconds, width_clip, height_clip


async def send_video(video_url, seconds, width_clip, height_clip, chat_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                content_length = int(response.headers.get('Content-Length', 0))
                with tqdm(total=content_length, unit='B', unit_scale=True, desc=video_url.split('/')[-1]) as pbar:
                    async with aiofiles.open(video_url.split('/')[-1], mode='wb') as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            await f.write(chunk)
                            pbar.update(len(chunk))
                    pbar.close()
                    # await telethon_client.send_file(
                    #     chat_id, video_url.split('/')[-1],
                    #     supports_streaming=True,
                    #     attributes=[DocumentAttributeVideo(seconds, width_clip, height_clip, supports_streaming=True)]
                    # )
                    logging.info("Видео отправлено!")

                    os.remove(video_url.split('/')[-1])
            else:
                logging.error(f"Failed to download video: {response.status}")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
