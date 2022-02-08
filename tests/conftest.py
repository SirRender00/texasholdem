"""
Config for all tests. Includes:
    - Fixture for a directory path for game history files.
    - Method for stripping comments from a history string.
"""
import os
from typing import Union
from pathlib import Path

import tests


GOOD_GAME_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_good_pgns"
"""
The path of the directory of the history files with valid game examples
"""

BAD_GAME_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_bad_pgns"
"""
The path of the directory of the history files with INVALID game examples
"""

BAD_FORMAT_HISTORY_DIRECTORY = Path(tests.__file__).parent / "pgns/test_bad_format_pgns"
"""
The path of the directory of the history files with INVALID pgns (as opposed to invalid moves)
"""


def strip_comments(history_path: Union[str, os.PathLike]) -> str:
    """
    Arguments:
        history_path (Union[str, os.PathLike]): A path to a history pgn
    Returns:
        str: The history string without comments
    """
    with open(history_path, mode='r', encoding='ascii') as file:
        history_string = file.read()

        new_lines = []
        for line in history_string.split('\n'):
            comment_index = line.find('#')

            if comment_index == -1:
                new_lines.append(line)
            elif comment_index != 0:
                new_lines.append(line[:comment_index].strip())

        return '\n'.join(new_lines)
