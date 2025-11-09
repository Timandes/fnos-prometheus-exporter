with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(75, 85):
        print(f"{i+1}: {repr(lines[i])}")