# Koduck

## Introduction
Koduck is a Discord bot framework written in Python! Its purpose is to jumpstart your Discord bot project with code that works out of the box, along with a number of handy features to help with management and data storage, and a number of example commands to help guide you in creating your own commands.

Koduck was originally intended for providing info and stats from game data (hence the tables stored in text files) and not really for managing roles and other administrative things in large servers, but it could probably be tweaked to include those purposes. This also means that whoever hosts it doesn't have to be an admin of the server, rather, Koduck maintains its own admins. Of course, server admins would still be able to control the permissions of the Koduck bot itself, for example restricting it to view certain channels, but only Koduck admins will be able to control the behavior of Koduck.

More advanced developers may want to check out the discord.py documentation, especially [discord.ext.commands](https://discordpy.readthedocs.io/en/latest/ext/commands/index.html), which is discord.py's own bot framework. However, if you just want something simple that is easy to setup, then Koduck is for you!

**Note**: This version of Koduck is updated to use discord.py v2.0, which is currently in beta and unstable. Please be advised!

## Background
For those interested - Originally, I had developed a bot named [KoduckBot](https://github.com/Chupalika/KoduckBot) that provides info from a game (Pokemon Shuffle). After some time it occurred to me that I might want to create a similar bot for other games. The only differences would be the functions that collected and outputted game data. I also wanted to clean up my messy code. So I got the idea to create a general bot with basic functions - this would be the base template - then add functions as needed. After that, the code grew over time as I got more ideas and Discord implemented more features.

## Features
- Add bot commands easily!
- Authority levels - assign levels to users and commands to control who has access to which commands
- Log - automatically log bot activity to use for debugging, statistics, etc.
  - If you prefer the standard, more verbose logger, you can enable it by setting the `enable_debug_logger` setting to a truthy value
- Messages are automatically parsed for command triggers and parameters which are passed to whatever function you define (also supports keyword arguments!)
- Yadon - A tool for storing and accessing data tables in text files as TSVs (tab separated values)
- Command functions provided in the base kit can be used as a guide for developing your own functions
- Support for App (Slash) Commands and Interactions
  - A `run` command is included which simulates a chat command. This can be useful for unverified bots in over 100 servers, since they cannot read messages without the `message_content` intent. The command is disabled by default - enable it by setting the `enable_run_command` setting to a truthy value

## Requirements
- Python 3.10+
- discord.py 2.0+
  - install in command prompt with `python -m pip install -U discord.py`
- a Discord application (create one [here](https://discordapp.com/developers/applications/))
  - turn it into a bot and take note of its token: it's basically its password
- It would help a lot to have at least some experience programming in Python...

## Quick Setup
- download/clone repository
- in `tables/settings.txt`, set the token to your bot's token
- in `tables/user_levels.txt`, replace `user_id` with your user id (to find this, right click yourself in Discord and click "Copy ID" - developer mode needs to be enabled for the option to show up)
- open up a command prompt, change the working directory to the Koduck folder, and run command `python main.py`

## Included Files

### koduck.py
Implements communication with discord, message parsing, logging, command and setting management, and message sending with cooldown check. Read the comments in the script for documentation, but try not to edit it.

### settings.py
Includes some required default settings for Koduck. Try not to edit this either, though it shouldn't be a big deal if you do. Add and edit settings using settings.txt instead.

### yadon.py
Provides tools for reading and writing data to and from text files in TSV table format. (Note that copying and pasting spreadsheet data to text files automatically separates cells with tabs!)
- The table is read as a dictionary (key -> values) with the first column as keys. This means that duplicate keys aren't supported - only the last row of the duplicates will be read.
- Data is read on the fly, so any manual updates to Yadon tables will also update any output in the future
- Although Koduck uses a few Yadon tables to help it operate, it needs to store the data read from the settings and commands tables, which means they don't update values on the fly if edited manually. That's why there are update command functions provided in the kit.

### main.py
The main script to start up Koduck. It includes the `refresh_commands` command function which is required to setup Koduck.

### *_commands.py
These scripts contain helpful basic commands such as `shutdown`, `restrictuser`, and `userinfo`. Use them as a guide to add your own commands, and feel free to remove any command functions you don't need. Note that each command function (besides slash commands) should take in at least one parameter for the KoduckContext. `\*args` and `\*\*kwargs` are recommended (but optional) to include in the signatures also, since python will throw an error if unexpected arguments are passed in by users.

An example of a prefix command might look like this: `/stage Psyduck option=shorthand`. Note that the default parameter delimiter is space, but multi-word arguments can be specified using quotes, like `key="multi word value"`.
* context will contain:
  * `koduck` is the Koduck instance for accessing its methods like `send_message`
  * `message` is the Discord.Message object that triggered the command
  * `command` is the trigger text ('stage')
  * `command_line` is the message text except for the prefix ('stage Psyduck, option=shorthand')
  * `params` is a list of the parameters (\['Psyduck', 'option=shorthand'\])
  * `param_line` is the message text except for the prefix and command ('Psyduck, option=shorthand')
  * `\*args` is a list of the unnamed parameters (\['Psyduck'\])
  * `\*\*kwargs` is a dict of the named parameters ({'option':'shorthand'})

Slash commands should take in a discord.Interaction parameter instead of a KoduckContext. The Koduck instance will be attached to it as the `koduck` property.

### commands.txt
A Yadon table that stores details about commands.
- The first column represents the text that will trigger the command
- The second column represents the name of the module where the function is defined
- The third column represents the name of the (callback) function in the module that will be called
- The fourth column represents the type of trigger:
  - `prefix` triggers if the message begins with the bot prefix + the trigger text (this type allows the callback function to have parameters)
  - `match` triggers if the message matches the text exactly
  - `contain` triggers if the message contains the text
  - `slash` indicates that it is an app command to be registered to Discord servers (this type allows the callback function to have parameters)
- The fifth column represents the minimum user level required to use this command
- The sixth column represents the description of the command which is required only for slash commands

Remember to add your commands to this table when you finish coding new command functions!

### settings.txt
A Yadon table for storing custom settings for Koduck. Use this to store variables that you might want to be edited during bot runtime.
- Any variables that are manually updated here (besides the bot token) can be updated during runtime with the provided `refreshsettings` command
- These settings overwrite settings in settings.py of the same name
- The third column is an optional user level required to edit and remove the setting (defaults to `max_user_level` defined in settings.py)

### user_levels.txt
A yadon table for storing the authority levels of users. By default all users are level 1. Rows in this table determine otherwise. The first column represents the user id and the second column represents the user level.

## Generated Files

### log.txt
This file stores the history of the bot's activity in a customizable format. You can customize it by setting the `log_format` setting using the keywords below. Note that many of these values can be empty. Timestamp is the only value guaranteed to be non-empty.
- `{timestamp}` represents the timestamp
- `{type}` represents the type of activity
- `{server_id}` represents the server ID
- `{server_name}` represents the server name
- `{channel_id}` represents the channel ID
- `{channel_name}` represents the channel name
- `{user_id}` represents the user ID
- `{discord_tag}` represents the user tag (username plus the #0000)
- `{nickaname}` represents the user nickname
- `{message_content}` represents the message content
- `{embed_data}` represents the embed data
- `{attachment_data}` represents the attachment data
- `{interaction_data}` represents the interaction data
- `{extra}` represents an extra string that helps describe the activity

### custom_responses.txt
This Yadon table is generated from the `add_custom_response()` command function. It's an example usage of `match` type commands and Yadon. A message that matches the trigger text will trigger a call to the `custom_response()` command function which will look up the text in this table and send a response message with the text in the second column.

### requestable_roles.txt
This Yadon table is generated from another example command function, `add_requestable_roles()`. Roles added this way will be stored in this table, and show up for users to toggle when they run the `requestroles` command.
