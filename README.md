# Koduck

## Introduction
Koduck is a very basic Discord bot framework written in Python! Originally, I'd developed a bot named [KoduckBot](https://github.com/Chupalika/KoduckBot) that provides info from a game. After some time it occurred to me that I might want to create a similar bot for other games. The only differences would be the functions that collected and outputted game data. And also my code was a bit messy... So I got the idea to create a general bot with basic functions - this would be the base template - then add functions as needed. I tried to design it to be easy to learn and use!

## Features
- Add bot commands easily!
- Authority levels - assign levels to users and commands to control who has access to which commands
- Log - automatically log bot activity to use for debugging or statistics or whatever

## Requirements
- Python 3.6+ (I think Python 3-3.5 should also work fine)
- discord module (install with ``python -m pip install -U discord.py``)
- a Discord application (create one [here](https://discordapp.com/developers/applications/))

## Quick Setup
- download/clone repository
- in settings.txt, set token to your bot's token (turn your Discord application into a bot to generate a token)
- in settings.txt, set masteradmin to your user id (right click yourself in Discord and click "Copy ID" - developer mode needs to be enabled for the option to show up)
- run in command prompt ``python main.py``

## Included Files

### koduck.py
Implements functions like sendmessage, addcommand, and updateuserlevel. Read the comments in the script for documentation, but try not to edit it.

### settings.py
Includes default settings for Koduck. Try not to edit this either, though it shouldn't be a big deal if you do. Edit settings using settings.txt instead.

### main.py
A template that uses Koduck. It adds a bunch of basic commands like shutdown, restrictuser, and userinfo. Use them as a guide to add your own commands.

### settings.txt
Custom settings for Koduck. Use this to store variables. Any variables updated here (except token) can be updated during bot runtime with Koduck's updatesettings function. These settings overwrite the settings in settings.py.

## Generated Files

### userlevels.txt
This file stores the authority levels of users. By default all users are level 1. Any info stored in this file should determine otherwise. Each line is an entry in the format [userid]\t[level]

### log.txt
This file stores the history of the bot's activity in a default, tab-seperated format which includes IDs of things.

### formattedlog.txt
This file stores the history of the bot's activity in a customizable, hopefully more readable format. You can customize it by setting the logformat setting, where:
- %t represents timestamp
- %s represents server name
- %c represents channel name
- %u represents username
- %U represents user tag (username plus the #0000)
- %m represents the user message
- %r represents the output result
