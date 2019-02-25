# -*- coding: utf_8 -*-
#Koduck connects to Discord as a bot and sets up a system in which functions are triggered by messages it can see that meet a set of conditions
#Yadon helps by using text files to keep track of data, like command details, settings, and user levels!
#- Yadon will provide fresh data whenever it's used. However, Koduck needs to keep its own track of two things and won't know if the text files were manually updated:
#-- Command details include function objects, which can't be passed in simply through text (from Yadon), since Koduck should not have access to main
#--- Which means command details can only be passed in from outside (main) either before client startup or through a function triggered by a command
#--- To make it easier to initialize commands from Yadon, Koduck will try to run the "updatecommands" command after startup if it was passed in
#-- Settings are stored as attributes in a module where a bunch of required settings are initialized
#--- Settings read from the settings table will replace any initialized settings
#--- If a setting is removed from the settings table and updatesettings() is called, the setting will still be active (to be fixed)

import discord
import asyncio
import sys, os, traceback
import datetime
import settings, yadon

client = discord.Client()

#command -> (function, type, tier)
#command is a string which represents the command name
#function is the function object to run when the command is triggered
#type is a string that determines the trigger type of the command, should be one of (prefix, match, contain)
#tier is an integer which represents the user authority level required to run the command
commands = {}
userlastoutput = {} #userid -> bot's most recent Discord Message in response to the user (only keeps track since bot startup)
lastmessageDT = {} #channelid -> datetime of most recent Discord Message sent

#######################
#GENERAL BOT FUNCTIONS#
#######################
#Records bot activity in the log text file.
#- message: the Discord Message that triggered the activity (needed to retrieve stats like date, time, channel, and user)
#- logresult: a String that indicates the result of the activity (can be whatever you like)
def log(message, logresult=""):
    logmessage = message.content.replace("\n", "\\n")
    logresult = logresult.replace("\n", "\\n")
    
    #determine some values
    timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    username = message.author.name
    discr = message.author.discriminator
    if message.server is not None:
        servername = message.server.name
    else:
        servername = "None"
    if message.channel.name is not None:
        channelname = message.channel.name
    else:
        channelname = "None"
    
    #normal log file
    if message.server is not None:
        logstring = "{}\t{}\t{}\t{}\t{}\t{}\n".format(timestamp, message.server.id, message.channel.id, message.author.id, logmessage, logresult)
    else:
        logstring = "{}\t{}\t{}\t{}\t{}\n".format(timestamp, message.channel.id, message.author.id, logmessage, logresult)
    with open(settings.logfile, "a", encoding="utf8") as file:
        file.write(logstring)
    
    #formatted log file
    logstring = settings.logformat.replace("%t", timestamp).replace("%s", servername).replace("%c", "#" + channelname).replace("%u", username).replace("%U", "{}#{}".format(username, discr)).replace("%m", logmessage).replace("%r", logresult) + "\n"
    with open(settings.formattedlogfile, "a", encoding="utf8") as file:
        file.write(logstring)
    
    return

#Sends a Discord Message to a Discord Channel, possibly including a Discord Embed. Returns the Message object or a string if sending failed (i.e. cooldown is active)
#- receivemessage: the Discord Message that triggered the activity
#- sendchannel: the Discord Channel to send the message to; by default it's the channel where the triggering message was sent
#- sendcontent: the String to include in the outgoing Discord Message
#- sendembed: the Discord Embed to attach to the outgoing Discord Message
async def sendmessage(receivemessage, sendchannel=None, sendcontent="", sendembed=None, ignorecd=False):
    if receivemessage is not None:
        if sendchannel is None:
            sendchannel = receivemessage.channel
    
    #CHECK COOLDOWN
    userlevel = getuserlevel(receivemessage.author.id)
    cooldownactive = False
    if userlevel < settings.ignorecdlevel:
        #calculate time since the last bot output on this channel
        global lastmessageDT
        try:
            TD = datetime.datetime.now() - lastmessageDT[sendchannel.id]
            cooldownactive = ((TD.microseconds / 1000) + (TD.seconds * 1000) < settings.channelcooldown)
        except KeyError:
            pass
    
    if receivemessage is not None:
        #calculate time since the last bot output from the user
        try:
            TD = datetime.datetime.now() - userlastoutput[receivemessage.author.id].timestamp
            usercooldown = 0
            while usercooldown == 0 and userlevel >= 0:
                try:
                    usercooldown = getattr(settings, "usercooldown_{}".format(userlevel))
                except AttributeError:
                    userlevel -= 1
            cooldownactive = ((TD.microseconds / 1000) + (TD.seconds * 1000) < usercooldown) or cooldownactive
        except KeyError:
            pass
    #ignore message if bot is on channel cooldown or user cooldown
    if cooldownactive and not ignorecd:
        log(receivemessage, logresult=settings.message_cooldownactive)
        return
    
    #Discord messages cap at 2000 characters
    if len(sendcontent) > 2000:
        sendcontent = settings.message_resulttoolong.format(len(sendcontent))
    
    #send the message and track some data
    THEmessage = await client.send_message(sendchannel, sendcontent, embed=sendembed)
    log(THEmessage)
    if receivemessage is not None:
        userlastoutput[receivemessage.author.id] = THEmessage
    lastmessageDT[sendchannel.id] = datetime.datetime.now()
    
    return THEmessage

#Assciates a String to a Function.
#- command: a string which represents the command name (will be converted to lowercase)
#- function: the function object that the command should call
#- type: a string that determines the trigger type of the command, should be one of (prefix, match, contain)
#- tier: an integer which represents the level of authority needed to run this command
def addcommand(command, function, type, tier):
    commands[command.lower()] = (function, type, tier)

def clearcommands():
    commands = {}

#Use this function if settings table was manually updated (it will always be run on startup)
#token can only be updated by restarting the bot
#botname is updated in the background task, so it won't update immediately
#Note: settings is a module with attributes, so removing a setting manually from the table doesn't actually remove the attribute
def updatesettings():
    table = yadon.ReadTable(settings.settingstablename)
    for key, values in table.items():
        try:
            value = values[0]
            #try to convert into float or int, otherwise treat as string
            try:
                if float(value) % 1 == 0:
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                value = value.replace("\\n", "\n").replace("\\t", "\t")
        except IndexError:
            value = None
        setattr(settings, key, value)

#update a setting and updates the settings file accordingly
#returns None if setting name doesn't exist, returns old value if it does and updating its value succeeded
def updatesetting(variable, value):
    try:
        oldvalue = getattr(settings, variable)
    except AttributeError:
        return
    
    value = value.replace("\n", "\\n").replace("\t", "\\t")
    yadon.WriteRowToTable(settings.settingstablename, variable, [value])
    try:
        if float(value) % 1 == 0:
            value = int(value)
        else:
            value = float(value)
    except ValueError:
        value = value.replace("\\n", "\n").replace("\\t", "\t")
    setattr(settings, variable, value)
    return oldvalue

#add a setting and updates the settings file accordingly
#returns None if setting already exists, returns value if it doesn't
def addsetting(variable, value):
    try:
        getattr(settings, variable)
        return
    except AttributeError:
        pass
    
    value = value.replace("\n", "\\n").replace("\t", "\\t")
    yadon.WriteRowToTable(settings.settingstablename, variable, [value])
    try:
        if float(value) % 1 == 0:
            value = int(value)
        else:
            value = float(value)
    except ValueError:
        value = value.replace("\\n", "\n").replace("\\t", "\t")
    setattr(settings, variable, value)
    return value

#Updates a user's authority level. Returns 0 if successful, -1 if not (i.e. level wasn't an integer)
def updateuserlevel(userid, level):
    #level should be an integer
    try:
        int(level)
    except ValueError:
        return -1
    
    yadon.WriteRowToTable(settings.userlevelstablename, userid, [str(level)])
    return 0

def getuserlevel(userid):
    try:
        return int(yadon.ReadRowFromTable(settings.userlevelstablename, userid)[0])
    except (TypeError, IndexError, ValueError):
        return 1

#Run a command as if it was triggered by a Discord message
async def runcommand(command, message=None, params=[]):
    try:
        function = commands[command][0]
        return await function(message, params)
    except (KeyError, IndexError):
        return

#######
#SETUP#
#######
updatesettings()

#background task is run every set interval while bot is running
async def backgroundtask():
    await client.wait_until_ready()
    while not client.is_closed:
        if client.user.bot and client.user.name != settings.botname:
            await client.edit_profile(username=settings.botname)
        if callable(settings.backgroundtask):
            client.loop.create_task(settings.backgroundtask())
        await asyncio.sleep(settings.backgroundtaskinterval)
client.loop.create_task(backgroundtask())

@client.event
async def on_ready():
    print("Bot online!")
    print("Name: {}".format(client.user.name))
    print("ID: {}".format(client.user.id))
    await runcommand("updatecommands")

##############
#INPUT OUTPUT#
##############
@client.event
async def on_message(message):
    #ignore bot messages
    if message.author.bot:
        return
    
    try:
        #PARSE COMMAND AND PARAMS
        command = ""
        params = []
        for commandname in commands.keys():
            if commandname in message.content.lower():
                commanddetails = commands[commandname]
                entireprefix = settings.commandprefix + commandname
                if message.content.lower().startswith(entireprefix) and commanddetails[1] == "prefix":
                    command = commandname
                    #Only prefixed commands should have parameters
                    extra = message.content[len(entireprefix)+1:]
                    if len(extra) > 0:
                        params = extra.split(settings.paramdelim)
                    break
                elif message.content.lower() == commandname and commanddetails[1] == "match":
                    command = commandname
                    break
                elif commanddetails[1] == "contain":
                    command = commandname
                    break
        if command == "":
            return
        
        #CHECK PERMISSIONS OF USER
        userlevel = getuserlevel(message.author.id)
        if userlevel < commands[command][2]:
            await sendmessage(message, sendcontent=settings.message_restrictedaccess)
            log(message, logresult=settings.message_restrictedaccess)
            return
        
        log(message)
        #RUN THE COMMAND
        function = commands[command][0]
        result = await function(message, params)
        if isinstance(result, str):
            log(message, logresult=result)
    
    except Exception as e:
        traceback.print_exc()
        await sendmessage(message, sendcontent=settings.message_somethingbroke)
        log(message, logresult=settings.message_unhandlederror)