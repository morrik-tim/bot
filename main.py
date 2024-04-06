import asyncio
import os

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from hdrezka import Search
from telethon import TelegramClient
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
phone = os.getenv("PHONE")

telethon_client = TelegramClient('anon', api_id, api_hash)
telethon_client.start(phone=phone)
bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Введите название фильма или сериала.")


@dp.message_handler()
async def main(message: types.Message):
    # search_results = await Search(message.text).get_page(page)
    # results = len(search_results)
    # for i in range(results):
    #     player = await search_results[i].player
    #     print(f'Имя - {player.post.name}')
    #     if message.text in player.post.name:
    #         print(f'Фильм - {player.post.name}')
    #         break
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

            await asyncio.sleep(0.8)


        page += 1  # Увеличиваем page на 1 после обработки всех результатов

    # translator_id = None  # default
    # for name, id_ in player.post.translators.name_id.items():
    #     print(f'Переводчик - {name}, ID: {id_}')
    #     if 'Дубляж' in name:
    #         translator_id = id_
    #         break
    #
    # stream = await player.get_stream(translator_id)
    # video = stream.video
    #
    # # stream = await player.get_stream(1, 1, translator_id)  # raise AJAXFail if invalid episode or translator
    # # video = stream.video
    # # print(await video.last_url)  # best quality (.m3u8)
    # # print((await video[video.min].last_url).mp4, end='\n\n')  # worst quality (.mp4)
    #
    # await message.answer_photo(search_results[i].poster)
    # await message.answer(player.post.info)
    #
    # for i in range(len(video.qualities)):
    #     if video.qualities[i] == 720:
    #         video_url = (await video[i].last_url).mp4
    #         break
    #     print(video.qualities[i])
    #     print(i)
    #     print((await video[i].last_url).mp4, end='\n\n')
    #
    # from tools import send_2_chat
    # await send_2_chat(message, message.chat.id, video_url)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
