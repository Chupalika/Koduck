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
global lastmessageDT
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
        
    #calculate time since the last bot output on this channel
    global lastmessageDT
    try:
        TD = datetime.datetime.now() - lastmessageDT[sendchannel.id]
        cooldownactive = ((TD.microseconds / 1000) + (TD.seconds * 1000) < settings.channelcooldown)
    except KeyError:
        cooldownactive = False
    
    if receivemessage is not None:
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
            pass
    
    #ignore message if bot is on channel cooldown or user cooldown
    if cooldownactive and not ignorecd:
        return settings.message_cooldownactive
    
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
#- command: a String which is the command name or alias
#- function: the Function that the command calls
#- tier: a level of authority needed to run this command
def addcommand(command, function, tier):
    commands[command] = (function, tier)

#Use this function if userlevels.txt was manually edited (it will always be run on startup)
def updateuserlevels():
    userlevels.clear()
    userlevels[settings.masteradmin] = 9
    try:
        file = open(settings.userlevelsfile)
    except FileNotFoundError:
        return
    filecontents = file.read()
    file.close()
    lines = filecontents.split("\n")
    for i in range(len(lines)):
        line = lines[i]
        if line == "":
            continue
        try:
            userid = line.split("\t")[0]
            level = line.split("\t")[1]
            userlevels[userid] = int(level)
        except (IndexError, ValueError):
            print("error parsing user level on line {}".format(i))

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
        lines = filecontents.split("\n")
        newfile = open(settings.userlevelsfile, "w")
        for i in range(len(lines)):
            line = lines[i]
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
                print("error parsing user level on line {}".format(i))
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
    file = open(settings.settingsfile, encoding="utf8")
    filecontents = file.read()
    file.close()
    lines = filecontents.split("\n")
    for i in range(len(lines)):
        line = lines[i]
        if line == "" or line.startswith("#"):
            continue
        try:
            variable = line.split(" = ")[0]
            value = line[line.index(" = ")+3:]
            try:
                if float(value) % 1 == 0:
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                value = value.replace("\\n", "\n").replace("\\t", "\t")
            setattr(settings, variable, value)
        except (IndexError, ValueError):
            print("failed to parse settings on line {}".format(i))
    settings.masteradmin = str(settings.masteradmin)

#update a setting and updates the settings file accordingly
#returns None if setting name doesn't exist, returns old value if it does and updating its value succeeded
def updatesetting(variable, value):
    try:
        oldvalue = getattr(settings, variable)
    except AttributeError:
        return
    
    value = value.replace("\n", "\\n").replace("\t", "\\t")
    
    file = open(settings.settingsfile, encoding="utf8")
    filecontents = file.read()
    file.close()
    
    lines = filecontents.split("\n")
    newfile = open(settings.settingsfile, "w", encoding="utf8")
    result = False
    for i in range(len(lines)):
        line = lines[i]
        if line == "" or line.startswith("#"):
            #prevent adding a blank line to the end
            if line == "" and i == len(lines) - 1:
                continue
            else:
                newfile.write("{}\n".format(line))
                continue
        try:
            oldvariable = line.split(" = ")[0]
            if oldvariable == variable:
                newfile.write("{} = {}\n".format(variable, value))
                result = True
            else:
                newfile.write("{}\n".format(line))
        except (IndexError, ValueError):
            newfile.write("{}\n".format(line))
    
    #if result is False at this point, that means it was in settings.py
    #append this override into settings.txt
    if not result:
        newfile.write("{} = {}\n".format(variable, value))
    newfile.close()
    
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
    file = open(settings.settingsfile, "a", encoding="utf8")
    file.write("{} = {}\n".format(variable, value))
    file.close()
    
    try:
        if float(value) % 1 == 0:
            value = int(value)
        else:
            value = float(value)
    except ValueError:
        value = value.replace("\\n", "\n").replace("\\t", "\t")
    setattr(settings, variable, value)
    return value

#Run a command as if it was triggered by a Discord message
async def runcommand(command, message=None, params=[]):
    function = commands[command][0]
    result = await function(message, params)

#######
#SETUP#
#######
updatesettings()
updateuserlevels()

#background task is run every set interval while bot is running
async def backgroundtask():
    await client.wait_until_ready()
    while not client.is_closed:
        if client.user.bot and client.user.name != settings.botname:
            await client.edit_profile(username=settings.botname)
        try:
            await settings.backgroundtask()
        except TypeError:
            pass
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
            log(message, logresult=settings.message_unknowncommand)
            return
        
        #CHECK PERMISSIONS OF USER
        try:
            authoritylevel = userlevels[message.author.id]
        except KeyError:
            authoritylevel = 1
        if authoritylevel < commands[command][1]:
            await sendmessage(message, sendcontent=settings.message_restrictedaccess)
            log(message, logresult=settings.message_restrictedaccess)
            return
        
        log(message)
        #RUN THE COMMAND
        function = commands[command][0]
        result = await function(message, params)
    
    except Exception as e:
        traceback.print_exc()
        await sendmessage(message, sendcontent=settings.message_somethingbroke)
        log(message, logresult=settings.message_unhandlederror)