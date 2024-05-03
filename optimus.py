import asyncio
import datetime
import logging
import os

import aiofiles
import aiohttp
import cv2

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from logging.handlers import RotatingFileHandler
from aiogram.utils import executor
from dotenv import load_dotenv, find_dotenv
from hdrezka import Search
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
current_date = datetime.datetime.now().strftime("%d-%m-%Y")
log_filename = f"log_file_{current_date}.log"
log_handler = RotatingFileHandler(filename=log_filename, maxBytes=1024, backupCount=10)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(log_handler)

telethon_client = TelegramClient('anon', API_ID, API_HASH)
telethon_client.start(phone=PHONE, password=PASSWORD)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())


class Variables:
    def __init__(self):
        self.choose_markup = None
        self.choose_quality = None
        self.chose_episode = None
        self.chosen_quality = None
        self.chosen_quality_index = None
        self.const_chat_id = -1002112068525
        self.content_type = None
        self.content_type_ = None
        self.cpt = None
        self.download_markup = None
        self.emoji_f = '📺📼'
        self.emoji_s = '📺🎞'
        self.episode_number = None
        self.film = 0
        self.markup_main = None
        self.page = 1
        self.player = None
        self.query = None
        self.reply_id = None
        self.search_results = None
        self.season_number = None
        self.seasons = None
        self.seasons_episodes = None
        self.series_ = None
        self.stream = None
        self.translator_id = None
        self.translator_name = None
        self.user_query = None
        self.video = None
        self.video_url = None

        self.film_name = None
        self.film_poster = None
        self.film_info = None


var = Variables()


@dp.message_handler(content_types=['video'])
async def reply_video(message: types.Message):
    video_ = message.video.file_id

    await bot.send_video(chat_id=var.reply_id, video=video_, caption=var.cpt)


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Введите название фильма или сериала.")
    var.reply_id = message.chat.id


@dp.message_handler(content_types=['text'])
async def main(message: types.Message):
    var.page = 1
    var.film = 0

    var.reply_id = message.chat.id
    var.user_query = message.text

    try:
        var.search_results = await Search(var.user_query).get_page(var.page)
        var.player = await var.search_results[var.film].player

        meta_tag_ = var.player.post._soup_inst.find('meta', property='og:type')
        var.content_type_ = meta_tag_['content'].removeprefix('video.')

        if var.content_type_ == "movie":
            emoji = var.emoji_f
        else:
            emoji = var.emoji_s

        var.markup_main = await main_markups()
        await message.answer_photo(var.search_results[var.film].poster,
                                   caption=f'{emoji} {var.player.post.name} - {var.search_results[var.film].info}',
                                   reply_markup=var.markup_main)
    except:
        await message.answer("Ничего не найдено. Попробуйте еще раз.")


@dp.callback_query_handler(lambda query: query.data == 'select')
async def select_callback_handler(query: types.CallbackQuery):
    if var.content_type_ == "movie":
        emoji = var.emoji_f
    else:
        emoji = var.emoji_s

    txt = f'Выберите озвучку\n\n{emoji} {var.player.post.name} - {var.search_results[var.film].info}'
    photo = var.search_results[var.film].poster
    var.choose_markup = await choose_translator_markups()

    await bot_edit_msg(query.message, txt, photo, var.choose_markup)


@dp.callback_query_handler(lambda query: query.data == 'new_search')
async def new_search_callback_handler(query: types.CallbackQuery):
    await query.message.answer("Введите название фильма или сериала.")


@dp.callback_query_handler(lambda query: query.data == 'next')
async def next_callback_handler(query: types.CallbackQuery):
    await next_film(query)
    await asyncio.sleep(1)


@dp.callback_query_handler(lambda query: query.data == 'back')
async def back_callback_handler(query: types.CallbackQuery):
    await back_film(query)
    await asyncio.sleep(1)


@dp.callback_query_handler(lambda query: query.data == 'back2menu')
async def back_callback_handler(query: types.CallbackQuery):
    await back2menu(query.message.chat.id, query.message.message_id)
    await asyncio.sleep(1)


@dp.callback_query_handler(
    lambda query: query.data in var.player.post.translators.name_id.keys() or query.data == 'default')
async def translator_callback_handler(query: types.CallbackQuery):
    var.translator_name = query.data

    if query.data == 'default':
        var.translator_id = None
    else:
        var.translator_id = var.player.post.translators.name_id[var.translator_name]  # id'shnik

    if var.content_type_ == 'movie':
        await process_film(query)
    else:
        await process_serial(query)


@dp.callback_query_handler(lambda query: query.data.startswith('season_'))
async def choose_season_callback_handler(query: types.CallbackQuery):
    var.season_number = int(query.data.split('_')[1])  # Получаем номер сезона из callback_data
    var.chose_episode = await choose_episode_markups()

    if var.content_type_ == "movie":
        emoji = var.emoji_f
    else:
        emoji = var.emoji_s

    txt = f'Озвучка - {var.translator_name}\n Сезон - {var.season_number}\n\nВыберите серию\n\n{emoji} {var.player.post.name} - {var.search_results[var.film].info}'
    photo = var.search_results[var.film].poster
    await bot_edit_msg(query.message, txt, photo, var.chose_episode)


@dp.callback_query_handler(lambda query: query.data.startswith('episode_'))
async def choose_episode_callback_handler(query: types.CallbackQuery):
    var.episode_number = int(query.data.split('_')[1])

    await asyncio.sleep(1)
    try:
        stream = await var.player.get_stream(season=var.season_number, episode=var.episode_number,
                                             translator_id=var.translator_id)
        var.video = stream.video
    except:
        pass

    if var.content_type_ == "movie":
        emoji = var.emoji_f

    else:
        emoji = var.emoji_s

    txt = f'Озвучка - {var.translator_name}\n Сезон - {var.season_number}\nСерия {var.episode_number}\n\nВыбирите качество\n\n{emoji} {var.player.post.name} - {var.search_results[var.film].info}'
    photo = var.search_results[var.film].poster
    var.choose_quality = await choose_quality_markups()

    await bot_edit_msg(query.message, txt, photo, var.choose_quality)


@dp.callback_query_handler(lambda query: query.data in var.video.qualities)
async def choose_quality_callback_handler(query: types.CallbackQuery):
    var.chosen_quality = query.data
    photo = var.search_results[var.film].poster

    if var.chosen_quality != '2K' and var.chosen_quality != '4K':
        for i in range(len(var.video.qualities)):
            if var.video.qualities[i] == var.chosen_quality:
                var.chosen_quality_index = i
                break

        var.download_markup = await download_markups()

        if var.content_type_ == 'movie':
            cpt = f'Озвучка - {var.translator_name}\nКачество - {var.chosen_quality}\n📺📼 {var.player.post.name} - {var.search_results[var.film].info}'
        else:
            cpt = f'Озвучка - {var.translator_name}\nСезон - {var.season_number}\nСерия {var.episode_number}\nКачество - {var.chosen_quality}\n\n📺🎞 {var.player.post.name} - {var.search_results[var.film].info}'

        await bot_edit_msg(query.message, cpt, photo, var.download_markup)

    else:
        cpt = f'2K и 4К не поддерживается, попробуйте другое качество'

        var.choose_quality = await choose_quality_markups()
        try:
            await bot_edit_msg(query.message, cpt, photo, var.choose_quality)
        finally:
            pass


@dp.callback_query_handler(lambda query: query.data == 'download')
async def download_callback_handler(query: types.CallbackQuery):
    photo = var.search_results[var.film].poster
    if var.content_type_ == 'movie':
        cpt = f'Озвучка - {var.translator_name}, Качество - {var.chosen_quality}\n\n{var.emoji_f} {var.player.post.name} - {var.search_results[var.film].info}\n\nНачинаем скачивать!'
    else:
        cpt = f'Озвучка - {var.translator_name}\nСезон - {var.season_number}, Серия {var.episode_number}\nКачество - {var.chosen_quality}\n\n{var.emoji_s} {var.player.post.name} - {var.search_results[var.film].info}\n\nНачинаем скачивать!'

    await bot_edit_msg(query.message, cpt, photo, None)

    video_url = (await var.video[var.chosen_quality_index].last_url).mp4
    seconds, width_clip, height_clip = await get_video_params(video_url)
    await send_video(video_url, seconds, width_clip, height_clip, query.message.chat.id)


async def next_film(query):
    results = len(var.search_results)

    try:
        if var.film == results - 1 and results >= 36:
            var.page += 1
            var.film = - 1
            var.search_results = await Search(var.user_query).get_page(var.page)

    except:
        pass

    if var.film < results - 1:
        var.film += 1

    var.player = await var.search_results[var.film].player
    await scroll(query, var.film)


async def back_film(query):
    if var.film > 0:
        var.film -= 1

    await scroll(query, var.film)

    if var.page > 1 and var.film == 0:
        var.page -= 1
        var.film = 36
        var.search_results = await Search(var.user_query).get_page(var.page)
        var.player = await var.search_results[var.film].player


async def back2menu(chat_id, message_id):
    player = await var.search_results[var.film].player

    if var.content_type_ == "movie":
        emoji = var.emoji_f
    else:
        emoji = var.emoji_s
    await bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=types.InputMediaPhoto(
            media=var.search_results[var.film].poster,
            caption=f'{emoji} {var.player.post.name} - {var.search_results[var.film].info}'),
        reply_markup=var.markup_main)


async def bot_edit_msg(message, cpt, photo, markup):
    await bot.edit_message_media(
        chat_id=message.chat.id,
        message_id=message.message_id,
        media=types.InputMediaPhoto(
            media=photo,
            caption=cpt),
        reply_markup=markup)


async def scroll(query, film_):
    player = await var.search_results[film_].player
    meta_tag = var.player.post._soup_inst.find('meta', property='og:type')
    content_type_ = meta_tag['content'].removeprefix('video.')

    if content_type_ == "movie":
        emoji = var.emoji_f
    else:
        emoji = var.emoji_s
    try:
        txt = f'{emoji} {var.player.post.name} - {var.search_results[film_].info}'
        photo = var.search_results[film_].poster
        await bot_edit_msg(query.message, txt, photo, var.markup_main)
    except:
        pass


async def process_film(query):
    await asyncio.sleep(1)
    try:
        stream = await var.player.get_stream(var.translator_id)
        var.video = stream.video
    except:
        pass

    try:
        await asyncio.sleep(1)
        if var.content_type_ == "movie":
            emoji = var.emoji_f
        else:
            emoji = var.emoji_s

        txt = f'Озвучка - {var.translator_name}\nВыберете качество\n\n{emoji} {var.player.post.name} - {var.search_results[var.film].info}'
        choose_quality = await choose_quality_markups()
        photo = var.search_results[var.film].poster

        await bot_edit_msg(query.message, txt, photo, choose_quality)

    except:
        pass


async def process_serial(query):
    try:
        if var.content_type_ == "movie":
            emoji = var.emoji_f
        else:
            emoji = var.emoji_s

        txt = f'Озвучка - {var.translator_name}\nВыберете сезон\n\n{emoji} {var.player.post.name} - {var.search_results[var.film].info}'
        photo = var.search_results[var.film].poster
        choose_season = await choose_season_markups()

        await bot_edit_msg(query.message, txt, photo, choose_season)
    except Exception as e:
        print(f"An error occurred: {e}")


async def get_video_params(video_file):
    cap = cv2.VideoCapture(video_file)

    if not cap.isOpened():
        print('Ошибка открытия видеофайла')
        return None, None, None

    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    ret, frame = cap.read()

    if not ret:
        return None, None, None

    height_clip__, width_clip__ = frame.shape[:2]
    seconds__ = frames / fps
    cap.release()

    return seconds__, width_clip__, height_clip__


async def upload_progress_callback(current, total):
    current_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)

    now = datetime.datetime.now()
    formatted_time = now.strftime("%H:%M")

    print(f"Uploaded {current_mb:.2f} MB out of {total_mb:.2f} MB at {formatted_time}")


async def send_params(id, url, caption, attributes, progress, size):
    await telethon_client.send_file(
        id, url.split('/')[-1],
        caption=caption,
        supports_streaming=True,
        use_cache=True,
        part_size_kb=8192,
        attributes=attributes,
        progress_callback=progress,
        file_size=size
    )


async def send_video(video_url_, seconds_, width_clip_, height_clip_, chat_id):

    timeout = aiohttp.ClientTimeout(total=3600)  # Установите подходящее значение таймаута
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(video_url_) as response:
            if response.status == 200:
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
                    await bot.send_message(chat_id, 'Скачивание завершилось, начинаю отправку!')
                    await upload_progress_callback(pbar.n, content_length)

                    preload_prefix_size = int(0.05 * content_length)

                    video_url_params = video_url_.split('/')[-1]
                    atr = [DocumentAttributeVideo(seconds_, width_clip_, height_clip_, supports_streaming=True,
                                                  preload_prefix_size=preload_prefix_size)]

                    if var.content_type_ == 'movie':
                        var.cpt = (f'{var.emoji_f} {var.player.post.name} - {var.search_results[var.film].info}'
                                   f'({var.chosen_quality}) - {var.translator_name}')
                    else:
                        var.cpt = (
                            f'{var.emoji_s} {var.player.post.name} - {var.search_results[var.film].info}({var.chosen_quality})\n '
                            f'{var.translator_name}, {var.season_number}, {var.episode_number}')

                    await send_params(var.const_chat_id, video_url_params, var.cpt, atr, upload_progress_callback,
                                      content_length)

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

    for name, id_, in var.player.post.translators.name_id.items():
        if name is None:
            markup.add(types.InlineKeyboardButton('по умолчанию', callback_data='default'))
        else:
            markup.add(types.InlineKeyboardButton(name, callback_data=name))

    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_season_markups():
    markup = types.InlineKeyboardMarkup()

    seasons_episodes = await var.player.get_episodes(translator_id=var.translator_id)
    seasons = len(seasons_episodes)

    for i in range(1, seasons + 1):
        markup.insert(types.InlineKeyboardButton(f'Сезон {i}', callback_data=f'season_{i}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_episode_markups():
    markup = types.InlineKeyboardMarkup()  # Указываем ширину ряда

    series_ = len(var.seasons_episodes[var.season_number])

    for i in range(1, series_ + 1):
        markup.insert(types.InlineKeyboardButton(f'Серия {i}', callback_data=f'episode_{i}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def choose_quality_markups():
    markup = types.InlineKeyboardMarkup()

    for i in range(len(var.video.qualities)):
        markup.add(types.InlineKeyboardButton(var.video.qualities[i], callback_data=var.video.qualities[i]))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


@dp.message_handler()
async def download_markups():
    markup = types.InlineKeyboardMarkup()

    markup.add(types.InlineKeyboardButton('Скачать', callback_data='download'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='back2menu'))

    return markup


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)