# -*- coding: utf_8 -*-

import discord
import asyncio
import sys, os, traceback
import datetime
import settings

client = discord.Client()
commands = {} #command -> (function, tier), where function is the function to run, and tier is the user authority level required to run the command
userlevels = {} #userid -> authority level
userlastoutput = {} #userid -> bot's most recent Discord Message in response to the user (only keeps track since bot startup)
botoutputs = {} #channelid -> list of Discord Messages sent in this channel (only keeps track since bot startup)
global lastmessageDT
lastmessageDT = {} #channelid -> datetime of most recent Discord Message sent

#######################
#GENERAL BOT FUNCTIONS#
#######################
#Records bot activity in the log text file.
#- message: the Discord Message that triggered the activity (needed to retrieve stats like date, time, channel, and user)
#- logresult: a String that indicates the result of the activity (can be whatever you like)
def log(message, logresult):
    logmessage = message.content
    logresult = logresult.replace("\n", "\\n")
    
    #determine some values
    timestamp = message.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    username = message.author.name
    if message.server is not None:
        servername = message.server.name
    else:
        servername = "None"
    if message.channel.name is not None:
        channelname = message.channel.name
    else:
        channelname = "None"
    
    #normal log file
    file = open(settings.logfile, "a", encoding="utf8")
    if message.server is not None:
        file.write("{}\t{}\t{}\t{}\t{}\t{}\n".format(timestamp, message.server.id, message.channel.id, message.author.id, logmessage, logresult))
    else:
        file.write("{}\t{}\t{}\t{}\t{}\n".format(timestamp, message.channel.id, message.author.id, logmessage, logresult))
    file.close()
    
    #formatted log file
    file = open(settings.formattedlogfile, "a", encoding="utf8")
    file.write(settings.logformat.replace("%t", timestamp).replace("%s", servername).replace("%c", channelname).replace("%u", username).replace("%m", logmessage).replace("%r", logresult) + "\n")
    file.close()
    
    return

#Sends a Discord Message to a Discord Channel, possibly including a Discord Embed. Returns the Message object or a string if sending failed (i.e. cooldown is active)
#- receivemessage: the Discord Message that triggered the activity
#- sendchannel: the Discord Channel to send the message to; by default it's the channel where the triggering message was sent
#- sendcontent: the String to include in the outgoing Discord Message
#- sendembed: the Discord Embed to attach to the outgoing Discord Message
async def sendmessage(receivemessage, sendchannel=None, sendcontent="", sendembed=None):
    if sendchannel is None:
        sendchannel = receivemessage.channel
    
    #calculate time since the last bot output on this channel
    global lastmessageDT
    try:
        TD = datetime.datetime.now() - lastmessageDT[receivemessage.channel.id]
        cooldownactive = ((TD.microseconds / 1000) + (TD.seconds * 1000) < settings.channelcooldown)
    except KeyError:
        cooldownactive = False
    
    #calculate time since the last bot output from the user
    try:
        TD = datetime.datetime.now() - userlastoutput[receivemessage.author.id].timestamp
        userlevel = userlevels[receivemessage.author.id]
        usercooldown = 0
        while usercooldown == 0 and userlevel >= 0:
            try:
                usercooldown = getattr(settings, "usercooldown_{}".format(userlevel))
            except AttributeError:
                userlevel -= 1
        cooldownactive = ((TD.microseconds / 1000) + (TD.seconds * 1000) < usercooldown) or cooldownactive
    except KeyError:
        okay = "okay"
    
    #ignore message if bot is on channel cooldown or user cooldown
    if cooldownactive:
        return settings.message_cooldownactive
    
    #Discord messages cap at 2000 characters
    if len(sendcontent) > 2000:
        sendcontent = settings.message_resulttoolong.format(len(sendcontent))
    
    #send the message and track some data
    THEmessage = await client.send_message(sendchannel, sendcontent, embed=sendembed)
    userlastoutput[receivemessage.author.id] = THEmessage
    lastmessageDT[receivemessage.channel.id] = datetime.datetime.now()
    
    try:
        botoutputs[receivemessage.channel].append(THEmessage)
    except KeyError:
        botoutputs[receivemessage.channel] = [THEmessage]
    
    return THEmessage

#Assciates a String to a Function.
#- command: a String which is the command name or alias
#- function: the Function that the command calls
#- tier: a level of authority needed to run this command
def addcommand(command, function, tier):
    commands[command] = (function, tier)

#Use this function if userlevels.txt was manually edited (it will always be run on startup)
def updateuserlevels():
    userlevels.clear()
    userlevels[settings.masteradmin] = 9
    file = open(settings.userlevelsfile)
    filecontents = file.read()
    for line in filecontents.split("\n"):
        if line == "":
            continue
        try:
            userid = line.split("\t")[0]
            level = line.split("\t")[1]
            userlevels[userid] = int(level)
        except IndexError:
            print("error parsing user levels")
        except ValueError:
            print("error parsing user levels")
    file.close()

#Updates a user's authority level. Returns 0 if successful, -1 if not (i.e. level wasn't an integer)
def updateuserlevel(userid, level):
    #level should be an integer
    try:
        int(level)
    except ValueError:
        return -1
    
    #update userlevels.txt if it includes the user, otherwise append new entry
    if userid in userlevels.keys():
        userlevels[userid] = int(level)
        file = open(settings.userlevelsfile)
        filecontents = file.read()
        file.close()
        newfile = open(settings.userlevelsfile, "w")
        for line in filecontents.split("\n"):
            if line == "":
                continue
            try:
                userid2 = line.split("\t")[0]
                level2 = line.split("\t")[1]
                if userid == userid2:
                    newfile.write("{}\t{}\n".format(userid, level))
                else:
                    newfile.write("{}\n".format(line))
            except (IndexError, ValueError):
                print("error parsing user levels")
                newfile.write("{}\n".format(line))
        newfile.close()
    else:
        userlevels[userid] = int(level)
        file = open(settings.userlevelsfile, "a")
        file.write("{}\t{}\n".format(userid, level))
        file.close()
        
    return 0

#Returns a user's authority level (default is 1)
def getuserlevel(userid):
    try:
        return userlevels[userid]
    except KeyError:
        return 1

#Use this function if settings.txt was manually updated (it will always be run on startup)
#token can only be updated by restarting the bot
#botname is updated in the background task, so it won't update immediately
def updatesettings():
    file = open(settings.settingsfile)
    filecontents = file.read()
    for line in filecontents.split("\n"):
        if line == "":
            continue
        try:
            variable = line.split(" = ")[0]
            value = line[line.index(" = ")+3:]
            try:
                value = int(value)
            except ValueError:
                okay = "okay"
            setattr(settings, variable, value)
        except IndexError:
            print("error parsing settings")
    file.close()
    settings.masteradmin = str(settings.masteradmin)

#######
#SETUP#
#######
updatesettings()
updateuserlevels()

#background task is run every set interval while bot is running
async def backgroundtask():
    await client.wait_until_ready()
    while not client.is_closed:
        if client.user.name != settings.botname:
            await client.edit_profile(username=settings.botname)
        try:
            settings.backgroundtask()
        except TypeError:
            okay = "okay"
        await asyncio.sleep(settings.backgroundtaskinterval)
client.loop.create_task(backgroundtask())

@client.event
async def on_ready():
    print("Bot online!")
    print("Name: {}".format(client.user.name))
    print("ID: {}".format(client.user.id))

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
        if message.content.startswith(settings.commandprefix):
            try:
                command = message.content[len(settings.commandprefix):message.content.index(" ")]
                params = message.content[message.content.index(" ")+1:].split(settings.paramdelim)
            except ValueError:
                command = message.content[len(settings.commandprefix):]
        else:
            return
        command = command.lower()
        
        #CHECK IF COMMAND EXISTS
        if command not in commands.keys():
            return log(message, settings.message_unknowncommand)
        
        #CHECK PERMISSIONS OF USER
        try:
            authoritylevel = userlevels[message.author.id]
        except KeyError:
            authoritylevel = 1
        if authoritylevel < commands[command][1]:
            await sendmessage(message, sendcontent=settings.message_restrictedaccess)
            return log(message, settings.message_restrictedaccess)
        
        #RUN THE COMMAND
        function = commands[command][0]
        result = await function(message, params)
        try:
            if len(result.embeds) >= 1:
                log(message, "{} [embed]".format(result.content))
            else:
                log(message, result.content)
        except AttributeError:
            if result is None:
                log(message, "[]")
            else:
                log(message, "[{}]".format(result))
    
    except Exception as e:
        traceback.print_exc()
        await sendmessage(message, sendcontent=settings.message_somethingbroke)
        log(message, settings.message_unhandlederror)