from colorama import Fore, Style


async def qonsoleprint(message):
    if message.guild:
        print(f"{Fore.WHITE}[#{message.channel.name.upper()}]{Fore.RED}<{message.author.name}{Fore.WHITE}@{Fore.WHITE}{Fore.BLUE}{message.author.id}> {Fore.GREEN}{message.content}{Style.RESET_ALL}")
    else:
        print(f"<{Fore.YELLOW}{message.author.name}{Fore.WHITE}@{Fore.WHITE}{Fore.BLUE}{message.author.id}{Fore.WHITE}> {Fore.GREEN}{message.content}{Style.RESET_ALL}")