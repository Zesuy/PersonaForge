import re
import json
from datetime import datetime 

# 加载 UID->标准用户名 映射
with open("name.json", "r", encoding="utf-8") as f:
    uid2name = json.load(f)

def process_chat(lines):
    result = []
    i = 0
    msg_idx = 1  # 消息行号
    last_time = None  # 上一条消息的时间
    nickname_to_uid = {}  # 创建昵称到UID的映射表
    
    while i < len(lines):
        line = lines[i].strip()
        # 匹配消息头
        m = re.match(
            r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (.+?)(?: / (.+?))? / (\d+)$', line)
        if m:
            time = m.group(1)
            user = m.group(2)
            group_nick = m.group(3)
            uid = m.group(4)
            
            # 更新昵称到UID的映射 - 使用最新的对应关系
            nickname_to_uid[user] = uid
            if group_nick:
                nickname_to_uid[group_nick] = uid
            
            # 检查时间间隔
            current_time = datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
            if last_time is not None:
                time_diff = (current_time - last_time).total_seconds() / 60  # 时间差(分钟)
                if time_diff >= 10:
                    # 添加时间间隔提示（带行号）
                    result.append(f"{msg_idx}. [间隔{int(time_diff)}分钟]")
                    msg_idx += 1
            
            # 用UID查标准用户名
            user = uid2name.get(uid, user)
            if group_nick:
                user = f"{user} / {group_nick}"
            content_lines = []
            i += 1
            # 收集消息内容
            while i < len(lines) and not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', lines[i]):
                content_lines.append(lines[i].strip())
                i += 1
            # 处理内容
            if not content_lines:
                continue
            
            # 回复消息
            if '[被引用的消息][文本]' in content_lines[0]:
                quoted = ''
                idx = 1
                while idx < len(content_lines) and '[文本]' in content_lines[idx]:
                    idx += 1
                if idx < len(content_lines):
                    quoted = content_lines[idx].strip()
                    idx += 1
                reply = ''
                at = ''
                while idx < len(content_lines):
                    if '[文本]' in content_lines[idx]:
                        idx += 1
                        continue
                    if content_lines[idx].startswith('@'):
                        at_nickname = content_lines[idx].strip()[1:].strip()  # 移除@符号提取昵称
                        # 在映射表中查找对应的UID
                        at_uid = nickname_to_uid.get(at_nickname)
                        if at_uid:
                            formal_name = uid2name.get(at_uid, at_nickname)
                            at = f"[@{formal_name}]"
                        else:
                            at = f"[@{at_nickname}]"
                    else:
                        reply += content_lines[idx].strip()
                    idx += 1
                if quoted or reply or at:
                    # 截断reply内容
                    if len(reply) > 150:
                        reply = reply[:150]
                    msg = f"{msg_idx}. {time} {user}/{uid} 说:[回复:{quoted}];{at};{reply}".strip()
                    result.append(msg)
                    msg_idx += 1
                    last_time = current_time  # 更新上一条消息时间
            # 新增: 处理格式为 [笑哭-182] 类型的表情
            elif any(re.match(r'\[\w+-\d+\]', line) for line in content_lines):
                # 收集所有表情
                emojis = []
                for line in content_lines:
                    if re.match(r'\[\w+-\d+\]', line):
                        emojis.append(line)
                
                if emojis:
                    emoji_text = ";".join(emojis)
                    msg = f"{msg_idx}. {time} {user}/{uid} 说:{emoji_text}"
                    result.append(msg)
                    msg_idx += 1
                    last_time = current_time
            # 表情消息
            elif '[表情]' in content_lines[0]:
                if len(content_lines) > 1:
                    emoji = content_lines[1]
                    msg = f"{msg_idx}. {time} {user}/{uid} 说:[{emoji}]"
                    result.append(msg)
                    msg_idx += 1
                    last_time = current_time  # 更新上一条消息时间
            # 图片消息
            elif content_lines[0] == '[' and len(content_lines) > 1 and content_lines[1].startswith('图'):
                # 检查是否有图片附带的文本内容
                img_text = ""
                if len(content_lines) > 2:
                    img_text = ' '.join(content_lines[2:]).strip()
                
                if img_text:
                    msg = f"{msg_idx}. {time} {user}/{uid}说:[图片] {img_text}"
                else:
                    msg = f"{msg_idx}. {time} {user}/{uid}说:[图片]"
                
                result.append(msg)
                msg_idx += 1
                last_time = current_time
            # 普通文本消息
            elif '[文本]' in content_lines[0]:
                msg_content = ''
                for cl in content_lines:
                    if '[文本]' in cl:
                        continue
                    # 检查是否包含@某人的信息
                    if cl.startswith('@'):
                        at_nickname = cl[1:].strip()  # 移除@符号提取昵称
                        # 在映射表中查找对应的UID
                        at_uid = nickname_to_uid.get(at_nickname)
                        if at_uid:
                            formal_name = uid2name.get(at_uid, at_nickname)
                            msg_content += f"[@{formal_name}]"
                        else:
                            msg_content += f"[@{at_nickname}]"
                    else:
                        msg_content += cl
                # 截断文本内容
                if len(msg_content) > 150:
                    msg_content = msg_content[:150]
                if msg_content:
                    msg = f"{msg_idx}. {time} {user}/{uid} 说:{msg_content}"
                    result.append(msg)
                    msg_idx += 1
                    last_time = current_time  # 更新上一条消息时间
        else:
            i += 1
    return result

# 示例用法
if __name__ == "__main__":
    with open("process_emoji.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
    processed = process_chat(lines)
    with open("process_formalise.txt", "w", encoding="utf-8") as f:
        for line in processed:
            f.write(line.strip() + "\n")