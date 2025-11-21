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


"""

Common utility functions for fnOS Prometheus Exporter

"""

import re


def camel_to_snake(name):
    """Convert camelCase to snake_case"""
    # Insert underscores before uppercase letters that follow lowercase letters or digits
    s1 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    return s1.lower()


def flatten_dict(d, parent_key='', sep='_'):
    """
    Flatten a nested dictionary by concatenating keys with separator

    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator to use between keys

    Returns:
        dict: Flattened dictionary
    """
    items = []
    for k, v in d.items():
        # Convert camelCase key to snake_case
        converted_key = camel_to_snake(k)
        new_key = f"{parent_key}{sep}{converted_key}" if parent_key else converted_key
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
