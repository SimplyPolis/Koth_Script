import asyncio
import datetime
import enum
import math
import os
from typing import Iterable, Iterator, NamedTuple, Optional
import requests
import auraxium
import uvicorn
from auraxium import census, event
import socketio
from collections import deque, ChainMap

facility_to_track = 298000
world_id = 19
service_id = "MEGABIGSTATS"


# async def main():
#     # NOTE: Depending on player activity, this script may exceed the ~6
#
#
#     async with auraxium.Client(service_id='s:MEGABIGSTATS') as client:
#         query = census.Query('map',world_id=19,zone_ids=8,service_id='s:MEGABIGSTATS')
#         join=query.create_join("map_region")
#         join.set_inject_at("facility_join_Regions.Row.RowData.RegionId")
#
#         print(query.url())
#         response= await  client.request(query)
#         print(response)
async def on_startup() -> None:
    pass


static_files = {
    '/admin': 'admin.html',
    '/static': './static',
    "/": "overlay.html"
}
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*", logger=True)

game_lock = asyncio.Lock()
game_start_event = asyncio.Event()


class GameState(enum.IntEnum):
    IMMINENT = 0
    UNDERWAY = 1
    PAUSED = 2
    OVERTIME = 3
    RESOLVED = 4


class Faction(enum.IntEnum):
    NULL = 0
    VS = 1
    NC = 2
    TR = 3
    NSO = 4


class Game:
    def __init__(self):
        self.scores = [0, 0, 0, 0]
        self.time = 0
        self.game_state = GameState.IMMINENT

    def startGame(self):
        if self.game_state == GameState.IMMINENT or self.game_state == GameState.PAUSED:
            self.game_state = GameState.UNDERWAY

    def pauseGame(self):
        if self.game_state == GameState.UNDERWAY:
            self.game_state = GameState.PAUSED

    def resetGame(self):
        if self.game_state == GameState.PAUSED:
            self.game_state = GameState.IMMINENT
            self.scores = [0, 0, 0, 0]
            self.time = 0

    def getTime(self) -> str:
        return f"{datetime.timedelta(seconds=self.time)}"

    def getTimeVS(self) -> str:
        return f"{datetime.timedelta(seconds=self.scores[1])}" if self.scores[1] else ""

    def getTimeNC(self) -> str:
        return f"{datetime.timedelta(seconds=self.scores[2])}" if self.scores[2] else ""

    def getTimeTR(self) -> str:
        return f"{datetime.timedelta(seconds=self.scores[3])}" if self.scores[3] else ""

    def getDict(self) -> dict:
        return {
            "match-status": self.game_state,
            "time": self.getTime(),
            "timeVS": self.getTimeVS(),
            "timeNC": self.getTimeNC(),
            "timeTR": self.getTimeTR()
        }


game: Optional[Game] = None


async def gameLoop():
    global game
    global game_lock
    # game_task = asyncio.current_task()
    client = auraxium.event.EventClient(service_id='s:MEGABIGSTATS')

    @client.trigger(event.FacilityControl, worlds=[19])
    async def trackFacilityControl(evt: event.FacilityControl):
        if evt.facility_id != facility_to_track:
            return
        async with game_lock:
            game.scores[evt.old_faction_id] = max(game.scores[evt.old_faction_id], game.time)
            game.time = 0


async def timerLoop():
    global game
    global game_lock
    global game_start_event
    while True:
        async with game_lock:
            await sio.emit('game_score', game.getDict())
            if game.game_state == GameState.UNDERWAY:
                game.time += 1
        await asyncio.sleep(1)


@sio.event
async def connect(sid, environ, auth):
    global game
    global game_lock
    async with game_lock:
        await sio.emit('game_score', game.getDict())


@sio.on('game_score_start')
async def startEvent(sid):
    global game
    global game_lock
    async with game_lock:
        game.startGame()


@sio.on('game_score_pause')
async def pauseEvent(sid):
    global game
    global game_lock
    async with game_lock:
        game.pauseGame()


@sio.on('game_score_reset')
async def resetEvent(sid):
    global game
    global game_lock
    async with game_lock:
        game.resetGame()


async def onStartup():
    global game_start_event
    global game
    game = Game()
    sio.start_background_task(gameLoop)
    sio.start_background_task(timerLoop)


app = socketio.ASGIApp(sio, static_files=static_files, on_startup=onStartup)
if __name__ == '__main__':
    config = uvicorn.Config("main:app", port=8080, log_level="info")
    server = uvicorn.Server(config)
    server.run()
