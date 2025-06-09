import base64

from typing import Callable, Awaitable
from amiyabot.adapters import MessageCallback
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *
from amiyautils import is_valid_url, random_code
from amiyalog import logger as log

CUSTOM_CHAIN_ITEM = Callable[[CHAIN_ITEM], Awaitable[dict]]


class OneBot12MessageCallback(MessageCallback):
    async def recall(self):
        if not self.response:
            log.warning('can not recall message because the response is None.')
            return False

        response = self.response.json

        if isinstance(response['data'], dict):
            await self.instance.recall_message(response['data']['message_id'])

    async def get_message(self):
        return None


async def build_message_send(api: BotInstanceAPIProtocol, chain: Chain, custom: Optional[CUSTOM_CHAIN_ITEM] = None):
    chain_list = chain.chain
    chain_data = []

    if chain_list:
        for item in chain_list:
            if custom:
                res = await custom(item)
                if res:
                    chain_data.append(res)
                    continue

            # At
            if isinstance(item, At):
                chain_data.append({'type': 'mention', 'data': {'user_id': item.target or chain.data.user_id}})

            # AtAll
            if isinstance(item, AtAll):
                chain_data.append({'type': 'mention_all', 'data': {}})

            # Face
            if isinstance(item, Face):
                ...

            # Text
            if isinstance(item, Text):
                chain_data.append({'type': 'text', 'data': {'text': item.content}})

            # Image
            if isinstance(item, Image):
                img = await item.get()
                res = await append_image(api, img)
                if res:
                    chain_data.append(res)

            # Voice
            if isinstance(item, Voice):
                ...

            # Html
            if isinstance(item, Html):
                result = await item.create_html_image()
                if result:
                    res = await append_image(api, result)
                    if res:
                        chain_data.append(res)

            # Extend
            if isinstance(item, Extend):
                chain_data.append(item.get())

    return {
        'detail_type': chain.data.message_type,
        'user_id': chain.data.user_id,
        'group_id': chain.data.channel_id,
        'message': chain_data,
    }


async def append_image(api: BotInstanceAPIProtocol, img_data: Union[bytes, str]):
    if isinstance(img_data, bytes):
        data = {'type': 'data', 'data': base64.b64encode(img_data).decode()}
        # 检测文件类型
        if img_data.startswith(b'GIF87a') or img_data.startswith(b'GIF89a'):
            extension = 'gif'
        elif img_data.startswith(b'\x89PNG'):
            extension = 'png'
        elif img_data.startswith(b'\xff\xd8\xff'):
            extension = 'jpg'
        else:
            extension = 'png'  # 默认为PNG
    elif is_valid_url(img_data):
        data = {'type': 'url', 'url': img_data}
        # 改进URL文件类型检测
        url_lower = img_data.lower()
        if url_lower.endswith('.gif') or '.gif?' in url_lower or '/gif/' in url_lower:
            extension = 'gif'
        elif url_lower.endswith(('.jpg', '.jpeg')) or '.jpg?' in url_lower or '.jpeg?' in url_lower:
            extension = 'jpg'
        elif url_lower.endswith('.webp') or '.webp?' in url_lower:
            extension = 'webp'
        elif url_lower.endswith('.png') or '.png?' in url_lower:
            extension = 'png'
        else:
            # 如果无法从URL判断，尝试发送HTTP请求获取Content-Type
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.head(img_data) as response:
                        content_type = response.headers.get('content-type', '').lower()
                        if 'gif' in content_type:
                            extension = 'gif'
                        elif 'jpeg' in content_type:
                            extension = 'jpg'
                        elif 'png' in content_type:
                            extension = 'png'
                        elif 'webp' in content_type:
                            extension = 'webp'
                        else:
                            extension = 'png'
            except:
                extension = 'png'  # 默认为PNG
    else:
        return None

    res = await api.post(
        '/',
        {
            'action': 'upload_file',
            'params': {
                'name': f'{random_code(20)}.{extension}',
                **data,
            },
        },
    )
    if res:
        return {'type': 'image', 'data': {'file_id': res.json['data']['file_id']}}
