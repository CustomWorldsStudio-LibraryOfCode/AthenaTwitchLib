# ----------------------------------------------------------------------------------------------------------------------
# - Package Imports -
# ----------------------------------------------------------------------------------------------------------------------
# General Packages
from __future__ import annotations
import asyncio
import re
from dataclasses import dataclass, field
import functools
from typing import Any, Callable

# Athena Packages
from AthenaColor import ForeNest as Fore

# Local Imports
from AthenaTwitchBot.regex import RegexPatterns
from AthenaTwitchBot.bot_settings import BotSettings
from AthenaTwitchBot.logic.logic_bot import LogicBot
from AthenaTwitchBot.tags import TagsPRIVMSG, TagsUSERSTATE
from AthenaTwitchBot.bot_logger import BotLogger
from AthenaTwitchBot.logic import LogicMemory, MessageLogic
from AthenaTwitchBot.message_context import MessageContext
from AthenaTwitchBot.bot_event_types import BotEvent

# ----------------------------------------------------------------------------------------------------------------------
# - Support Code -
# ----------------------------------------------------------------------------------------------------------------------
class _TransportBuffer:
    """
    Simple class to be used by the `BotConnectionProtocol`, before the transporter object is actually set.
    It keeps the to be sent message into a small buffer, for it to then be parsed and deleted once the
    actual transporter is present in the `BotConnectionProtocol`
    """
    buffer: list[bytes] = []

    @classmethod
    def write(cls, data:bytes):
        cls.buffer.append(data)

def track_handler(fnc:Callable) -> Any:
    """
    Simple decorator to keep track of how many calls are made to handlers
    """

    @functools.wraps(fnc)
    async def wrapper(*args, **kwargs):
        result, *_ = await asyncio.gather(
            fnc(*args, **kwargs),
            BotLogger.logger.log_handler_called(fnc.__name__),
            BotLogger.logger.log_handled_message(line=kwargs.get("line",None))
        )
        return result

    return wrapper

# ----------------------------------------------------------------------------------------------------------------------
# - Code -
# ----------------------------------------------------------------------------------------------------------------------
@dataclass(slots=True)
class BotConnectionProtocol(asyncio.Protocol):
    """
    Asyncio.Protocol child class,
    Holds all logic to convert the incoming Twitch IRC messages to useful calls/data
    """
    settings: BotSettings
    regex_patterns: RegexPatterns
    bot_logic: LogicBot
    bot_event_future: asyncio.Future

    _transport: asyncio.transports.Transport = None  # delayed as it has to be set after the connection has been made
    _loop :asyncio.AbstractEventLoop = field(init=False)

    def __post_init__(self):
        self._loop = asyncio.get_running_loop()

    # ------------------------------------------------------------------------------------------------------------------
    # - Properties -
    # ------------------------------------------------------------------------------------------------------------------
    @property
    def transport(self):
        """
        Getter of the `transport` property
        This is necessary as transport is set later by the constructor than when the protocol is created
        When the transport isn't set yet, it will store write data to a temp buffer
        This buffer will be removed after the setter of the `transport` property is called
        """
        if self._transport is None:
            return _TransportBuffer

        return self._transport

    @transport.setter
    def transport(self, value:asyncio.transports.Transport):
        """
        Setter of the `transport` property
        Executes any write calls in the buffer, and the deletes the buffer
        """
        self._transport = value

        if _TransportBuffer.buffer:
            for data in _TransportBuffer.buffer:
                self._transport.write(data)

            _TransportBuffer.buffer.clear()

    # ------------------------------------------------------------------------------------------------------------------
    # - Protocol Calls (aka, calls made by asyncio.Protocol) -
    # ------------------------------------------------------------------------------------------------------------------
    def data_received(self, data: bytearray) -> None:
        """
        First hit of the protocol when it receives data from Twitch IRC
        Because twitch sends in this data in bytes, and sometimes multiple different message,
        the function has to decode and split the data on every new line
        """

        # TODO sort on most used messages

        for line in data.decode().split("\r\n"):
            # An Empty line
            if not line:
                continue

            elif message := self.regex_patterns.message.match(line):
                if cmd_match := self.regex_patterns.message_command.match(message.groups()[-1]):
                    self._loop.create_task(self.handle_message_command(message,cmd_match,line=line))
                else:
                    self._loop.create_task(self.handle_message(message, line=line))

            elif line == "PING :tmi.twitch.tv":
                self._loop.create_task(self.handle_ping(line=line))

            elif server_message := self.regex_patterns.server_message.match(line):
                self._loop.create_task(self.handle_server_message(server_message, line=line))

            elif join := self.regex_patterns.join.match(line):
                self._loop.create_task(self.handle_join(join, line=line))

            elif part := self.regex_patterns.part.match(line):
                self._loop.create_task(self.handle_part(part, line=line))

            elif server_353 := self.regex_patterns.server_353.match(line):
                self._loop.create_task(self.handle_server_353(server_353, line=line))

            elif server_366 := self.regex_patterns.server_366.match(line):
                self._loop.create_task(self.handle_server_366(server_366, line=line))

            elif server_cap := self.regex_patterns.server_cap.match(line):
                self._loop.create_task(self.handle_server_cap(server_cap, line=line))

            elif user_notice := self.regex_patterns.user_notice.match(line):
                self._loop.create_task(self.handle_user_notice(user_notice, line=line))

            elif user_state := self.regex_patterns.user_state.match(line):
                self._loop.create_task(self.handle_user_state(user_state, line=line))

            else:
                self._loop.create_task(self.handle_UNKNOWN(line))

    def connection_lost(self, exc: Exception | None) -> None:
        # TODO, something here
        if exc is not None:
            print(exc)

        if not self.bot_event_future.done():
            self.bot_event_future.set_result(BotEvent.RESTART)

    # ------------------------------------------------------------------------------------------------------------------
    # - Line handlers -
    # ------------------------------------------------------------------------------------------------------------------
    @track_handler
    async def handle_ping(self,*, line):
        """
        Method is called when the Twitch server sends a keep alive PING message
        Needs to have the reply: `"PONG :tmi.twitch.tv` for the connection to remain alive
        """
        print(f"{Fore.Peru('PONG')} | {line}")

        # Need to keep alive
        self.transport.write("PONG :tmi.twitch.tv\r\n".encode())

    @track_handler
    async def handle_server_message(self, server_message:re.Match, *, line:str):
        """
        Method is called when the Twitch server sends a message that isn't related to any user or room messages
        """
        print(f"{Fore.Blue('SERVER_MESSAGE')} | {line}")


    @track_handler
    async def handle_server_353(self, server_353: re.Match, *, line: str):
        """
        Method is called when twitch sends a 353 message
        """
        print(f"{Fore.AliceBlue('SERVER_353')} | {line}")

    @track_handler
    async def handle_server_366(self, server_366: re.Match, *, line: str):
        """
        Method is called when twitch sends a 353 message
        """
        print(f"{Fore.Ivory('SERVER_366')} | {line}")

    @track_handler
    async def handle_server_cap(self, server_cap: re.Match, *, line: str):
        """
        Method is called when twitch sends a CAP message
        """
        print(f"{Fore.Khaki('SERVER_CAP')} | {line}")

    @track_handler
    async def handle_join(self, join:re.Match,*, line:str):
        """
        Method is called when any user (bot or viewer) joins the channel
        """
        print(f"{Fore.Red('JOIN')} | {line}")

    @track_handler
    async def handle_part(self, part:re.Match, *, line:str):
        """
        Method is called when any user (bot or viewer) parts the channel
        """
        print(f"{Fore.DeepPink('PART')} | {line}")

    @track_handler
    async def handle_message(self, message:re.Match, *, line:str):
        """
        Method is called when any user (bot or viewer) sends a regular message in the channel
        """
        print(f"{Fore.Orchid('MESSAGE')} | {message.groups()[-1]} | {Fore.SlateGray(line)}")

        # Extract data from matched message
        #   Easily done due to regex groups
        tags_group_str,user,channel,text = message.groups()

        # extract the logic
        #   If no logic can be found, not further actions need to be taken
        if not (msg_logic := LogicMemory.get_normal_message_logic(channel, default=False)):
            return

        # Create the context and run more checks
        message_context = MessageContext(
            tags=await TagsPRIVMSG.import_from_group_as_str(tags_group_str),
            user=user,
            channel=channel,
            text=text,
            transport=self.transport,
            bot_event_future=self.bot_event_future
        )
        await msg_logic.coroutine(message_context=message_context)

    @track_handler
    async def handle_message_command(self, message:re.Match, cmd_match:re.Match, *, line:str):
        """
        Method is called when any user (bot or viewer) sends a message in the channel,
        which is presumed to be a bot command
        """
        print(f"{Fore.Orchid('MESSAGE_COMMAND_WITH_ARGS')} | {message.groups()[-1]} | {Fore.SlateGray(line)}")

        # Extract data from matched message
        #   Easily done due to regex groups
        tags_group_str,user,channel,text = message.groups()
        command, *args = cmd_match.groups()

        # extract the logic
        #   If no logic can be found, not further actions need to be taken
        if not (cmd_logic := LogicMemory.get_command_logic(channel, command, default=False)):
            return

        message_context = MessageContext(
            tags=await TagsPRIVMSG.import_from_group_as_str(tags_group_str),
            user=user,
            channel=channel,
            text=f"!{command} {args}",
            transport=self.transport,
            bot_event_future=self.bot_event_future
        )

        # actually call the command
        await cmd_logic.coroutine(message_context=message_context)

    @track_handler
    async def handle_message_command_without_args(self, message: re.Match, cmd_match:re.Match, *, line: str):
        """
        Method is called when any user (bot or viewer) sends a message in the channel,
        which is presumed to be a bot command
        """
        print(f"{Fore.Orchid('MESSAGE_COMMAND_WITHOUT_ARGS')} | {message.groups()[-1]} | {Fore.SlateGray(line)}")

        # Extract data from matched message
        #   Easily done due to regex groups
        tags_group_str, user, channel, command = message.groups()
        command, = cmd_match.groups()

        # extract the logic
        #   If no logic can be found, not further actions need to be taken
        if cmd_logic := LogicMemory.get_command_logic(channel, default=False):
            return

        message_context = MessageContext(
            tags=await TagsPRIVMSG.import_from_group_as_str(tags_group_str),
            user=user,
            channel=channel,
            text=f"!{command}",
            transport=self.transport,
            bot_event_future=self.bot_event_future
        )

        # String is a command
        await cmd_logic.coroutine(message_context=message_context)

    @track_handler
    async def handle_user_notice(self, user_notice:re.Match, *, line:str):
        """
        Method is called when twitch sends a USERNOTICE message
        """
        print(f"{Fore.Plum('USERNOTICE')} | {line}")

    @track_handler
    async def handle_user_state(self, user_state:re.Match, *, line:str):
        """
        Method is called when twitch sends a USERSTATE message
        """
        tags_group_str,channel = user_state.groups()
        tags = await TagsUSERSTATE.import_from_group_as_str(tags_group_str)
        print(f"{Fore.Plum('USERSTATE')} | {line} | {tags}")

    @track_handler
    async def handle_UNKNOWN(self, line:str):
        """
        Method is called when the protocol can't find an appropriate match for the given string
        """
        print(Fore.SlateGray(f"NOT CAUGHT | {line}"))
        await BotLogger.logger.log_unknown_message(line)