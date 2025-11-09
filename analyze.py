import re
with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 查找从 '# Global variables to maintain connection and system info instance' 开始的段落
start_marker = '# Global variables to maintain connection and system info instance'
start_pos = content.find(start_marker)
if start_pos != -1:
    # 从开始位置向后读取约10行来获取完整段落
    lines = content[start_pos:].split('\n')
    for i, line in enumerate(lines[:15]):  # 取前15行
        print(f'{i}: {repr(line)}')