# ----------------------------------------------------------------------------------------------------------------------
# - Package Imports -
# ----------------------------------------------------------------------------------------------------------------------
# General Packages
from __future__ import annotations
import asyncio
import re
import dataclasses

# Athena Packages
from AthenaColor import ForeNest as Fore

# Local Imports
from AthenaTwitchLib.irc.irc_line_handler import IrcLineHandler

# ----------------------------------------------------------------------------------------------------------------------
# - Code -
# ----------------------------------------------------------------------------------------------------------------------
@dataclasses.dataclass(slots=True)
class LineHandler_Server366(IrcLineHandler):
    """
    Class is called when twitch sends a 353 message
    """
    _console_color:Fore = Fore.Ivory

    async def _output_on_ingest_console(self, matched_content: re.Match, original_line: str):
        print(f"{self._console_color('SERVER_366')} | {original_line}")

    async def _output_on_ingest_logger(self, matched_content: re.Match, original_line: str):
        ...

    async def _handle_line(self, transport:asyncio.Transport, matched_content: re.Match, original_line: str):
        ...