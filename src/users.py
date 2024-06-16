import json

USERS_FILE = 'config/users.json'

def read_users():
    try:
        with open(USERS_FILE, 'r') as file:
            users_data = json.load(file)
    except FileNotFoundError:
        users_data = {}
    
    return users_data

def create_user(discord_id, steam_id=None, ql_elo=None, qc_name=None, qc_rank=None, donotdisturb=None):
    users_data = read_users()
    
    if discord_id not in users_data:
        users_data[discord_id] = {
            'steam_id': steam_id,
            'ql_elo': ql_elo,
            'qc_name': qc_name,
            'qc_rank': qc_rank,
            'donotdisturb': donotdisturb    
        }
        save_users(users_data)
        return True
    else:
        return False

def update_user(discord_id, field_to_edit, new_value):
    users_data = read_users()
    
    if discord_id in users_data:
        if field_to_edit in users_data[discord_id]:
            users_data[discord_id][field_to_edit] = new_value
            save_users(users_data)
            return True
    return False

def save_users(users_data):
    with open(USERS_FILE, 'w') as file:
        json.dump(users_data, file, indent=4)



def is_registered(user_id):
    with open('config/users.json', 'r') as users_file:
        users_data = json.load(users_file)

    return str(user_id) in users_data

def valid_steam_id(user_id):
    with open('config/users.json', 'r') as users_file:
        users_data = json.load(users_file)

    user_entry = users_data.get(str(user_id), {})
    return user_entry.get('steam_id') is not None