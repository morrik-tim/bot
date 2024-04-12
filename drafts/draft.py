# search_results = await Search(message.text).get_page(page)
# results = len(search_results)
# for i in range(results):
#     player = await search_results[i].player
#     print(f'Имя - {player.post.name}')
#     if message.text in player.post.name:
#         print(f'Фильм - {player.post.name}')
#         break
# stream = await player.get_stream(1, 1, translator_id)  # raise AJAXFail if invalid episode or translator
# video = stream.video
# print(await video.last_url)
# print((await video[video.min].last_url).mp4, end='\n\n')  # worst quality (.mp4)

# async with aiohttp.ClientSession() as session:
#     async with session.get(video_url) as response:
#         if response.status == 200:
#             content_length = int(response.headers.get('Content-Length', 0))
#             with tqdm(total=content_length, unit='B', unit_scale=True, desc=video_url.split('/')[-1]) as pbar:
#                 async with aiofiles.open(video_url.split('/')[-1], mode='wb') as f:
#                     asyncio.StreamWriter(response.content, f)
#                     pbar.update(content_length)
#                 await telethon_client.send_file(
#                     chat_id, video_url.split('/')[-1],
#                     supports_streaming=True,
#                     attributes=[DocumentAttributeVideo(seconds, width_clip, height_clip, supports_streaming=True)]
#                 )
#             logging.info("Видео отправлено!")
#         else:
#             logging.error(f"Failed to download video: {response.status}")
