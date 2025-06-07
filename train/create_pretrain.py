import os
import json
import re
from datetime import datetime
from openai import OpenAI
import time # 引入 time 模块用于处理可能的速率限制

# 这是一个为floating生成微调语料的python脚本，目的是基于已有的历史聊天记录，生成一段思考和发言的内容。
# todo: 1.调用api生成思考和发言内容 (已完成)
# 2.把格式化后的generated_think内容写入到文件中. (已完成)

# 角色扮演与思维链生成指令
geneate_think="""# 角色扮演与思维链生成指令
## 任务
你将扮演群聊成员{user_name}。你的任务是基于他在聊天记录中展现出的风格和当前对话的上下文，反向推演出最真实的内心思考。

## 背景
通过以下的聊天记录，你可以观察和学习 {user_name} 的说话风格、个性和思维模式。

## 聊天记录
{chat_history}

## {user_name} 的目标发言
`{actual_response}`

## 你的任务
请完全代入 {user_name} 的角色，**仅仅依据上面聊天记录所展示出的风格**，推演出为了说出那句“目标发言”，他最真实的内心思考过程是怎样的。让思考过程自然、符合直觉，避免过度分析或解释。

## 输出格式
<think>
（在这里写下你的思考过程）
</think>
<response>
{actual_response}
</response>
"""


class ChatParser:
    """聊天记录解析器，负责解析聊天窗口文本"""
    
    @staticmethod
    def parse_chat_windows(chat_text):
        """解析聊天窗口，返回解析后的窗口列表"""
        # 使用更稳健的正则表达式来分割窗口
        window_pattern = r'==================================================\n窗口 #\d+.*?(?=\n==================================================|\Z)'
        windows = re.findall(window_pattern, chat_text, re.DOTALL)
        
        parsed_windows = []
        for window_content in windows:
            # 提取窗口编号
            window_id_match = re.search(r'窗口 #(\d+)', window_content)
            window_id = int(window_id_match.group(1)) if window_id_match else 0
            
            # 提取时间
            time_match = re.search(r'# 窗口起始时间: ([\d-]+ [\d:]+)', window_content)
            start_time = time_match.group(1) if time_match else ""
            
            # 提取行范围
            range_match = re.search(r'# 行范围: (\d+)-(\d+)', window_content)
            start_line = int(range_match.group(1)) if range_match else 0
            end_line = int(range_match.group(2)) if range_match else 0
            
            # 提取分割原因
            reason_match = re.search(r'# 分割原因: (.+)', window_content)
            split_reason = reason_match.group(1).strip() if reason_match else ""
            
            # 提取消息
            # 修正了消息提取的正则表达式，使其能正确处理包含特殊字符的用户名和内容
            message_pattern = re.compile(r'(\d+)\. (.+?)/(\d+)\s+说:(.*)')
            messages = []
            
            # 只处理消息部分，忽略注释和标题
            lines = window_content.split('\n')
            message_lines = [line for line in lines if not line.startswith('#') and not line.startswith('===') and line.strip()]

            for line in message_lines:
                 # 跳过间隔标记
                if line.startswith('[间隔'):
                    continue

                msg_match = message_pattern.match(line)
                if msg_match:
                    position = int(msg_match.group(1))
                    username = msg_match.group(2).strip()
                    user_id = msg_match.group(3).strip()
                    content = msg_match.group(4).strip()
                    
                    # 如果内容为空，但行中包含[图片]，则将内容设为[图片]
                    if not content and '[图片]' in line:
                        content = "[图片]"
                    
                    if content: # 只添加有内容的消息
                        messages.append({
                            "position": position,
                            "username": username,
                            "user_id": user_id,
                            "content": content
                        })

            if messages: # 仅当窗口中有有效消息时才添加
                parsed_windows.append({
                    "window_id": window_id,
                    "start_time": start_time,
                    "line_range": (start_line, end_line),
                    "split_reason": split_reason,
                    "messages": messages
                })
        
        return parsed_windows
    
    @staticmethod
    def extract_user_messages(windows, username):
        """提取特定用户的消息及其上下文"""
        user_messages_with_context = []
        
        for window in windows:
            messages_in_window = window["messages"]
            for i, msg in enumerate(messages_in_window):
                if msg["username"] == username:
                    # 构建上下文（当前消息之前的所有消息）
                    # 注意：上下文只包含当前消息之前的部分
                    context_messages = messages_in_window[:i]
                    
                    # 格式化上下文
                    context_str = "\n".join(
                        f"{context_msg['username']}: {context_msg['content']}" 
                        for context_msg in context_messages
                    )
                    
                    user_messages_with_context.append({
                        "window_id": window["window_id"],
                        "position": msg["position"],
                        "content": msg["content"], # 这是AI需要说的"实际发言"
                        "context": context_str  # 这是提供给AI的"聊天记录"
                    })
        
        return user_messages_with_context

class CreateThink:
    """生成思考和发言的类"""
    
    def __init__(self, openai_client):
        self.openai_client = openai_client
    
    # ------------------- TODO 1: 调用API生成思考和发言内容 (已完成) -------------------
    def generate_think(self, user_name, chat_history, actual_response):
        """生成思考和发言"""
        prompt = geneate_think.format(
            user_name=user_name,
            chat_history=chat_history if chat_history else "（无上下文，你是第一个发言）", # 处理没有历史记录的情况
            actual_response=actual_response
        )
        
        try:
            response = self.openai_client.chat.completions.create(
                model="deepseek-chat", # 确保你的API提供商支持此模型
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7, # 可以适当调整以获得更多样化的思考过程
                max_tokens=1024,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"调用API时出错: {e}")
            # 可以选择等待一段时间后重试
            time.sleep(5) 
            return None # 返回 None 表示失败

def main():
    # ---- 初始化客户端 ----
    # 请确保已设置环境变量 DEEPSEEK_API_KEY，或在此处直接提供
    try:
        client = OpenAI(api_key=os.getenv("api_key"),base_url=os.getenv("base_url", "https://api.deepseek.com/v1"))
    except TypeError:
        print("错误：请设置环境变量 'DEEPSEEK_API_KEY'。")
        print("例如: export DEEPSEEK_API_KEY='你的sk-xxxx密钥'")
        return

    # ---- 配置参数 ----
    target_user_name = "Floating." # 你想要为其生成语料的用户名
    input_filepath = "all_windows_merged.txt" # 包含聊天记录的输入文件
    output_filepath = "output.jsonl" # 输出的微调语料文件

    # ---- 读取和解析聊天记录 ----
    print(f"正在从 '{input_filepath}' 读取聊天记录...")
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            chat_text = f.read()
    except FileNotFoundError:
        print(f"错误: 输入文件 '{input_filepath}' 未找到。请创建该文件并填入聊天记录。")
        return

    parsed_windows = ChatParser.parse_chat_windows(chat_text)
    user_messages = ChatParser.extract_user_messages(parsed_windows, target_user_name)
    
    if not user_messages:
        print(f"在文件中未找到用户 '{target_user_name}' 的任何消息。")
        return

    print(f"成功解析聊天记录。找到用户 '{target_user_name}' 的 {len(user_messages)} 条消息。")

    # ---- 初始化生成器 ----
    think_generator = CreateThink(client)

    # ------------------- TODO 2: 把格式化后的内容写入到文件中 (已完成) -------------------
    print(f"开始生成思考过程并写入到 '{output_filepath}'...")
    
    # ---- 循环处理每条消息并生成语料 ----
    with open(output_filepath, 'a', encoding='utf-8') as f:
        for i, message_data in enumerate(user_messages):
            print(f"正在处理第 {i+1}/{len(user_messages)} 条消息 (窗口ID: {message_data['window_id']})...")
            
            # 调用API生成思考和响应
            generated_xml = think_generator.generate_think(
                user_name=target_user_name,
                chat_history=message_data["context"],
                actual_response=message_data["content"]
            )
            
            if generated_xml:
                # 构建符合OpenAI微调格式的JSON对象
                # 这种格式通常包含一个 'messages' 列表
                system_prompt = f"你将扮演一个群聊成员{target_user_name}。"
                user_content = f"## 当前聊天记录\n{message_data['context']}\n\n## 你的任务\n请进行内心思考，然后说出以下这句话：`{message_data['content']}`"

                fine_tune_data = {
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": generated_xml}
                    ]
                }
                
                # 将JSON对象转换为字符串并写入文件，后跟换行符
                f.write(json.dumps(fine_tune_data, ensure_ascii=False) + '\n')
                print(f"  > 第 {i+1} 条语料已成功生成并写入文件。")
            else:
                print(f"  > 第 {i+1} 条消息处理失败，已跳过。")
    
    print("\n处理完成！")
    print(f"所有生成的微调语料都已保存到 '{output_filepath}' 文件中。")


if __name__ == "__main__":
    main()