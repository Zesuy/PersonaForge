import re

def parse_emoji_table(table_string):
    """
    解析表情ID和含义的对应表。
    输入: table_string (str): 包含表情对应关系的字符串，每行格式如 "类型 ID 含义"。
    输出: dict: 表情ID到表情含义的映射字典。
    """
    emoji_map = {}
    lines = table_string.strip().split('\n')
    for line in lines:
        parts = line.split()
        # 跳过表头或格式不正确的行
        # 表情类型(parts[0])在此处未使用，按需取用parts[1]为ID, parts[2:]为含义
        if len(parts) >= 3 and parts[1].isdigit():
            emoji_id = parts[1]
            emoji_meaning = " ".join(parts[2:]) # 含义可能包含空格
            emoji_map[emoji_id] = emoji_meaning
    return emoji_map

def process_chat_log(chat_log_string, emoji_map):
    """
    处理聊天记录，替换表情为统一格式 [描述-ID]。
    """
    lines = chat_log_string.splitlines()
    processed_lines = []
    i = 0
    while i < len(lines):
        current_line_original = lines[i]
        current_line_stripped = current_line_original.strip()

        if current_line_stripped == "[表情]" and i + 1 < len(lines):
            next_line_original = lines[i+1]
            next_line_stripped = next_line_original.strip()

            # 检查是否为未解析的表情，格式如: -ID
            if next_line_stripped.startswith("-") and next_line_stripped[1:].isdigit():
                emoji_id = next_line_stripped[1:]
                if emoji_id in emoji_map:
                    processed_lines.append(f"[{emoji_map[emoji_id]}-{emoji_id}]")
                else:
                    processed_lines.append(f"[未知表情-{emoji_id}]")
                i += 2  # 处理了两行
            
            # 检查是否为已解析的表情，格式如: /含义-ID
            elif next_line_stripped.startswith("/"):
                match = re.match(r"/(.+)-(\d+)", next_line_stripped)
                if match:
                    meaning, emoji_id = match.groups()
                    processed_lines.append(f"[{meaning}-{emoji_id}]")
                else:
                    processed_lines.append(current_line_original)
                    processed_lines.append(next_line_original)
                i += 2  # 处理了两行
            
            # 新增：检查是否为直接显示的表情格式，如: 笑哭-182
            elif re.match(r"(.+)-(\d+)", next_line_stripped):
                match = re.match(r"(.+)-(\d+)", next_line_stripped)
                if match:
                    meaning, emoji_id = match.groups()
                    processed_lines.append(f"[{meaning}-{emoji_id}]")
                else:
                    processed_lines.append(next_line_original)
                i += 2  # 处理了两行
            else:
                processed_lines.append(current_line_original)
                i += 1
        else:
            processed_lines.append(current_line_original)
            i += 1
            
    return "\n".join(processed_lines)
# --- 表情对应表 ---
# 表情类型 表情ID 表情含义 (表头会被忽略)
emoji_table_data = """
表情类型 表情ID 表情含义
1 4 得意
1 5 流泪
1 8 睡
1 9 大哭
1 10 尴尬
1 12 调皮
1 14 微笑
1 16 酷
1 21 可爱
1 23 傲慢
1 24 饥饿
1 25 困
1 26 惊恐
1 27 流汗
1 28 憨笑
1 29 悠闲
1 30 奋斗
1 32 疑问
1 33 嘘
1 34 晕
1 38 敲打
1 39 再见
1 41 发抖
1 42 爱情
1 43 跳跳
1 49 拥抱
1 53 蛋糕
1 60 咖啡
1 63 玫瑰
1 66 爱心
1 74 太阳
1 75 月亮
1 76 赞
1 78 握手
1 79 胜利
1 85 飞吻
1 89 西瓜
1 96 冷汗
1 97 擦汗
1 98 抠鼻
1 99 鼓掌
1 100 糗大了
1 101 坏笑
1 102 左哼哼
1 103 右哼哼
1 104 哈欠
1 106 委屈
1 109 左亲亲
1 111 可怜
1 116 示爱
1 118 抱拳
1 120 拳头
1 122 爱你
1 123 NO
1 124 OK
1 125 转圈
1 129 挥手
1 144 喝彩
1 147 棒棒糖
1 171 茶
1 173 泪奔
1 174 无奈
1 175 卖萌
1 176 小纠结
1 179 doge
1 180 惊喜
1 181 骚扰
1 182 笑哭
1 183 我最美
1 201 点赞
1 203 托脸
1 212 托腮
1 214 啵啵
1 219 蹭一蹭
1 222 抱抱
1 227 拍手
1 232 佛系
1 240 喷脸
1 243 甩头
1 246 加油抱抱
1 262 脑阔疼
1 264 捂脸
1 265 辣眼睛
1 266 哦哟
1 267 头秃
1 268 问号脸
1 269 暗中观察
1 270 emm
1 271 吃瓜
1 272 呵呵哒
1 273 我酸了
1 277 汪汪
1 278 汗
1 281 无眼笑
1 282 敬礼
1 284 面无表情
1 285 摸鱼
1 287 哦
1 289 睁眼
1 290 敲开心
1 293 摸锦鲤
1 294 期待
1 297 拜谢
1 298 元宝
1 299 牛啊
1 305 右亲亲
1 306 牛气冲天
1 307 喵喵
1 314 仔细分析
1 315 加油
1 318 崇拜
1 319 比心
1 320 庆祝
1 322 拒绝
1 324 吃糖
1 326 生气
"""

# --- 你的聊天记录示例 ---
# 你可以将你的聊天记录内容赋值给这个变量，或者从文件中读取
# 例如: with open('chat.txt', 'r', encoding='utf-8') as f: chat_log_input = f.read()
with open('527178076.txt', 'r', encoding='utf-8') as f: chat_log_input = f.read()

# 1. 解析表情对应表
emoji_mapping = parse_emoji_table(emoji_table_data)
# print("表情对应表:", emoji_mapping) # 可以取消注释这行来查看解析的表情表

# 2. 处理聊天记录
processed_chat_log = process_chat_log(chat_log_input, emoji_mapping)

# 3. 打印处理后的聊天记录
print("\n--- 处理后的聊天记录 ---")

# 4. 保存处理后的聊天记录
with open('process_emoji.txt', 'w', encoding='utf-8') as f:
    f.write(processed_chat_log)
print("\n处理后的记录已保存到 process_emoji.txt")