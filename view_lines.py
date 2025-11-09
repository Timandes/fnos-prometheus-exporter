with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(55, 62):  # 查看相关行
        print(f"{i+1}: {repr(lines[i])}")