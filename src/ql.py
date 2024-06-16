import shlex
import requests
import json
from src.users import read_users, create_user, update_user, save_users

# Replace these with the actual values
balance_api_url = "qlstats.net"
balance_api_endpoint = "elo"
json_file_path = "config/cvars.json"
SCORES_FILE = 'config/scores.json'

def getQLelo(steam_id):

    # Build the URL for the request
    url = f"http://{balance_api_url}/{balance_api_endpoint}/{steam_id}"

    # Make the request
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        response_data = response.json()

        # Extract and print Elo and games played for each game mode
        for player_data in response_data["players"]:
            steam_id = player_data["steamid"]
            
            # print(f"Player Name: {steam_id}")
            for game_mode, info in player_data.items():
                if game_mode != "steamid":
                    elo = info.get("elo", "N/A")
                    games = info.get("games", "N/A")
                    print(f"{game_mode.upper()} Elo: {elo}, Games Played: {games}")
                    duel_elo = player_data.get("duel", {}).get("elo", "N/A")
                    
        return duel_elo
    else:
        print(f"Request failed with status code: {response.status_code}")
        print(response.text)  # Print the response text for debugging


def find_matching_elo(target_elo):
    matching_ids = []

    # Read user data from the file
    user_data = read_users()

    for discord_id, user_info in user_data.items():
        user_elo = user_info.get('ql_elo')
        donotdisturb = user_info.get('donotdisturb', 0)  # Default to 0 if 'donotdisturb' is not present

        # Check if user has "do not disturb" enabled
        if donotdisturb == 1:
            continue

        if user_elo is not None and -100 <= (user_elo - target_elo) <= 100:
            matching_ids.append(discord_id)

    return matching_ids

def getQLcvars(user_input):
    matching_entries = []
    matching_rows = []

    # Read the JSON file and search for the input
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)

        # Check if the user input matches any value in the 'Entry' or other columns
        for entry in data:
            if entry['Entry'] == user_input:
                matching_entries.append(entry)
            elif any(isinstance(value, str) and user_input.lower() in value.lower() for value in entry.values()):
                matching_rows.append(entry)

    output = ""

    if matching_entries:
        # If a match in 'Entry' key is found, add the whole entry nicely formatted to output
        for entry in matching_entries:
            output += f"```Cvar : {entry['Entry']}\n"
            output += f"Flags : {entry['Flags']}\n"
            output += f"Usage : {entry['Usage']}\n"
            output += f"Default Value : {entry['Default Value']}\n"
            output += f"Description : {entry['Description']}\n"
            output += f"Keywords : {entry['Keywords']}\n\n```"

    elif matching_rows:
        # Add other relevant cvars (entries with the input in their values) to output
        output += "**Relevant cvars :\n\n**"
        for entry in matching_rows:
            output += f"```Cvar : {entry['Entry']}\n"
            output += f"Flags : {entry['Flags']}\n"
            output += f"Usage : {entry['Usage']}\n"
            output += f"Default Value : {entry['Default Value']}\n"
            output += f"Description : {entry['Description']}\n"
            output += f"Keywords : {entry['Keywords']}\n\n```"

    if not matching_entries and not matching_rows:
        # If no match at all
        output += "No matches found."

    return output
    
    


def updateQLcvars(user_input):
    output = ""
    query = user_input
    new_values = shlex.split(query)

    if len(new_values) == 6:
        input_entry = new_values[0].strip('"')
        updated_entry = {'Entry': input_entry, 'Flags': new_values[1], 'Usage': new_values[2], 'Default Value': new_values[3], 'Description': new_values[4], 'Keywords': new_values[5]}

        matching_entry = None
        matching_entries = []

        # Read the JSON file and search for the input
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)

            # Check if the user input matches any value in the 'Entry' key
            for entry in data:
                if input_entry in entry['Entry']:
                    matching_entry = entry
                elif any(isinstance(value, str) and input_entry.lower() in value.lower() for value in entry.values()):
                    matching_entries.append(entry)

        if matching_entry and matching_entry['Entry'] == input_entry:
            output += f"```Updating {input_entry} with :\n\n"
            output += f"Flags : {updated_entry['Flags']}\n"
            output += f"Usage : {updated_entry['Usage']}\n"
            output += f"Default Value: {updated_entry['Default Value']}\n"
            output += f"Description : {updated_entry['Description']}\n"
            output += f"Keywords : {updated_entry['Keywords']}\n\n```"

            # Update the JSON file
            data.remove(matching_entry)
            data.append(updated_entry)

            with open(json_file_path, 'w') as json_file:
                json.dump(data, json_file, indent=4)

        elif matching_entries:
            output += f"**Cvar not found, maybe you meant one these ?**\n\n"
            for entry in matching_entries:
                output += f"```Cvar: {entry['Entry']}\n"
                output += f"Flags: {entry['Flags']}\n"
                output += f"Usage: {entry['Usage']}\n"
                output += f"Default Value: {entry['Default Value']}\n"
                output += f"Description: {entry['Description']}\n"
                output += f"Keywords: {entry['Keywords']}\n\n```"

        else:
            output += "No matching or relevant entry found. Just ask Cyardor :D"
    else: 
        output += "You're supposed to provide all fields (eg. ql.write cg_draw2D 'A T' 'cg_draw2D [0|1]' '1' 'Displays HUD elements.' 'hud'. \nThis will be upgraded soon :)"


    return output
    
    
def updateQLcvarField(query, field, new_value):
    output = ""
    input_entry = query.strip('"').lower()  # Make the input case-insensitive

    # Read the JSON file and search for the input
    with open(json_file_path, 'r') as json_file:
        data = json.load(json_file)

        matching_entry = None

        # Check if the user input matches any value in the 'Entry' key
        for entry in data:
            entry_name = entry.get('Entry', '').strip().lower()  # Remove leading/trailing spaces
            if input_entry == entry_name:  # Match in a case-insensitive way
                matching_entry = entry

        if matching_entry and input_entry == matching_entry.get('Entry', '').strip().lower():
            # print(f"Match found for input: {input_entry}")
            # Update the specified field with the new value
            if field in matching_entry:
                output += f"```Updating {input_entry}'s {field} with:\n\n"
                output += f"{field.capitalize()}: {new_value}\n\n```"

                # Update the JSON file
                matching_entry[field] = new_value

                with open(json_file_path, 'w') as json_file:
                    json.dump(data, json_file, indent=4)
            else:
                output += f"Invalid field: {field}. Please provide a valid field to update."
        else:
            # print(f"No match found for input: {input_entry}")
            output += f"Cvar not found. Please provide a valid cvar to update."

    return output
    
    
def read_scores():
    try:
        with open(SCORES_FILE, 'r') as scores_file:
            scores_data = json.load(scores_file)
        return scores_data
    except FileNotFoundError:
        return {}

def save_scores(scores_data):
    with open(SCORES_FILE, 'w') as scores_file:
        json.dump(scores_data, scores_file, indent=4)