import json

def load_config():
    # Read configuration from config.json
    with open('config/config.json', 'r') as config_file:
        config_data = json.load(config_file)

    # Extract values from config
    BOT_TOKEN = config_data.get("BOT_TOKEN")
    CHANNEL_QL = config_data.get("CHANNEL_QL")
    CHANNEL_QC = config_data.get("CHANNEL_QC")
    CHANNEL_LFG = config_data.get("CHANNEL_LFG")
    ADMINS = config_data.get("ADMINS")
    GUILD_ID = config_data.get("GUILD_ID")
    RANK_VALUES = config_data.get("RANK_VALUES", {})
    QL_EU_ROLES = config_data.get("QL_EU_ROLES")
    QL_NA_ROLES = config_data.get("QL_NA_ROLES")
    
    # Validate the presence of required values
    if not BOT_TOKEN or not CHANNEL_QL or not ADMINS or not GUILD_ID:
        print("Error: Missing configuration values. Please check your config.json file.")
        exit()

    return BOT_TOKEN, CHANNEL_QL, CHANNEL_QC, CHANNEL_LFG, ADMINS, GUILD_ID, RANK_VALUES, QL_EU_ROLES, QL_NA_ROLES