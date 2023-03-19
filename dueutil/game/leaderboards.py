import threading
import time
from collections import namedtuple

from cachetools.func import ttl_cache

from .. import dbconn, events, util
from ..game import players

leaderboards = dict()
last_leaderboard_update = 0
UPDATE_INTERVAL = 3600 / 12

_LocalLeaderboard = namedtuple("LocalLeaderboard", ["updated", "data"])


def calculate_player_rankings(rank_name, sort_function, reverse=True):
    ranked_players = sorted(
        filter(lambda player: player.id != util.gconf.DEAD_BOT_ID, players.players.values()),
        key=sort_function,
        reverse=reverse,
    )

    leaderboards[rank_name] = (tuple(player.id for player in ranked_players), sort_function, reverse)

    ranks = []
    for rank, player_id in enumerate(leaderboards[rank_name][0]):
        ranks.append({"rank": rank + 1, "player_id": player_id})

    if len(ranks) > 0:
        db = dbconn.conn()
        db.drop_collection(rank_name)
        db[rank_name].create_index("rank", unique=True)
        db[rank_name].create_index("player_id", unique=True)
        db[rank_name].insert_many(ranks, ordered=False)


def calculate_level_leaderboard():
    calculate_player_rankings("levels", lambda player: player.total_exp)


def get_leaderboard(rank_name):
    if rank_name in leaderboards:
        return leaderboards[rank_name][0]


@ttl_cache(maxsize=32, ttl=3600)
def get_local_leaderboard(guild, rank_name):
    rankings = get_leaderboard(rank_name)
    if rankings is not None:
        rankings = list(
            filter(
                lambda player_id: guild.get_member(player_id) is not None and player_id != util.gconf.DEAD_BOT_ID,
                rankings,
            )
        )
        return _LocalLeaderboard(updated=last_leaderboard_update, data=rankings)


def get_rank(player, rank_name, guild=None):
    if guild is not None:
        # Local
        rankings = get_local_leaderboard(guild, rank_name).data
    else:
        rankings = get_leaderboard(rank_name)
    try:
        return rankings.index(player.id) + 1
    except (ValueError, IndexError):
        return -1


async def update_leaderboards(_):
    global last_leaderboard_update
    if time.time() - last_leaderboard_update >= UPDATE_INTERVAL:
        last_leaderboard_update = time.time()
        leaderboard_thread = threading.Thread(target=calculate_updates)
        leaderboard_thread.start()
        util.logger.info("Global leaderboard updated!")


def calculate_updates():
    for rank_name, data in leaderboards.items():
        calculate_player_rankings(rank_name, data[1], data[2])


events.register_message_listener(update_leaderboards)
calculate_level_leaderboard()
