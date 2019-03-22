# Koduck

## Introduction
Koduck is a Discord bot framework written in Python! Originally, I'd developed a bot named [KoduckBot](https://github.com/Chupalika/KoduckBot) that provides info from a game. After some time it occurred to me that I might want to create a similar bot for other games. The only differences would be the functions that collected and outputted game data. And also my code was a bit messy... So I got the idea to create a general bot with basic functions - this would be the base template - then add functions as needed. I tried to design it to be easy to learn and use, but I think it might be turning out too complex. :|

The goal of Koduck is to give bot developers a quick start and several implemented features that might be useful, such as spam prevention using cooldowns, data storage and access using text files, and logging.

## Features
- Add bot commands easily!
- Authority levels - assign levels to users and commands to control who has access to which commands
- Log - automatically log bot activity to use for debugging or statistics or whatever
- Messages are automatically parsed for command triggers and parameters which are passed to whatever function you define (also supports keyword arguments!)
- Yadon - A tool for storing and accessing data tables in text files as TSVs (tab separated values)
- Base command functions provided can be used as a guide for developing your own functions

## Requirements
- Python 3.0 to 3.6 (discord.py does not work with 3.7+)
- discord module (install with ``python -m pip install -U discord.py``)
- a Discord application (create one [here](https://discordapp.com/developers/applications/))
- It would help a lot to have at least some experience programming in Python...

## Quick Setup
- download/clone repository
- in settings.txt, set token to your bot's token (turn your Discord application into a bot to generate a token)
- in userlevels.txt, add a line which looks like this: ``userid\t3\n`` where \t is a tab, \n is a new line, and userid is your user id (right click yourself in Discord and click "Copy ID" - developer mode needs to be enabled for the option to show up)
- open up a command prompt, change working directory to where Koduck is, run command ``python main.py``

## Included Files

### koduck.py
Implements communication with discord, message parsing, logging, command and setting management, and message sending with cooldown check. Read the comments in the script for documentation, but try not to edit it.

### settings.py
Includes some required default settings for Koduck. Try not to edit this either, though it shouldn't be a big deal if you do. Add and edit settings using settings.txt instead.

### yadon.py
Provides tools for reading and writing data to and from text files in TSV table format. (Note that copying and pasting spreadsheet data to text files automatically separates cells with tabs!)
- The table is read as a dictionary (key -> values) with the first column as keys. This means that duplicate keys aren't supported - only the last row of the duplicates will be read.
- Data is read on the fly, so any manual updates to Yadon tables will also update any output in the future
- Although Koduck uses a few Yadon tables to help it operate, it needs to store the data read from the settings and commands tables, which means they don't update values on the fly if edited manually. That's why there are update command functions provided in main.py.

### main.py
A template that uses Koduck. It adds a bunch of basic commands like shutdown, restrictuser, and userinfo. Use them as a guide to add your own commands, and feel free to remove any functions you don't need.

### commands.txt
A Yadon table that stores details about commands.
- The first column represents the text that will trigger the command
- The second column represents the name of the function in main.py that will be called
- The third column represents the type of trigger: prefix triggers if the message begins with the bot prefix + the trigger text (this type is the only type that supports having parameters), match triggers if the message matches the text exactly, contain triggers if the message contains the text
- The fourth column represents the minimum user level required to use this command

Remember to add your commands to this table when you finish coding new command functions in main.py!

### settings.txt
A Yadon table for storing custom settings for Koduck. Use this to store variables that you might want to be edited during bot runtime.
- Any variables updated here (except token) can be updated during runtime with Koduck's updatesettings function
- These settings overwrite settings in settings.py of the same name
- The third column is an optional user level required to edit and remove the setting (defaults to 1, but remember that the editsetting and removesetting commands also have user level requirements)

### userlevels.txt
A yadon table for storing the authority levels of users. By default all users are level 1. Rows in this table determine otherwise. The first column represents the user id and the second column represents the user level.

## Generated Files

### log.txt
This file stores the history of the bot's activity in a default, tab-seperated format which includes IDs of things.

### formattedlog.txt
This file stores the history of the bot's activity in a customizable, hopefully more readable format. You can customize it by setting the logformat setting, where:
- %t represents timestamp
- %s represents server name
- %c represents channel name
- %u represents username
- %U represents user tag (username plus the #0000)
- %n represents nickname
- %m represents the user message
- %r represents the output result

Many of these values can be empty, especially when logging activity that does not involve discord messages.

### customresponses.txt
This Yadon table is generated from the addcustomresponse() command function. It's an example usage of 'match' type commands and Yadon. A message that matches the trigger text will trigger a call to the customresponse() command function which will look up the text in this table and send a response message with the text in the second column.
