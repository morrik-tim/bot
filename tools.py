import os

import aiohttp
from aiogram import types
from moviepy.editor import VideoFileClip
from telethon import TelegramClient
from telethon.tl.types import DocumentAttributeVideo

api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

telethon_client = TelegramClient('anon', api_id, api_hash)
telethon_client.start(phone=phone)

async def duration(video_file):
    clip = VideoFileClip(video_file)
    seconds = clip.duration
    clip.close()
    return seconds


async def width(video_file):
    clip = VideoFileClip(video_file)
    width_clip = clip.w
    clip.close()
    return width_clip


async def height(video_file):
    clip = VideoFileClip(video_file)
    height_clip = clip.h
    clip.close()
    return height_clip

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

async def send_2_chat(message: types.Message, chat_id: int, video_url: str):
    # Скачивание видео
    video_file = await download_video(video_url)
    print("Отправляю видео...")
    await message.answer("Отправляю видео...")
    await message.answer_sticker(sticker="CAACAgEAAxkBAAEL2CBmDr4j3_F20zqwx8FJiWU7Avac1wACLQIAAqcjIUQ9QDDJ7YO0tjQE")

    d = await duration(video_file)
    w = await width(video_file)
    h = await height(video_file)
    print(f'Длительность: {d} секунд')
    print(f'Ширина: {w} px')
    print(f'Высота: {h} px\n')

    # Отправка видео
    await telethon_client.send_file(
        chat_id,
        video_file,
        supports_streaming=True,
        attributes=[DocumentAttributeVideo(d, w, h, supports_streaming=True)]
    )

    print("Видео отправлено!")
    await message.answer("Видео отправлено!")
    os.remove(video_file)  # Удаление файла после отправки