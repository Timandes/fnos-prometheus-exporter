# Copyright 2025 Timandes White
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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