# ----------------------------------------------------------------------------------------------------------------------
# - Package Imports -
# ----------------------------------------------------------------------------------------------------------------------
# General Packages
from __future__ import annotations
from dataclasses import dataclass, field
import asyncio

# Custom Library

# Custom Packages
from AthenaTwitchBot.models.protocols.protocol_twitch import ProtocolTwitch
from AthenaTwitchBot.models.protocols.protocol_server import ProtocolServer
from AthenaTwitchBot.models.data_handlers.data_handler_server import DataHandlerServer
from AthenaTwitchBot.models.data_handlers.data_handler_twitch import DataHandlerTwitch


from AthenaTwitchBot.data.connections import *

# ----------------------------------------------------------------------------------------------------------------------
# - All -
# ----------------------------------------------------------------------------------------------------------------------
__all__ = ["Launcher"]

# ----------------------------------------------------------------------------------------------------------------------
# - Code -
# ----------------------------------------------------------------------------------------------------------------------
@dataclass(slots=True, kw_only=True)
class Launcher:
    protocol_twitch_type:type[ProtocolTwitch]=ProtocolTwitch
    protocol_server_type:type[ProtocolServer]=ProtocolServer

    loop:asyncio.AbstractEventLoop=field(default_factory=asyncio.get_event_loop)

    ssl_twitch_enabled:bool=True

    server_connection:bool=False
    ssl_server_enabled:bool=False
    server_host:str=None
    server_port:int=None

    console_output: bool = True

    # non init
    protocol_twitch:ProtocolTwitch=field(init=False, default=None)
    protocol_server:ProtocolServer=field(init=False, default=None)

    def launch(self):
        # create the connection to twitch and handle basic setup
        self.loop.run_until_complete(
            self.create_connection_twitch()
        )
        # If the setting is enabled, also create a connection to and from an external server
        #   Meant to handle connections like logging to a database, GUI system, etc...
        if self.server_connection:
            self.loop.run_until_complete(
                self.create_connection_server()
            )


        # run everything that is in the loop forever
        self.loop.run_forever()
        self.loop.close()

    async def create_connection_twitch(self):
        _, self.protocol_twitch = await self.loop.create_connection(
            protocol_factory=self.protocol_twitch_type.factory(
                data_handler=DataHandlerTwitch()
            ),
            host=TWITCH_IRC_HOST if not self.ssl_twitch_enabled else TWITCH_IRC_HOST_SSL,
            port=TWITCH_IRC_PORT if not self.ssl_twitch_enabled else TWITCH_IRC_PORT_SSL,
            ssl=self.ssl_twitch_enabled
        )

    async def create_connection_server(self):
        if self.server_host is None:
            raise ValueError
        elif self.server_port is None:
            raise ValueError

        _, self.protocol_server = await self.loop.create_connection(
            protocol_factory=self.protocol_server.factory(
                data_handler=DataHandlerServer()
            ),
            host=self.server_host,
            port=self.server_port,
            ssl=self.ssl_server_enabled
        )
