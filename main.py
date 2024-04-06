import os

from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from dotenv import load_dotenv, find_dotenv
from hdrezka import Search

from tools import send_2_chat

load_dotenv(find_dotenv())

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(bot)

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

        await send_2_chat(message, message.chat.id, video_url)

    except Exception as e:
        await message.answer(f'Произошла ошибка: {e}')


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
