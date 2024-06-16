import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from src.ql import getQLelo, getQLcvars, updateQLcvars, updateQLcvarField, find_matching_elo, read_scores, save_scores
from src.users import read_users, create_user, update_user, save_users, is_registered, valid_steam_id
import shlex
import json
from colorama import init
from src.qc import get_player_info, get_qc_rank, find_matching_qc_rank, sort_rank
from src.admin import process_admin
from utils.qonsole import qonsoleprint
from src.config import load_config
import random


init()  # Colorama

BOT_TOKEN, CHANNEL_QL, CHANNEL_QC, CHANNEL_LFG, ADMINS, GUILD_ID, RANK_VALUES, QL_EU_ROLES, QL_NA_ROLES = load_config()
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.reactions = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

#bo3 logic variables
MAP_POOL = ["Bloodrun", "Aerowalk", "Furious Heights", "Cure", "Lost World", "Campgrounds", "Sinister"]
bo_mappool = list(MAP_POOL)
actualPool = []
pickingPlayer = None
pickingAction = 1  # Starting with fpicker banning the first map
pickingState = 0  # 0 means bot is free
fpicker = None
spicker = None
output = ""
EMOJI_MAP = {
    1: '\U00000031\U000020e3',  # Reaction for 1
    2: '\U00000032\U000020e3',  # Reaction for 2
    3: '\U00000033\U000020e3',  # Reaction for 3
    4: '\U00000034\U000020e3',  # Reaction for 4
    5: '\U00000035\U000020e3',  # Reaction for 5
    6: '\U00000036\U000020e3',  # Reaction for 6
    7: '\U00000037\U000020e3'   # Reaction for 7
}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')


@bot.event
async def on_message(message):
    await qonsoleprint(message)
    if isinstance(message.channel, discord.DMChannel):
        for attachment in message.attachments:
            if any(attachment.filename.lower().endswith(image_type) for image_type in ['png', 'jpg', 'jpeg', 'gif', 'dm_91']):
                a = message.content
                message.content += attachment.url
                await qonsoleprint(message)
                message.content =a
        if message.author.id in ADMINS:
            if message.content.startswith('$'):
                await process_admin(bot, message)
        # else:
            # await message.author.send("Hello there! :o)\nI'm still a bit too shy to talk to strangers..")
    await bot.process_commands(message)


@bot.command(name='elo', brief="Usage : !elo / !elo [@user] / !elo [steamid]")
async def elo(ctx, *args):
    """
    Retrieves your elo from qlstats.net, or the elo for the provided steam id. Retrieving it without the steam id or by mentionning only works if relevant profile has been set by !steamid."
    Works in #quake-live and #looking-for-game.
    """
    if args:
        # Check if the argument is a mention
        if ctx.message.mentions:
            # Retrieve elo for mentioned users
            for mentioned_user in ctx.message.mentions:
                user_id = str(mentioned_user.id)
                user_data = read_users()
                if user_id in user_data and 'steam_id' in user_data[user_id]:
                    steam_id = user_data[user_id]['steam_id']
                    ql_elo = getQLelo(steam_id)
                    await ctx.send(f'Current QL elo for {mentioned_user.display_name}: {ql_elo}')
                else:
                    await ctx.send(f"I don't know {mentioned_user.display_name} yet :(\nMake sure they have set their Steam ID using !steamid.")
        else:
            # Case: The user provided their own steam ID
            target = args[0]
            # Check if the target is a string containing only numbers
            if target.isdigit():
                steam_id = int(target)
                ql_elo = getQLelo(steam_id)
                update_user(str(ctx.author.id), "ql_elo", ql_elo)
                await ctx.send(f'Current QL elo for {steam_id} : {ql_elo}')
            else:
                await ctx.send("Invalid steam ID. Please provide a valid steam ID consisting of numeric characters.")
    else:
        # Case: The user didn't provide any argument, find their own elo
        user_id = str(ctx.author.id)
        # Read user data from the file
        user_data = read_users()
        # Check if the user exists in the data
        if user_id in user_data:
            user_info = user_data[user_id]
            # Check if the user has a Steam ID set
            if 'steam_id' in user_info and user_info['steam_id']:
                # Retrieve QL ELO using the stored Steam ID
                ql_elo = getQLelo(user_info['steam_id'])
                update_user(user_id, "ql_elo", ql_elo)
                if ql_elo is not None:
                    await ctx.send(f"{ctx.author.display_name} wants to flex! Current elo : {ql_elo}")
                else:
                    await ctx.send('Failed to retrieve your elo. Please try again later :o)')
            else:
                await ctx.send("You have to provide your Steam ID before. Find it in you Quake Live directory or your qlstats.net page!\n Usage : !steamid <your-steamid>")
        else:
            await ctx.send("You have to provide your Steam ID before. Find it in you Quake Live directory or your qlstats.net page!\n Usage : !steamid <your-steamid>")


@bot.command(name='lfg.ql', brief="Usage : !lfg.ql / !lfg.ql [elo value]")
async def lfg(ctx, *args):
    """
    Mentions people with matching elo (+/- 100) in #looking-for-game. It retrieves only registered profiles, and you can use it without value only if you're registered.
    Works in #quake-live and #looking-for-game.
    """
    user_roles = [role.id for role in ctx.author.roles]
    has_ql_eu_role = any(role_id in QL_EU_ROLES for role_id in user_roles)
    has_ql_na_role = any(role_id in QL_NA_ROLES for role_id in user_roles)
    if not (has_ql_eu_role or has_ql_na_role):
        await ctx.send("You need to have either a QL-EU or QL-NA role to use this command.")
        return
    if args:
        if len(args) == 1 and args[0].isdigit():
            # Case: The user provided a specific elo value
            target_elo = int(args[0])
            if 0 < target_elo < 2500:
                matching_ids = find_matching_elo(target_elo)
                print(f'Matching IDs before filtering: {matching_ids}')  # Debug: Before filtering
                # Exclude the message author's ID from the list
                matching_ids = [user_id for user_id in matching_ids if user_id != str(ctx.author.id)]
                matching_ids = await filter_matching_ids_by_role(ctx, matching_ids, has_ql_eu_role, has_ql_na_role)
                if matching_ids:
                    output = ', '.join([f'<@{user_id}>' for user_id in matching_ids])
                    await ctx.send(f'Summoning players around {target_elo}elo :\n{output}')
                else:
                    await ctx.send("I couldn't find anyone around your level :(")
            else:
                await ctx.send("Yeah, right.. Might as well call this one then: https://www.twitch.tv/rapha")
        else:
            await ctx.send("You're supposed to provide a valid elo value here. If you don't, I'll use yours!\n Usage : !elo or !elo 1000")
    else:
        # Case: The user didn't provide any argument, find players around their own elo
        user_id = str(ctx.author.id)
        # Read user data from the file
        user_data = read_users()
        # Check if the user exists in the data
        if user_id in user_data:
            user_info = user_data[user_id]
            # Check if the user has a Steam ID set
            if 'steam_id' in user_info and user_info['steam_id']:
                # Retrieve QL ELO using the stored Steam ID
                ql_elo = getQLelo(user_info['steam_id'])
                update_user(user_id, "ql_elo", ql_elo)
                if ql_elo is not None:
                    matching_ids = find_matching_elo(ql_elo)
                    # Exclude the message author's ID from the list
                    matching_ids = [user_id for user_id in matching_ids if user_id != str(ctx.author.id)]
                    matching_ids = await filter_matching_ids_by_role(ctx, matching_ids, has_ql_eu_role, has_ql_na_role)
                    if matching_ids:
                        output = ', '.join([f'<@{user_id}>' for user_id in matching_ids])
                        await ctx.send(f"Summoning players around {ql_elo}elo : \n{output}")
                    else:
                        await ctx.send("I couldn't find anyone around your level :(")
                else:
                    await ctx.send('Failed to retrieve your elo. Please try again later :o)')
        else:
            await ctx.send("I don't know you yet :(. Please ensure you have set your Steam ID using !steamid.")


@bot.command(name='steamid', brief="Usage : !steamid / !steamid [new steam id]")
async def steamid(ctx, *args):
    """
    Register/update your steam id. The more people do, the more useful the bot can get in the future.
    You can find this value on your steam profile, in your Quake Live directory (the "many numers files" is named after this ID) or on qlstats.net.
    Using it without providing id will give back your own if it's already registered - to give it to a pal to be added as friend, for instance.
    Works in #quake-live, #quake-champions and #looking-for-game.
    """
    user_id = str(ctx.author.id)
    if args:
        if args[0].isdigit():
            steam_id = args[0]
            user_data = read_users()
            if user_id in user_data:
                user_data[user_id]['steam_id'] = steam_id
                save_users(user_data)
                await ctx.send(f'Alright buddy, your new Steam ID is : {steam_id} :o) ')
            else:
                create_user(user_id, steam_id=steam_id)
                await ctx.send(f"Hourray! {ctx.author.display_name}'s Steam ID is {steam_id}! Flex a bit with '!elo' ;)")
        else:
            await ctx.send("This is not a valid steam id! Find it in you Quake Live directory or your qlstats.net page!")
    else:
        user_id = str(ctx.author.id)
        # Read user data from the file
        user_data = read_users()
        # Check if the user exists in the data
        if user_id in user_data:
            user_info = user_data[user_id]
            # Check if the user has a Steam ID set
            if 'steam_id' in user_info and user_info['steam_id']:
                steam_id = user_data[user_id]['steam_id']
                await ctx.send(f"Hmmm... \"{ctx.author.display_name}\"? I know you! Your Steam ID is {steam_id}")
            else:
                await ctx.send("You're supposed to provide your Steam ID here.. Find it in you Quake Live directory or your qlstats.net page!\n Usage : !steamid <your-steamid>")
        else:
            await ctx.send("You're supposed to provide your Steam ID here.. Find it in you Quake Live directory or your qlstats.net page!\n Usage : !steamid <your-steamid>")


@bot.command(name='cvar', brief="Usage : !cvar [variable] / !cvar [keyword]")
async def cvar(ctx, *args):
    """
    Look up a Quake Live console variable in our documentation, browsing by exact name or keywords.
    Works in #quake-live.
    
    This documentation lacks corrections, many values got their fields mixed up and we need to sort it out. Any help is appreciated :)
    """
    query = args[0]
    output = getQLcvars(query)
    if len(output) > 2000:
        output = "**Sorry i can't send a message that long, please pick more precise keywords.**"
    await ctx.send(output)


@bot.command(name='insta', brief="Gets the link of tumer's clips channel")
async def insta(ctx):
    await ctx.send("```https://www.instagram.com/qfn.tumer/ \nDrop your clips.dm_68 in hub3aero's DMs ;)```")


@bot.command(name='rank', brief="Usage : !rank / !rank [@user] / !rank [ingame name]")
async def rank(ctx, *args):
    """
    Retrieves your rank from quake-stats.bethesda.net/, or the rank for the provided name.
    Retrieving it without the name or by mentionning only works if relevant profile as been set by !ign.
    Works in #quake-champions and #looking-for-game.
    """
    if ctx.message.mentions:
        for mentioned_user in ctx.message.mentions:
            player_id = str(mentioned_user.id)
            user_data = read_users()
            # Check if the user exists in the data
            if player_id in user_data:
                qc_name = user_data[player_id].get('qc_name')
                qc_rank = user_data[player_id].get('qc_rank')
                if qc_name and qc_rank:
                    player_info = get_player_info(qc_name)
                    if player_info:
                        await ctx.send(f"**Current rank infos for {qc_name} :**\n```{player_info}```")
                    else:
                        await ctx.send(f"Couldn't retrieve stats for {qc_name}.")
                else:
                    if qc_name is None:
                        await ctx.send(f"{mentioned_user.display_name} hasn't registered a Quake Champions name. Use !ign <your_name> to register.")
                    elif qc_rank is None:
                        new_rank = get_player_info(qc_name)
                        await ctx.send(new_rank)
            else:
                await ctx.send(f"Couldn't find data for {mentioned_user.display_name}. Ask them to register using !ign <their_name>.")
    elif args:
        # Case: Arguments provided

        player_name = ' '.join(args)
        player_info = get_player_info(player_name)
        if player_info:
            await ctx.send(f"**Current rank infos for {player_name} :**\n```{player_info}```")
        else:
            await ctx.send(f"Couldn't retrieve stats for {player_name}.")
    else:
        # Case: No mentions or args
        user_id = str(ctx.author.id)
        user_data = read_users()
        if user_id in user_data and 'qc_name' in user_data[user_id]:
            qc_name = user_data[user_id]['qc_name']
            qc_rank = user_data[user_id]['qc_rank']
            if qc_name is not None and qc_rank is not None:
                player_info = get_player_info(qc_name)
                if player_info:
                    await ctx.send(f"**{ctx.author.display_name} wants to flex!**\n```{player_info}```")
                else:
                    await ctx.send(f"Couldn't retrieve stats for {qc_name}.")
            else:
                if qc_name is None:
                    await ctx.send("Your Quake Champions name is not set. Use !ign <your_name> to register.")
                elif qc_rank is None:
                    newrank = get_player_info(qc_name)
                    await ctx.send(f"**{ctx.author.display_name} wants to flex!**\n```{newrank}```")
        else:
            await ctx.send("You haven't registered a Quake Champions name. Use !ign <your_name> to register.")


@bot.command(name='ign', brief="Usage : !ign / !ign [new ingame name]")
async def ign(ctx, *args):
    """
    Register/update your ingame name, the more people do, the more useful the bot can get in the future.
    Using it without providing name will give back your own if it's already registered - to give it to a pal to be added as friend, for instance.
    Works in #quake-champions and #looking-for-game.   
    """
    # Check if any arguments are provided
    if args:
        # Check if the argument is a mention
        if ctx.message.mentions:
            # Retrieve the first mentioned user
            mentioned_user = ctx.message.mentions[0]
            user_id = str(mentioned_user.id)
        else:
            # Use the author's ID if no mentions
            user_id = str(ctx.author.id)
        # Read user data from the file
        with open('config/users.json', 'r') as json_file:
            users_data = json.load(json_file)
        # Check if the user exists in the data
        if user_id in users_data:
            user_info = users_data[user_id]
            # Update qc_name if arguments are provided
            if args:
                user_info['qc_name'] = ' '.join(args)
                qc_name = ' '.join(args)
                # Update the file with the modified data
                with open('config/users.json', 'w') as json_file:
                    json.dump(users_data, json_file, indent=4)
                await ctx.send(f"Alright buddy, your new Quake Champions name is : {qc_name} :o) ")
            else:
                # Return qc_name if it exists, otherwise tell to register
                qc_name = user_info.get('qc_name')
                if qc_name:
                    await ctx.send(f"Hmmm... \"{ctx.author.display_name}\"? I know you! Your Quake Champions name is {qc_name}")
                else:
                    await ctx.send("You haven't registered a Quake Champions name. Use `!ign <your_name>` to register.")
        else:
            create_user(user_id, qc_name=args[0])

            await ctx.send(f"Your Quake Champions name has been set to: {args[0]}")
    else:
        # Case: No arguments provided
        user_id = str(ctx.author.id)
        with open('config/users.json', 'r') as json_file:
            users_data = json.load(json_file)
        # Check if the user exists in the data
        if user_id in users_data:
            qc_name = users_data[user_id].get('qc_name')
            if qc_name:
                await ctx.send(f"Your registered Quake Champions name is: {qc_name}")
            else:
                await ctx.send("You haven't registered a Quake Champions name. Use `!ign <your_name>` to register.")
        else:
            await ctx.send("You haven't registered a Quake Champions name. Use `!ign <your_name>` to register.")


@bot.command(name='lfg.qc', brief="Usage : !lfg.qc / !lfg.qc [rank]")
async def lfg_qc(ctx, *args):
    """
    Mentions people with matching rank in #looking-for-game. It retrieves only registered profiles, and you can use it without value only if you're registered.
    Works in #looking-for-game.
    """
    if args:
        if len(args) == 1 and isinstance(args[0], str):
            # Case: The user provided a specific QC rank value
            target_qc_rank = args[0].capitalize()
            matching_ids = find_matching_qc_rank(target_qc_rank)
            # Exclude the message author's ID from the list
            matching_ids = [user_id for user_id in matching_ids if user_id != str(ctx.author.id)]
            if matching_ids:
                output = ', '.join([f'<@{user_id}>' for user_id in matching_ids])
                await ctx.send(f'Summoning players around {target_qc_rank} rank :\n{output}')
            else:
                await ctx.send(f"I couldn't find anyone around {target_qc_rank} rank :(")
        else:
            await ctx.send("You're supposed to provide a valid Quake Champions rank value here.\n Usage: !lfg.qc or !lfg.qc Silver 1")
    else:
        # Case: The user didn't provide any argument, find players around their own rank
        user_id = str(ctx.author.id)
        # Read user data from the file
        user_data = read_users()
        # Check if the user exists in the data
        if user_id in user_data:
            user_info = user_data[user_id]
            # Check if the user has a QC name set
            if 'qc_name' in user_info and user_info['qc_name']:
                qc_name = user_info['qc_name']
                # Retrieve QC rank using the stored QC name
                qc_rank = get_qc_rank(qc_name)
                update_user(user_id, "qc_rank", qc_rank)
                if qc_rank is not None:
                    matching_ids = find_matching_qc_rank(qc_rank)
                    # Exclude the message author's ID from the list
                    matching_ids = [user_id for user_id in matching_ids if user_id != str(ctx.author.id)]
                    if matching_ids:
                        output = ', '.join([f'<@{user_id}>' for user_id in matching_ids])
                        await ctx.send(f"Summoning players around {qc_rank} rank :\n{output}")
                    else:
                        await ctx.send(f"I couldn't find anyone around {qc_rank} rank :(")
                else:
                    await ctx.send('Failed to retrieve your rank. Please try again later :o)')
            else:
                await ctx.send('You need to set your Quake Champions name first using !ign.')
        else:
            await ctx.send("I don't know you yet :(. Please ensure you have set your Quake Champions name using !ign.")
            
            
@bot.command(name='pingsoff', brief="Disable bot's mentions.")
async def pingsoff(ctx):
    # Set "do not disturb" for the author to 1
    user_id = str(ctx.author.id)
    update_user(user_id, 'donotdisturb', 1)
    await ctx.send("Ok, i won't mention you until you ask for it with '!pingson'.")


@bot.command(name='pingson', brief="Enable bot mentions (default).")
async def pingson(ctx):
    # Set "do not disturb" for the author to None
    user_id = str(ctx.author.id)
    update_user(user_id, 'donotdisturb', None)
    await ctx.send("I'm glad you're back! You'll get mentions now :)")


@bot.command(name='top5.ql', brief="Show top 5 players in QL elo.")
async def top5_ql(ctx):
    user_data = read_users()
    top_5_ql = sorted(user_data.items(), key=lambda x: x[1].get('ql_elo', 0) or 0, reverse=True)[:5]
    
    output = "Top 5 Quake Live ELO:\n```"
    for i, (user_id, data) in enumerate(top_5_ql, start=1):
        user = await bot.fetch_user(int(user_id))
        if data.get('ql_elo', 0):
            output += f"{i}. {user.display_name} - {data.get('ql_elo', 0)}\n"
    await ctx.send(f"{output}```")
    
    
@bot.command(name='top10.ql', brief="Show top 10 players in QL elo.")
async def top10_ql(ctx):
    user_data = read_users()
    top_10_ql = sorted(user_data.items(), key=lambda x: x[1].get('ql_elo', 0) or 0, reverse=True)[:10]
    
    output = "Top 10 Quake Live ELO:\n```"
    for i, (user_id, data) in enumerate(top_10_ql, start=1):
        user = await bot.fetch_user(int(user_id))
        if data.get('ql_elo', 0):
            output += f"{i}. {user.display_name} - {data.get('ql_elo', 0)}\n"
    
    await ctx.send(f"{output}```")

@bot.command(name='top10.cap', brief="Show top 10 players in QL elo below the 1100 elo cap.")
async def top10_cap(ctx):
    user_data = read_users()
    top_10_ql = sorted((item for item in user_data.items() if item[1].get('ql_elo') is not None and item[1].get('ql_elo', 0) < 1100), key=lambda x: x[1].get('ql_elo', 0) or 0, reverse=True)[:10]
    
    output = "Top 10 Quake Live ELO:\n```"
    for i, (user_id, data) in enumerate(top_10_ql, start=1):
        user = await bot.fetch_user(int(user_id))
        if data.get('ql_elo', 0):
            output += f"{i}. {user.display_name} - {data.get('ql_elo', 0)}\n"
    
    await ctx.send(f"{output}```")

@bot.command(name='top5.qc', brief="Show top 5 players in QC rank.")
async def top5_qc(ctx):
    user_data = read_users()
    
    # Mapping of rank strings to numeric values
    rank_values = RANK_VALUES
    
    top_5_qc = sorted(user_data.items(), key=lambda x: rank_values.get(x[1].get('qc_rank', 'Bronze 1'), 0), reverse=True)[:5]
    
    output = "```Top 5 Quake Champions Rank:\n"
    for i, (user_id, data) in enumerate(top_5_qc, start=1):
        user = await bot.fetch_user(int(user_id))
        if data.get('qc_name', 'Unknown') and data.get('qc_rank', 'Unknown'):
            output += f"{i}. {data.get('qc_name', 'Unknown')} ({user.display_name}) - {data.get('qc_rank', 'Unknown')}\n"
    
    await ctx.send(f"{output}```")


@bot.command(name='top10.qc', brief="Show top 10 players in QC rank.")
async def top10_qc(ctx):
    user_data = read_users()
    
    # Mapping of rank strings to numeric values
    rank_values = RANK_VALUES
    
    top_10_qc = sorted(user_data.items(), key=lambda x: rank_values.get(x[1].get('qc_rank', 'Bronze 1'), 0), reverse=True)[:10]
    
    output = "```Top 10 Quake Champions Rank:\n"
    for i, (user_id, data) in enumerate(top_10_qc, start=1):
        user = await bot.fetch_user(int(user_id))
        if data.get('qc_name', 'Unknown') and data.get('qc_rank', 'Unknown'):
            output += f"{i}. {data.get('qc_name', 'Unknown')} ({user.display_name}) - {data.get('qc_rank', 'Unknown')}\n"
    
    await ctx.send(f"{output}```")


@bot.command(name='scores', brief="Usage (in bot's dm) !scores #gameID <your score> <opponent score>")
async def score(ctx, game_id, score1, score2):
    """
    Report your score for a #gameID. Those ids are provided by the bot when you use the !bo3 command for sets.
    Works in DMs only.
    """
    # Get the author's user ID
    author_id = ctx.author.id
    scores = read_scores()
    # Clean the game_id to keep only numbers
    game_id = ''.join(filter(str.isdigit, game_id))

    # Check if the game_id is within the valid range
    if game_id.isdigit() and 1 <= int(game_id) <= len(scores):
        # Get the corresponding game entry
        game_entry = scores[int(game_id) - 1]

        # Check if the author is one of the players
        if author_id == int(game_entry['player1_id']):
            # Update scores for player 1
            if score1.replace("-", "").isdigit() and score2.replace("-", "").isdigit():
                game_entry['score1'] = int(score1)
                game_entry['score2'] = int(score2)

                # Determine the winner based on scores
                game_entry['winner_id'] = author_id if int(score1) > int(score2) else int(game_entry['player2_id'])
            else:
                await ctx.send("Invalid score format. Please provide valid integer scores.")
                return
        elif author_id == int(game_entry['player2_id']):
            # Update scores for player 2
            if score1.replace("-", "").isdigit() and score2.replace("-", "").isdigit():
                game_entry['score1'] = int(score2)
                game_entry['score2'] = int(score1)

                # Determine the winner based on scores
                game_entry['winner_id'] = author_id if int(score2) > int(score1) else int(game_entry['player1_id'])
            else:
                await ctx.send("Invalid score format. Please provide valid integer scores.")
                return
        else:
            await ctx.send("You are not a player in this game.")
            return

        # Save the updated scores to the JSON file
        save_scores(scores)

        await ctx.send(f"Scores for Game #{game_id} have been updated.")
    else:
        await ctx.send("Invalid game_id. Please provide a valid game_id.")
        
        
@bot.command(name='bo3', brief="Usage : !bo3 @user")
async def start_bo3(ctx, opponent: discord.User):
    """
    Starts a map picking process for a best-of-three quake live game. You and @user have to be registered.
    You can then report your score, winners will be stored and.. maybe  magic happens at some point.
    Works in #looking-for-game.
    """
    global bo_mappool, pickingPlayer, pickingState, actualPool, fpicker, spicker, output
    pickingPlayer = ctx.author.id
    if ctx.message.mentions:
        enemy_id = opponent.id
        player_id = ctx.author.id
        if enemy_id != player_id and is_registered(player_id) and is_registered(enemy_id) and valid_steam_id(player_id) and valid_steam_id(enemy_id):
            if pickingState == 0:
               pickingState = 1
               scores = read_scores()
               # Initialize the scores list if it's empty
               if not scores:
                   scores = []
                   # Send the initial map pool message
               map_pool_text = " | ".join([f"{i + 1}. {map_name}" for i, map_name in enumerate(bo_mappool)])
               output = ""
               for game_id in range(len(scores) + 1, len(scores) + 4):
                   scores.append({
                       "game_id": game_id,
                       "player1_id": str(player_id),
                       "score1": None,
                       "player2_id": str(enemy_id),
                       "score2": None,
                       "winner_id": None
                   })
                   output += f"#{game_id} "
               save_scores(scores)
               print(output)
               if cointoss():
                   fpicker, spicker = ctx.author, opponent
                   print("chance")
               else:
                   spicker, fpicker = ctx.author, opponent
               initial_message = f"{fpicker.display_name} vs. {spicker.display_name}:\n```Available maps: {map_pool_text}\n{fpicker.display_name}'s turn to ban\nReact with the corresponding emoji to ban a map!```"
               message = await ctx.send(initial_message)
               for i in range(1, 8):
                   await message.add_reaction(EMOJI_MAP[i])
            else:
                await ctx.send("Bot is currently in use, please retry in a minute.")
        else:
            await ctx.send("Both players must be registered with valid Steam IDs!")
    else:
        await ctx.send("You have to @mention a registered user!")                    


@bot.command(name='ip', brief="Usage : !ip 123.456.789:27960 (proper ipv4, no domain name)")
async def ip(ctx, args):
    """
    Turns an ip into a clickable steam link.
    """
    await ctx.send(f"https://connectsteam.me/?{args}")

@bot.command(name='qfn.cfg', brief="Gets the link of our 'basics cvars' config file.")
async def insta(ctx):
    await ctx.send("https://github.com/quake-for-newbies/qfnresources/blob/main/qfn.cfg \nFeel free to contribute if you have ideas to add :)")

@bot.command(name='srating', brief="Show current game stats for selected players.")
async def srating(ctx):
    splayers = [105719668081192960, 750336829072605336, 215762134376775680, 281906807591665665, 119568298852614146, 214398628209360898, 364440625396973568, 364072492995706880, 316156621032128513, 373948650470244364, 1177941953011273728, 510178076588507137]
    scores = read_scores()

    if not scores:
        await ctx.send("No game scores available.")
        return

    user_wins = {}

    for game in scores:
        winner_id = game.get("winner_id")
        if winner_id and int(winner_id) in splayers:
            winner = await bot.fetch_user(winner_id)
            winner_name = winner.display_name
            user_wins[winner_name] = user_wins.get(winner_name, 0) + 1

    if user_wins:
        sorted_user_wins = sorted(user_wins.items(), key=lambda x: x[1], reverse=True)
        response_text = "Current game stats for selected players:\n\n"
        
        # Podium formatting for first, second, and third places
        for i, (user, wins) in enumerate(sorted_user_wins[:3], start=1):
            response_text += f"{' ' * (3 - len(str(i)))}#{i}: {user} : {wins} {'games' if wins > 1 else 'game'} won\n"
        
        # Other players
        for i, (user, wins) in enumerate(sorted_user_wins[3:], start=4):
            response_text += f"{user} : {wins} {'games' if wins > 1 else 'game'} won\n"
        
        response_text = f"```\n{response_text}\n```"
        await ctx.send(response_text)
    else:
        await ctx.send("No winners recorded for the selected players.")

@bot.event
async def on_reaction_add(reaction, user):
    global bo_mappool, pickingPlayer, pickingState, actualPool, fpicker, spicker
    if user.bot:
        return
    # Do the right action based on the pickingState
    if pickingState == 1 and user.id == fpicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 8)]:
            removed_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} banned map: {removed_map}")
            pickingState += 1
            await update_map_pool_message(reaction.message.id)
 
    elif pickingState == 2 and user.id == spicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 7)]:
            removed_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} banned map: {removed_map}")
            pickingState += 1 
            await update_map_pool_message(reaction.message.id)
 
    elif pickingState == 3 and user.id == fpicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 6)]:
            picked_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} picked map: {picked_map}")
            actualPool.append(picked_map)  # Add the picked map to actualPool
            pickingPlayer = spicker.id  # Switch to the second picker
            pickingState += 1
            await update_map_pool_message(reaction.message.id)
 
    elif pickingState == 4 and user.id == spicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 5)]:
            picked_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} picked map: {picked_map}")
            actualPool.append(picked_map)  # Add the picked map to actualPool
            pickingState += 1       
            await update_map_pool_message(reaction.message.id)
 
    elif pickingState == 5 and user.id == fpicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 4)]:
            removed_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} banned map: {removed_map}")
            pickingState += 1
            await update_map_pool_message(reaction.message.id)
 
    elif pickingState == 6 and user.id == spicker.id:
        if str(reaction.emoji) in [EMOJI_MAP[i] for i in range(1, 3)]:
            removed_map = bo_mappool.pop(get_map_index_from_reaction(reaction))
            print(f"Player {user.display_name} banned map: {removed_map}")
 
            # Add remaining map to actualPool
            actualPool.append(bo_mappool[0])
 
            # Reset pickingState to 0 to free the bot
            pickingState = 0
 
            # Check if actualPool has 3 items
            if len(actualPool) == 3:
                # Edit the map pool message to show "Match ready! ActualPool - Game IDs"
                await update_map_pool_message(reaction.message.id, match_ready=True)
            bo_mappool = list(MAP_POOL)
            actualPool = []


async def update_map_pool_message(message_id, match_ready=False):
    global bo_mappool, actualPool, pickingPlayer, pickingState, fpicker, spicker
    channel = bot.get_channel(832997284089167892)  # Replace with the actual channel ID
    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        print(f"Message with ID {message_id} not found.")
        return
    if match_ready:
        actual_pool_text = " | ".join([f"{i + 1}. {map_name}" for i, map_name in enumerate(actualPool)])
        final_message = f"{fpicker.display_name} vs. {spicker.display_name}:\n```Maps to play: {actual_pool_text}, best of three.\nGames ids: {output}.\nhfgl :)```"
        await message.edit(content=final_message)
    else:
        map_pool_text = " | ".join([f"{i + 1}. {map_name}" for i, map_name in enumerate(bo_mappool)])
        step_actions = {
            1: {"picker": fpicker, "action": "ban"},
            2: {"picker": spicker, "action": "ban"},
            3: {"picker": fpicker, "action": "pick"},
            4: {"picker": spicker, "action": "pick"},
            5: {"picker": fpicker, "action": "ban"},
            6: {"picker": spicker, "action": "ban"},
        }
        current_step_info = step_actions[pickingState]
        picking_info = f"\n{current_step_info['picker'].display_name}'s turn to {current_step_info['action']}\nReact with the corresponding emoji to {current_step_info['action']} a map!```"
        interim_message = f"{fpicker.display_name} vs. {spicker.display_name}:\n```Available maps: {map_pool_text}{picking_info}\n"
        print(f"Updated Map Pool: {map_pool_text} {picking_info}")
        await message.edit(content=interim_message)
    

def get_map_index_from_reaction(reaction):
    for number, emoji in EMOJI_MAP.items():
        if str(reaction.emoji) == emoji:
            return number - 1  # Subtract 1 to convert to 0-based index
    return None  # Return None if the emoji is not found

            
def cointoss():
    # Use random.choice to randomly select 0 or 1
    return random.choice([0, 1])
    

async def filter_matching_ids_by_role(ctx, matching_ids, has_ql_eu_role, has_ql_na_role):
    filtered_ids = []
    excluded_users = []
    
    for user_id in matching_ids:
        member = ctx.guild.get_member(int(user_id))
        
        if member is None:  # Try fetching the member from the API if not found in the cache
            try:
                member = await ctx.guild.fetch_member(int(user_id))
            except discord.NotFound:
                # print(f'User ID {user_id} not found in the guild even after API fetch.')
                continue
            except discord.Forbidden:
                # print(f'Missing permissions to fetch user ID {user_id} from the API.')
                continue
        
        member_roles = [role.id for role in member.roles]
        
        if has_ql_eu_role:
            if any(role_id in QL_EU_ROLES for role_id in member_roles):
                filtered_ids.append(user_id)
                continue  # Skip to next user after match
        
        if has_ql_na_role:
            if any(role_id in QL_NA_ROLES for role_id in member_roles):
                filtered_ids.append(user_id)
                continue  # Skip to next user after match
        
        excluded_users.append(member.name)
    
    return filtered_ids
bot.run(BOT_TOKEN)