import HdRezkaApi.HdRezkaApi
from HdRezkaApi import *

import optimus


async def get_stream_rezka(url, translator_id):
    rezka = HdRezkaApi.HdRezkaApi(url)

    stream = rezka.getStream(translation=translator_id)('360p')

    return stream
