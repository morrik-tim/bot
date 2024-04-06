import os
import aiohttp

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from hdrezka import Search
from telethon import TelegramClient
from dotenv import load_dotenv, find_dotenv
from telethon.tl.types import DocumentAttributeVideo
from moviepy.editor import VideoFileClip

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
    try:
        await message.answer_video(video=open(video_url, 'rb'))
    except Exception as e:
        await message.answer(f'Произошла ошибка: {e}')

    print("Видео отправлено!")
    await message.answer("Видео отправлено!")
    os.remove(video_file)  # Удаление файла после отправки


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Введите название фильма или сериала.")


@dp.message_handler()
async def main(message: types.Message):
    try:
        search_results = await Search(message.text).get_page(0)
        results = len(search_results)
        for i in range(results):
            player = await search_results[i].player
            print(f'Имя - {player.post.name}')
            if message.text in player.post.name:
                print(f'Фильм - {player.post.name}')
                break


        translator_id = None  # default
        for name, id_ in player.post.translators.name_id.items():
            print(f'Переводчик - {name}, ID: {id_}')
            if 'Дубляж' in name:
                translator_id = id_
                break

        stream = await player.get_stream(translator_id)
        video = stream.video

        # stream = await player.get_stream(1, 1, translator_id)  # raise AJAXFail if invalid episode or translator
        # video = stream.video
        # print(await video.last_url)  # best quality (.m3u8)
        # print((await video[video.min].last_url).mp4, end='\n\n')  # worst quality (.mp4)

        await message.answer_photo(search_results[i].poster)
        await message.answer(player.post.info)


        for i in range(len(video.qualities)):
            if video.qualities[i] == 720:
                video_url = (await video[i].last_url).mp4
                break
            print(video.qualities[i])
            print(i)
            print((await video[i].last_url).mp4, end='\n\n')

        chat_id = message.chat.id

        # await send_2_chat(message, chat_id, video_url)

    except Exception as e:
        await message.answer(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
