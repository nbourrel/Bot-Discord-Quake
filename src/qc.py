import requests
import json

def get_player_info(player_name):
    output = ""
    url = f"https://quake-stats.bethesda.net/api/v2/Player/Stats?name={player_name}"

    try:
        response = requests.get(url)

        # Check if the response status code is not 200
        if response.status_code != 200:
            output += f"Error: Received a non-200 status code ({response.status_code}) from the server."
            return

        # Parse the JSON response
        player_data = response.json()

        # Check if the response data is empty or does not contain the expected structure
        if not player_data or "playerRatings" not in player_data:
            output += f"User does not exist."
            return

        # Extract the player's rating for the "duel" game mode
        duel_rating = player_data.get("playerRatings", {}).get("duel", {}).get("rating")
        
        # Check if the duel rating is not present in the response
        if duel_rating is None:
            output += f"Error: Duel rating not found in the response."
            return
        
        rank = sort_rank(duel_rating)
        
        output += f"Current rank : {rank} ({duel_rating})\n\n"
        
        
        most_played_champion = None
        max_champion_games = 0
        max_efficiency = 0

        # Iterate through every champion and print "won" and "lost" values in "GameModeDuel"
        for champion, stats in player_data.get("playerProfileStats", {}).get("champions", {}).items():
            game_mode_duel_stats = stats.get("gameModes", {}).get("GameModeDuel", {})
            champion_duel_won = game_mode_duel_stats.get("won", None)
            champion_duel_lost = game_mode_duel_stats.get("lost", None)

            if champion_duel_won is not None and champion_duel_lost is not None:
                champion_games = champion_duel_won + champion_duel_lost

                # Calculate efficiency (win percentage)
                efficiency = champion_duel_won / champion_games if champion_games > 0 else 0

                # print(f"{champion}: Duel Wins - {champion_duel_won}, Duel Losses - {champion_duel_lost}, Total Games - {champion_games}, Efficiency - {efficiency:.2%}")

                # Update most played champion based on total games played
                if champion_games > max_champion_games:
                    max_champion_games = champion_games
                    most_played_champion = champion

                # Update most efficient champion based on efficiency
                if efficiency > max_efficiency:
                    max_efficiency = efficiency
                    most_efficient_champion = champion

            else:
                output += f"Error: Duel stats for {champion} not found in the response."

        # Print most played and most efficient champion
        output += f"Main Champion : {most_played_champion.title()}\n"
        output += f"Most Efficient Champion : {most_efficient_champion.title()} ({max_efficiency:.2%})"

        # Read users.json
        with open('config/users.json', 'r') as users_file:
            users_data = json.load(users_file)

        # Check if there's a matching entry for player_name
        matching_entry = next((entry for entry in users_data.values() if 'qc_name' in entry and entry['qc_name'] is not None and entry['qc_name'].lower() == player_name.lower()), None)

        # Update qc_rank for the entry in users.json
        if matching_entry:
            matching_entry['qc_rank'] = rank

            # Write the updated data back to users.json
            with open('config/users.json', 'w') as users_file:
                json.dump(users_data, users_file, indent=4)

        return(output)
    except requests.exceptions.RequestException as e:
        output += f"Request error occurred: {e}"
        return(output)
        
        
        
        
        
        
        
        
        
def sort_rank(elo):
    rank_limits = {
        2100: "Elite",
        2025: "Diamond 5",
        1950: "Diamond 4",
        1875: "Diamond 3",
        1800: "Diamond 2",
        1725: "Diamond 1",
        1650: "Gold 5",
        1575: "Gold 4",
        1500: "Gold 3",
        1425: "Gold 2",
        1350: "Gold 1",
        1275: "Silver 5",
        1200: "Silver 4",
        1125: "Silver 3",
        1050: "Silver 2",
        975: "Silver 1",
        900: "Bronze 5",
        825: "Bronze 4",
        750: "Bronze 3",
        675: "Bronze 2",
        0: "Bronze 1"
    }
    
    # Find the relevant rank based on the player's rating
    relevant_limit = next((r for r in sorted(rank_limits.keys(), reverse=True) if elo >= r), 0)

    return rank_limits[relevant_limit]
    
def find_matching_qc_rank(target_qc_rank):
    # Read users.json
    with open('config/users.json', 'r') as users_file:
        users_data = json.load(users_file)

    # Remove numbers and spaces from target_qc_rank
    cleaned_target_qc_rank = ''.join(char for char in target_qc_rank if char.isalpha())

    # Find matching user IDs based on cleaned qc_rank
    matching_ids = [
        user_id for user_id, entry in users_data.items()
        if entry.get('qc_rank') and cleaned_target_qc_rank.lower() in ''.join(char for char in entry['qc_rank'] if char.isalpha()).lower()
        and entry.get('donotdisturb', 0) != 1  # Exclude users with "do not disturb" enabled
    ]

    return matching_ids

def get_qc_rank(qc_name):
    # Read users.json
    with open('config/users.json', 'r') as users_file:
        users_data = json.load(users_file)

    # Check if there's a matching entry for qc_name
    entry = next((entry for entry in users_data.values() if 'qc_name' in entry and entry['qc_name'] is not None and entry['qc_name'].lower() == qc_name.lower()), None)

    # If entry is None or qc_rank is None, return None
    if entry is None or 'qc_rank' not in entry or entry['qc_rank'] is None:
        return None

    return entry['qc_rank']
