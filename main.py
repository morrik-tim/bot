import os
import aiohttp
import datetime
import cv2

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from hdrezka import Search
from telethon import TelegramClient
from dotenv import load_dotenv, find_dotenv
from telethon.tl.types import DocumentAttributeVideo

load_dotenv(find_dotenv())
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

telethon_client = TelegramClient('anon', api_id, api_hash)
telethon_client.start(phone=phone)

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)


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

async def duration(video_url):
    cap = cv2.VideoCapture(video_url)

    # Получите общее количество кадров и кадров в секунду для данного видео
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    # Вычислите продолжительность видео в секундах
    seconds = frames / fps
    video_time = str(datetime.timedelta(seconds=seconds))

    print(f"Продолжительность в секундах: {seconds:.2f}")
    print(f"Время видео: {video_time}")
    return video_time

async def send_2_chat(message: types.Message, chat_id: int, video_url: str):
    # Скачивание видео
    video_file = await download_video(video_url)
    dur = duration(video_url)
    print("Отправляю видео...")
    await message.answer("Отправляю видео...")
    await message.answer_sticker(sticker="CAACAgEAAxkBAAEL2CBmDr4j3_F20zqwx8FJiWU7Avac1wACLQIAAqcjIUQ9QDDJ7YO0tjQE")

    # Отправка видео
    await telethon_client.send_file(
        chat_id,
        video_file,
        supports_streaming=True,
        attributes=[DocumentAttributeVideo(dur, 320, 320, supports_streaming=True)]
    )

    # await bot.send_video(chat_id=chat_id, video=open(video_file, 'rb'))
    print("Видео отправлено!")
    await message.answer("Видео отправлено!")
    os.remove(video_file)  # Удаление файла после отправки


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Введите название фильма или сериала.")


@dp.message_handler()
async def main(message: types.Message):
    try:
        search_results = await Search(message.text).get_page(1)
        # results = len(search_results)
        player = await search_results[1].player

        translator_id = None  # default
        for name, id_ in player.post.translators.name_id.items():
            print(f'Переводчик - {name}, ID: {id_}')
            if 'субтитры' in name.casefold():
                translator_id = id_
            break

        stream = await player.get_stream(translator_id)
        video = stream.video

        await message.answer_photo(search_results[1].poster)
        await message.answer(player.post.info)

        print((await video.last_url).mp4)

        video_url = (await video[video.min].last_url).mp4
        chat_id = message.chat.id

        await send_2_chat(message, video_url, chat_id)

    except Exception as e:
        await message.answer(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
