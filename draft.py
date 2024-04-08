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