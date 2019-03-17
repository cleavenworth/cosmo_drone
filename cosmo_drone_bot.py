#!/usr/bin/env python3

import os
import asyncio
import time
import types
import discord


from bungie_api import BungieLookup as BL

TOKEN = os.environ['DISCORD_KEY']
PERMISSION_INT = 84992

cosmodrone = discord.Client()

def format_lookup_message(score_list):
    msg = "\n"
    if isinstance(score_list, list):
        msg = "\n" + "**{}** - Current Triumph Score: **{}**".format(score_list[0], score_list[1])
    else:
        for player in score_list:
            msg_part = "**{}** - Current Triumph Score: **{}**".format(player, score_list[player]['score'])
            msg = msg + "\n" + msg_part
    return msg

def format_compare_message(score_data):
    msg = "\n"
    top_scorer_data = [score_data[0][0], score_data[0][1]]
    msg_part = "**{}** is in the lead with **{}** total Triumph Score.".format(top_scorer_data[0], top_scorer_data[1])
    msg = msg + "\n" + msg_part
    msg_part = "Highest to Lowest Scores:"
    msg = msg + "\n" + msg_part
    for player, score in score_data[1]:
        msg_part = "**{}** - **{}**".format(player, score)
        msg = msg + "\n" + msg_part
    return msg

def format_leaderboard_message(score_data):
    msg = "\n"
    top_scorer_data = [score_data[0][0], score_data[0][1]]
    msg_part = "**{}** is in the lead of all registered users with **{}** total Triumph Score.".format(top_scorer_data[0], top_scorer_data[1])
    msg = msg + "\n" + msg_part + "\n"
    msg_part = "Highest to Lowest Scores:"
    msg = msg + "\n" + msg_part
    for player, score in score_data[1]:
        msg_part = "**{}** - **{}**".format(player, score)
        msg = msg + "\n" + msg_part
    return msg

def build_top_five_message(score_data):
    embed_list = []
    bl = BL()
    for triumph in score_data:
        triumph_info = bl.get_triumph_info(triumph[0])
        embed = discord.Embed(title=triumph_info['displayProperties']['name'], \
        description=triumph_info['displayProperties']['description'], color=0x006eff)
        embed.add_field(name="Percent Complete", \
        value=str(round(triumph[1]['CompletionPercentage'], 2)) + "%")
        for objective in triumph[1]['objectiveHashes']:
            embed.add_field(name=triumph[1]['objectiveHashes'][objective]['progressDescription'], \
            value=str(triumph[1]['objectiveHashes'][objective]['progress']) + "/" + \
            str(triumph[1]['objectiveHashes'][objective]['completionValue']), inline=True)
        embed_list.append(embed)
    return embed_list

def perform_triumph_action(action, player_list=None, discord_user=None):
    # try:
    if isinstance(player_list, list):
        try:
            player_list = player_list.split()
            if len(player_list[0]) == 1:
                print("Split a string")
        except Exception as error:
            print(error)
    if not player_list:
        discord_flag = True
        # player_list = ""
    elif player_list.split()[0] == "me":
        discord_flag = True
    else:
        discord_flag = False
    # except IndexError:
        # player_list = ""
    if action == "lookup":
        if discord_flag == True:
            bl = BL(player=player_list, discord_lookup=discord_user)
            triumph_scores = bl.get_triumph_score_v2(bl.get_bungie_membership_id(bl.player))
        else:
            bl = BL(player=player_list)
            triumph_scores = bl.get_triumph_score_v2(bl.get_bungie_membership_id(bl.player))
    elif action == "compare":
        if discord_flag == True:
            bl = BL(player=player_list, discord_lookup=discord_user)
        else:
            bl = BL(player=player_list)
        triumph_scores = bl.compare_triumph_score(bl.player)
    elif action == 'leaderboard':
        bl = BL(leaderboard=True)
        triumph_scores = bl.triumph_leaderboard(bl.player)
    elif action == 'top_five':
        if discord_flag == True:
            bl = BL(discord_lookup=discord_user, player=player_list)
            triumph_scores = bl.top_five_closest_triumphs(bl.player)
        else:
            bl = BL(player=player_list)
            triumph_scores = bl.top_five_closest_triumphs(bl.player)
    return triumph_scores

def register_user(player, discord_user):
    bl = BL(player=player)
    bl.register_bnet_user(discord_user=discord_user, player=bl.player)

# class Timer:
#     def __init__(self, timeout, callback):
#         self._timeout = timeout
#         self._callback = callback
#         self._task = asyncio.ensure_future(self._job())
#
#     async def _job(self):
#         await asyncio.sleep(self._timeout)
#         await self._callback()
#
#     def cancel(self):
#         self._task.cancel()
#
#
# async def timeout_callback():
#     await asyncio.sleep(0.1)
#     print('echo!')
#
#
# async def main():
#     print('\nfirst example:')
#     timer = Timer(2, timeout_callback)  # set timer for two seconds
#     await asyncio.sleep(2.5)  # wait to see timer works
#
#     print('\nsecond example:')
#     timer = Timer(2, timeout_callback)  # set timer for two seconds
#     await asyncio.sleep(1)
#     timer.cancel()  # cancel it
#     await asyncio.sleep(1.5)  # and wait to see it won't call callback


# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)
# try:
#     loop.run_until_complete(main())
# finally:
#     loop.run_until_complete(loop.shutdown_asyncgens())
#     loop.close()



@cosmodrone.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == cosmodrone.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention}'.format(message)
        await cosmodrone.send_message(message.channel, msg)

    if message.content.startswith('!triumph_score'):
        await cosmodrone.send_message(message.channel, "Scanning the Cosmo Drone...")
        player_list = message.content[15:]
        score_list = perform_triumph_action(action="lookup", player_list=player_list, \
        discord_user="{0.author}".format(message))
        await cosmodrone.send_message(message.channel, "{0.author.mention}".format(message) + \
        format_lookup_message(score_list=score_list))

    if message.content.startswith('!triumph_compare'):
        await cosmodrone.send_message(message.channel, "Scanning the Cosmo Drone...")
        player_list = message.content[16:]
        score_data = perform_triumph_action(action="compare", player_list=player_list, \
        discord_user="{0.author}".format(message))
        await cosmodrone.send_message(message.channel, "{0.author.mention}".format(message) + \
        format_compare_message(score_data=score_data))

    if message.content.startswith('!triumph_leaderboard'):
        await cosmodrone.send_message(message.channel, "Scanning the Cosmo Drone Leaderboard... (This may take a few moments)")
        player_list = message.content[20:]
        score_data = perform_triumph_action(action="leaderboard", player_list=player_list, \
        discord_user="{0.author}".format(message))
        await cosmodrone.send_message(message.channel, "{0.author.mention}".format(message) + \
        format_leaderboard_message(score_data=score_data))

    if message.content.startswith('!triumph_register'):
        player = message.content[18:]
        await cosmodrone.send_message(message.channel, "Uploading Your BattleNet Tag to "\
        "the Cosmo Drone...")
        register_user(player, discord_user="{0.author}".format(message))
        await cosmodrone.send_message(message.channel, "Your BattleNet Tag has been "\
        "saved to your Discord user. You can now use `!triumph_score me` or just "\
        "`!triumph_score` to view your current Triumph Score.")

    if message.content.startswith('!triumph_vs_tracker'):
        player_list = message.content[20:].split()
        vs_list = " vs. ".join(f"**{x}**" for x in player_list)
        print(vs_list)
        print(player_list)
        await cosmodrone.send_message(message.channel, "Setting Up Vs Tracker for {}".format(vs_list))

    if message.content.startswith('!triumph_top_five'):
        player = message.content[18:]
        await cosmodrone.send_message(message.channel, "{0.author.mention} "\
        "gathering your triumph info. Check your DMs in a moment!".format(message))
        score_data = perform_triumph_action(action="top_five", \
        discord_user="{0.author}".format(message), player_list=player)
        await cosmodrone.send_message(message.author, "{0.author.mention} "\
        "your closest triumphs are...".format(message))
        embed_list = build_top_five_message(score_data)
        for embed in embed_list:
            await cosmodrone.send_message(message.author, embed=embed)
            await asyncio.sleep(1.5)
        # except Exception as error:
        #     print(error)

    if message.content.startswith('!help'):
        await cosmodrone.send_message(message.author, \
        "Register first using `!triumph_register YourBNetTag`")

# async def clock():
#     while True:
#         from datetime import timedelta, datetime
#         cosmodrone.now.now = datetime.now()
#         await asyncio.sleep(1)
#         if


@cosmodrone.event
async def on_ready():
    print('Logged in as', cosmodrone.user.name)
    print(cosmodrone.user.id)
    print('------')

# cosmodrone.now = types.MethodType( cosmodrone, clock )
# cosmodrone.loop.create_task(clock())
cosmodrone.run(TOKEN)
