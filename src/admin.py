import discord
from discord.ext import commands
from discord.ext.commands import Context
from src.ql import getQLelo, getQLcvars, updateQLcvars, updateQLcvarField, find_matching_elo, read_scores
from src.users import read_users, create_user, update_user, save_users

from src.config import load_config

BOT_TOKEN, CHANNEL_QL, CHANNEL_QC, CHANNEL_LFG, ADMINS, GUILD_ID, RANK_VALUES, QL_EU_ROLES, QL_NA_ROLES = load_config()

async def process_admin(bot, message):
    command = message.content[1:].split(' ', 1)[0].lower()
    # Check if the first word is 'cvar'
    if command == 'newcvar':
        query = message.content[len('$newcvar '):]
        output = updateQLcvars(query)
        await message.author.send(output)
    elif command == 'cfield':
        words = shlex.split(message.content[len('$cfield '):])
        output = updateQLcvarField(words[0], words[1], words[2])
        await message.author.send(output)
    elif command == 'offtopic':
        # Get the guild
        guild = bot.get_guild(GUILD_ID)
        # Check if the guild is found
        if guild:
            # Get the source channel name and destination channel name from user input
            args = message.content.split(' ')[1:]
            if len(args) == 2:
                source = args[0]
                destination_channel_name = args[1]
                # Get the source channel by name
                source_channel = discord.utils.get(guild.channels, name=source)
                # Get the destination channel by name
                destination_channel = discord.utils.get(guild.channels, name=destination_channel_name)
                # Check if both channels are found
                if source_channel and destination_channel:
                    # Send the message to the destination channel
                    await source_channel.send(f"I'm sure this conversation would be even more delightful in #{destination_channel_name} :D")
                    await message.author.send(f'Justice has been brought to #{source}. Burt can now sleep in peace ;)')
                else:
                    await message.author.send('One or both of the specified channels were not found.')
            else:
                await message.author.send('Invalid number of arguments. Please provide two channel names after the command.')
        else:
            await message.author.send('Guild not found.')
    elif command == 'steamid':
        user_id = str(message.author.id)
        args = message.content.split(' ')[1:]
        if args:
            steam_id = args[0]
            user_data = read_users()
            if user_id in user_data:
                user_data[user_id]['steam_id'] = steam_id
                save_users(user_data)
                await message.author.send(f'Alright buddy, your new Steam ID is : {steam_id} :o) ')
            else:
                create_user(user_id, steam_id=steam_id)
                await message.author.send(f'Hourray! You set your Steam ID : {steam_id}! Flex a bit with "!elo" ;)')
        else:
            await message.author.send("You're supposed to provide your Steam ID here.. Find it in you Quake Live directory or your qlstats.net page!\n Usage : !steamid <your-steamid>")
    elif command == "users.stats":
        guild = bot.get_guild(GUILD_ID)
        # Check if the guild is found
        if guild:
            # Get the total number of members in the guild
            total_members = guild.member_count
            # Read user data from the file
            user_data = read_users()
            # Count the number of registered users
            registered_users = len(user_data)
            # Calculate the percentage of registered users
            if total_members > 0:
                percentage = (registered_users / total_members) * 100
            else:
                percentage = 0
            # Send the percentage as a direct message
            await message.author.send(f"**Users stats for {guild.name} : **\n```Members : {total_members}\nRegistered users : {registered_users}\n\nPercentage of registered users: {percentage:.2f}%```")
        else:
            await message.author.send('Guild not found.')
    elif command == "who":
        # Split the message content after "$who " and keep only the first word
        args = message.content[len("$who "):].split(" ", 1)

        if not args or not args[0]:
            await message.author.send("Please provide a user to search for.")
            return

        search_term = args[0].lower()
        user_data = read_users()

        # Check if the search term matches any user ID, steam ID, Quake Champions name, or Quake Live Elo
        matching_users = [
            (user_id, data) for user_id, data in user_data.items() if
            search_term in [user_id, data.get('steam_id', ''), (data.get('qc_name', '') or '').lower(), str(data.get('ql_elo', ''))]
        ]

        if not matching_users:
            await message.author.send(f"No user found with the provided search term: {search_term}")
            return

        output = "Matching Users:\n```"
        for user_id, user_info in matching_users:
            output += f"User ID: {user_id}\n"
            output += f"Steam ID: {user_info.get('steam_id', 'N/A')}\n"
            output += f"Quake Champions Name: {user_info.get('qc_name', 'N/A')}\n"
            output += f"Quake Champions Rank: {user_info.get('qc_rank', 'N/A')}\n"
            output += f"Quake Live Elo: {user_info.get('ql_elo', 'N/A')}\n"
            output += f"Do Not Disturb: {user_info.get('donotdisturb', 'N/A')}\n\n```"
        await message.author.send(output)
    elif command == 'users.score':
        scores = read_scores()

        if not scores:
            await message.author.send("No game scores available.")
            return

        user_wins = {}

        for game in scores:
            winner_id = game.get("winner_id")
            if winner_id:
                winner_name = await get_username(bot, GUILD_ID, int(winner_id))
                user_wins[winner_name] = user_wins.get(winner_name, 0) + 1

        if user_wins:
            sorted_user_wins = sorted(user_wins.items(), key=lambda x: x[1], reverse=True)
            response_text = "Current game stats:\n```"
            for user, wins in sorted_user_wins:
                response_text += f"{user} : {wins} {'games' if wins > 1 else 'game'} won\n"
            response_text += "```"
            await message.author.send(response_text)
        else:
            await message.author.send("No winners recorded.")
    elif command == 'srating':
        splayers = [105719668081192960, 750336829072605336, 215762134376775680, 281906807591665665, 119568298852614146, 214398628209360898, 364440625396973568, 364072492995706880, 316156621032128513, 373948650470244364, 1177941953011273728, 510178076588507137]
        scores = read_scores()

        if not scores:
            await message.author.send("No game scores available.")
            return

        user_wins = {}

        for game in scores:
            winner_id = game.get("winner_id")
            if winner_id and int(winner_id) in splayers:
                winner_name = await get_username(bot, GUILD_ID, int(winner_id))
                user_wins[winner_name] = user_wins.get(winner_name, 0) + 1

        if user_wins:
            sorted_user_wins = sorted(user_wins.items(), key=lambda x: x[1], reverse=True)
            response_text = "Current game stats for selected players:\n"
            for user, wins in sorted_user_wins:
                response_text += f"{user} : {wins} {'games' if wins > 1 else 'game'} won\n"
            response_text += ""
            mentions = " ".join([f"<@{player_id}>" for player_id in splayers])
            # response_text = f"{mentions}\n{response_text}"
            await message.author.send(response_text)
        else:
            mentions = " ".join([f"<@{player_id}>" for player_id in splayers])
            await message.author.send(f"{mentions}\nNo winners recorded for the selected players.")
            
    elif command == 'help':
        help_text = (
            "Available Admin Commands:\n\n"
            "`$newcvar <query>` - Update a whole Quake Live cvar.\n"
            "`$cfield <query> <field> <new_value>` - Update specific field in Quake Live cvar.\n"
            "`$offtopic <source_channel> <destination_channel>` - Suggest moving an offtopic conversation to a different channel.\n"
            "`$steamid <your_steamid>` - Set or update your Steam ID.\n"
            "`$users.stats` - Show stats for the server's members and registered users.\n"
            "`$who <search_term>` - Search for users by ID, Steam ID, Quake Champions name, or Quake Live Elo.\n"
        )
        await message.author.send(help_text)                    
    else:
        await message.author.send(f'Unknown command: {command}')
        


async def get_username(bot, guild_id, user_id):
    guild = bot.get_guild(guild_id)
    member = guild.get_member(user_id)
    return member.display_name if member else f"<@{user_id}>"
