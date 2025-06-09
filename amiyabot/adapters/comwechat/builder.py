import os
import base64
from amiyabot.adapters import MessageCallback
from amiyabot.adapters.apiProtocol import BotInstanceAPIProtocol
from amiyabot.adapters.onebot.v12 import build_message_send as build_ob12
from amiyabot.builtin.message import Message
from amiyabot.builtin.messageChain import Chain
from amiyabot.builtin.messageChain.element import *


def random_code(length: int) -> str:
    """生成随机字符串"""
    import random
    import string
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


async def upload_gif_file(api: BotInstanceAPIProtocol, file_path: str):
    """上传GIF文件并获取file_id"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # 检测文件类型
        if file_data.startswith(b'GIF87a') or file_data.startswith(b'GIF89a'):
            extension = 'gif'
        else:
            extension = 'gif'  # 默认为GIF
        
        data = {'type': 'data', 'data': base64.b64encode(file_data).decode()}
        
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
        if res and res.json and 'data' in res.json:
            return res.json['data']['file_id']
        return None
    except Exception as e:
        print(f"上传GIF文件失败: {e}")
        return None


class ComWeChatMessageCallback(MessageCallback):
    async def recall(self):
        return False

    async def get_message(self) -> Optional[Message]:
        return None


async def build_message_send(api: BotInstanceAPIProtocol, chain: Chain):
    async def handle_item(item: CHAIN_ITEM):
        # Face - 处理GIF文件上传
        if isinstance(item, Face):
            face_id = item.face_id
            
            # 如果face_id是文件路径，先上传获取file_id
            if isinstance(face_id, str) and os.path.exists(face_id):
                uploaded_file_id = await upload_gif_file(api, face_id)
                if uploaded_file_id:
                    return {'type': 'wx.emoji', 'data': {'file_id': uploaded_file_id}}
                else:
                    # 上传失败，返回None跳过该元素
                    return None
            else:
                # 如果已经是file_id，直接使用
                return {'type': 'wx.emoji', 'data': {'file_id': face_id}}

    return await build_ob12(api, chain, handle_item)
