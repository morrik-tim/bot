import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from dotenv import load_dotenv, find_dotenv
from hdrezka import Search
from moviepy.editor import VideoFileClip
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo

load_dotenv(find_dotenv())
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

logging.basicConfig(level=logging.INFO)
telethon_client = TelegramClient('anon', api_id, api_hash)
telethon_client.start(phone=phone)
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Введите название фильма или сериала.")


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    global video_url, film, player
    markup = await markups()

    page = 1
    while True:
        search_results = await Search(message.text).get_page(page)
        results = len(search_results)
        if results == 0:
            break  # Выход из цикла, если результатов нет

        for film in range(results):
            player = await search_results[film].player
            # if message.text in player.post.name:
            #     print(f'Фильм - {player.post.name}')
            #     break
            meta_tag = player.post._soup_inst.find('meta', property='og:type')

            content = meta_tag['content'].removeprefix('video.')
            print(f'Название - {player.post.name}')
            print(f'Тип контента - {content}')
            await message.answer_photo(search_results[film].poster, player.post.name, reply_markup=markup)

            await asyncio.sleep(2)

        if results < 36:
            break
        else:
            page += 1  # Увеличиваем page на 1 после обработки всех результатов

        translator_id = None  # default
        for name, id_ in player.post.translators.name_id.items():
            print(f'Переводчик - {name}, ID: {id_}')
            if 'Дубляж' in name:
                translator_id = id_
                break

        stream = await player.get_stream(translator_id)
        video = stream.video

        await message.answer_photo(search_results[film].poster, reply_markup=markup)
        await message.answer(player.post.info, reply_markup=markup)

        for i in range(len(video.qualities)):
            if video.qualities[i] == 720:
                video_url = (await video[i].last_url).mp4
                break
            print(video.qualities[i])
            print(i)
            print((await video[i].last_url).mp4, end='\n\n')

        # await send_2_chat(message, message.chat.id, video_url)


async def send_2_chat(message: types.Message, chat_id: int, video_url: str):
    # Скачивание видео
    video_file = await download_video(video_url)
    print("Отправляю видео...")
    await message.answer("Отправляю видео...")
    await message.answer_sticker(sticker="CAACAgEAAxkBAAEL2CBmDr4j3_F20zqwx8FJiWU7Avac1wACLQIAAqcjIUQ9QDDJ7YO0tjQE")

    seconds, width_clip, height_clip = await get_video_params(video_file)

    print(f'Длительность: {seconds} секунд')
    print(f'Ширина: {width_clip} px')
    print(f'Высота: {height_clip} px\n')

    # Отправка видео
    await telethon_client.send_file(
        chat_id,
        video_file,
        supports_streaming=True,
        attributes=[DocumentAttributeVideo(seconds, width_clip, height_clip, supports_streaming=True)]
    )

    print("Видео отправлено!")
    await message.answer("Видео отправлено!")
    os.remove(video_file)  # Удаление файла после отправки


@dp.message_handler()
async def markups():
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='back'),
        types.InlineKeyboardButton('Далее', callback_data='next'))
    markup.add(types.InlineKeyboardButton('Выбрать', callback_data='select'))
    return markup


async def get_video_params(video_file):
    clip = VideoFileClip(video_file)
    seconds = clip.duration
    width_clip = clip.w
    height_clip = clip.h
    clip.close()
    return seconds, width_clip, height_clip


async def download_video(video_url):
    local_filename = video_url.split('/')[-1]
    async with aiohttp.ClientSession() as session:
        async with session.get(video_url) as response:
            if response.status == 200:
                with open(local_filename, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                return local_filename


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
