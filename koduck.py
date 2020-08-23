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
import sys, os, traceback, re
import datetime, pytz
import settings, yadon

client = discord.Client()
koduckinstance = None

class Koduck:
    def __init__(self):
        self.client = client
        global koduckinstance
        koduckinstance = self
        
        #command -> (function, type, tier)
        #command is a string which represents the command name
        #function is the function object to run when the command is triggered
        #type: a string that determines the trigger type of the command, should be one of (prefix, match, contain)
        #tier is an integer which represents the user authority level required to run the command
        self.commands = {}
        self.prefixcommands = []
        self.matchcommands = []
        self.containcommands = []
        
        self.outputhistory = {} #userid -> list of Discord Messages sent by bot in response to the user, oldest first (only keeps track since bot startup)
        self.lastmessageDT = {} #channelid -> datetime of most recent Discord Message sent
        
        self.updatesettings()
        client.loop.create_task(backgroundtask())
    
    #######################
    #GENERAL BOT FUNCTIONS#
    #######################
    #Records bot activity in the log text files.
    #- message: the Discord Message that triggered the activity (for retrieving stats like date, time, channel, and user)
    #- logresult: a String that indicates the result of the activity (can be whatever you like)
    def log(self, message=None, logresult=""):
        logresult = logresult.replace("\n", "\\n")
        
        if message is None:
            timestamp = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            
            #normal log file
            logstring = "{}\t\t\t\t\t{}\n".format(timestamp, logresult)
            with open(settings.logfile, "a", encoding="utf8") as file:
                file.write(logstring)
            
            #formatted log file
            logstring = settings.logformat.replace("%t", timestamp).replace("%s", "").replace("%c", "").replace("%u", "").replace("%U", "").replace("%n", "").replace("%m", "").replace("%r", logresult) + "\n"
            with open(settings.formattedlogfile, "a", encoding="utf8") as file:
                file.write(logstring)
        
        else:
            #determine some values
            logmessage = message.content.replace("\n", "\\n")
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S.%f")
            username = message.author.name
            discr = message.author.discriminator
            if message.guild is not None:
                servername = message.guild.name
                nickname = message.author.nick or ""
            else:
                servername = ""
                nickname = ""
            if hasattr(message.channel, "name"):
                channelname = message.channel.name
            else:
                channelname = ""
            
            #normal log file
            logstring = "{}\t{}\t{}\t{}\t{}\t{}\n".format(timestamp, message.guild.id if message.guild is not None else "", message.channel.id if message.guild is not None else "", message.author.id, logmessage, logresult)
            with open(settings.logfile, "a", encoding="utf8") as file:
                file.write(logstring)
            
            #formatted log file
            logstring = settings.logformat.replace("%t", timestamp).replace("%s", servername).replace("%c", "#" + channelname if channelname else "").replace("%u", username).replace("%U", "{}#{}".format(username, discr)).replace("%n", nickname).replace("%m", logmessage).replace("%r", logresult) + "\n"
            with open(settings.formattedlogfile, "a", encoding="utf8") as file:
                file.write(logstring)
    
    #Sends a Discord Message to a Discord Channel, possibly including a Discord Embed. Returns the Message object or a string if sending failed (i.e. cooldown is active)
    #- receivemessage: the Discord Message that triggered the activity (can be None)
    #- sendchannel: the Discord Channel to send the message to; by default it's the channel where the triggering message was sent
    #- sendcontent: the String to include in the outgoing Discord Message
    #- sendembed: the Discord Embed to attach to the outgoing Discord Message
    #- sendfile: a Discord File to include in the outgoing Discord Message (note: if this is not None, then sendembed is ignored)
    async def sendmessage(self, receivemessage, sendchannel=None, sendcontent="", sendembed=None, sendfile=None, ignorecd=False):
        #If sendmessage was triggered by a user message, check cooldowns
        if receivemessage is not None:
            if sendchannel is None:
                sendchannel = receivemessage.channel
            
            #Check cooldowns
            cooldownactive = False
            userlevel = self.getuserlevel(receivemessage.author.id)
            if userlevel < settings.ignorecdlevel:
                cooldownactive = self.checkchannelcooldown(sendchannel.id)
            cooldownactive = cooldownactive or self.checkusercooldown(receivemessage.author.id)
            
            #ignore message if bot is on channel cooldown or user cooldown
            if cooldownactive and not ignorecd:
                self.log(receivemessage, logresult=settings.message_cooldownactive)
                return
        
        #Discord messages cap at 2000 characters
        if len(sendcontent) > 2000:
            sendcontent = settings.message_resulttoolong.format(len(sendcontent), 2000)
        
        #Discord embed limits
        #URL validation is not done here, but invalid URLs will cause a 400 error
        if sendembed and not sendfile:
            errors = []
            
            #Embed title
            if sendembed.title != discord.Embed.Empty and len(str(sendembed.title)) > 256:
                errors.append(("overflow", "title", len(str(sendembed.title)), 256))
            
            #Embed description
            if sendembed.description != discord.Embed.Empty and len(str(sendembed.description)) > 2048:
                errors.append(("overflow", "description", len(str(sendembed.description)), 2048))
            
            #Embed footer
            if sendembed.footer.text != discord.Embed.Empty and len(str(sendembed.footer.text)) > 2048:
                errors.append(("overflow", "footer.text", len(str(sendembed.footer.text)), 2048))
            
            #Embed author
            if sendembed.author.name != discord.Embed.Empty and len(str(sendembed.author.name)) > 256:
                errors.append(("overflow", "author.name", len(str(sendembed.author.name)), 256))
            
            #Embed fields
            if len(sendembed.fields) > 25:
                errors.append(("overflow", "fields", len(sendembed.fields), 25))
            for field in sendembed.fields:
                if len(str(field.name)) == 0:
                    errors.append(("empty", "field.name", 0, 0))
                if len(str(field.name)) > 256:
                    errors.append(("overflow", "field.name", len(field.name), 256))
                if len(str(field.value)) == 0:
                    errors.append(("empty", "field.value", 0, 0))
                if len(str(field.value)) > 1024:
                    errors.append(("overflow", "field.value", len(field.value), 1024))
            
            #Embed total characters
            totalcharacters = sum([len(x) for x in [str(sendembed.title), str(sendembed.description), str(sendembed.footer.text), str(sendembed.author.name)] if x != discord.Embed.Empty]) + sum([len(str(field.name)) + len(str(field.value)) for field in sendembed.fields])
            if totalcharacters > 6000:
                errors.append(("overflow", "embed", totalcharacters, 6000))
            
            #Check collected errors
            if len(errors) > 0:
                if errors[0][0] == "empty":
                    sendcontent = settings.message_embedemptyfield.format(errors[0][1])
                    sendembed = None
                elif errors[0][0] == "overflow":
                    sendcontent = settings.message_embedtoolong.format(errors[0][1], errors[0][2], errors[0][3])
                    sendembed = None
        
        #send the message and track some data
        if not sendfile:
            THEmessage = await sendchannel.send(content=sendcontent, embed=sendembed)
        else:
            THEmessage = await sendchannel.send(content=sendcontent, file=sendfile)
        self.log(THEmessage)
        if receivemessage is not None:
            userlastoutputs = self.getuserlastoutputs(receivemessage.author.id)
            userlastoutputs.append(THEmessage)
            self.outputhistory[receivemessage.author.id] = userlastoutputs[max(0,len(userlastoutputs)-settings.outputhistorysize):]
        self.lastmessageDT[sendchannel.id] = datetime.datetime.now()
        
        return THEmessage
    
    #Assciates a String to a Function.
    #- command: a string which represents the command name (will be converted to lowercase)
    #- function: the function object that the command should call
    #- type: a string that determines the trigger type of the command, should be one of (prefix, match, contain)
    #- tier: an integer which represents the level of authority needed to run this command
    def addcommand(self, command, function, type, tier):
        if type == "prefix":
            self.prefixcommands.append(command.lower())
        elif type == "match":
            self.matchcommands.append(command.lower())
        elif type == "contain":
            self.containcommands.append(command.lower())
        else:
            return
        self.commands[command.lower()] = (function, type, tier)
    
    #Remove a command, returns 0 if successful, -1 if command not recognized
    def removecommand(self, command):
        if command not in self.commands.keys():
            return -1
        commanddetails = self.commands[command]
        {"prefix": self.prefixcommands, "match": self.matchcommands, "contain": self.containcommands}[commanddetails[1]].remove(command)
        del self.commands[command]
    
    def clearcommands(self):
        self.prefixcommands = []
        self.matchcommands = []
        self.containcommands = []
        self.commands = {}
    
    #Use this function if settings table was manually updated (it will always be run on startup)
    #token can only be updated by restarting the bot
    #botname is updated in the background task, so it won't update immediately
    #Note: settings is a module with attributes, so removing a setting manually from the table doesn't actually remove the attribute
    def updatesettings(self):
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
    #returns None if setting name doesn't exist or auth level is lower than setting's level (defaults to max user level if not specified or setting is in settings.py), returns old value if it does and updating its value succeeded
    def updatesetting(self, variable, value, authlevel=settings.defaultuserlevel):
        try:
            oldvalue = getattr(settings, variable)
        except AttributeError:
            return
        
        try:
            settinglevel = int(yadon.ReadRowFromTable(settings.settingstablename, variable)[1])
        except (IndexError, ValueError, TypeError):
            settinglevel = settings.maxuserlevel
        if settinglevel > authlevel:
            return
        
        value = value.replace("\n", "\\n").replace("\t", "\\t")
        yadon.WriteRowToTable(settings.settingstablename, variable, [value, str(settinglevel)])
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
    def addsetting(self, variable, value, authlevel=settings.defaultuserlevel):
        try:
            getattr(settings, variable)
            return
        except AttributeError:
            pass
        
        value = value.replace("\n", "\\n").replace("\t", "\\t")
        yadon.WriteRowToTable(settings.settingstablename, variable, [value, str(authlevel)])
        try:
            if float(value) % 1 == 0:
                value = int(value)
            else:
                value = float(value)
        except ValueError:
            value = value.replace("\\n", "\n").replace("\\t", "\t")
        setattr(settings, variable, value)
        return value
    
    #remove a setting and updates the settings file accordingly
    #returns None if setting doesn't exist or level is lower than setting's level (defaults to max user level if not specified or setting is in settings.py), returns the old value if it did
    def removesetting(self, variable, authlevel=settings.defaultuserlevel):
        try:
            value = getattr(settings, variable)
        except AttributeError:
            return
        
        try:
            settinglevel = int(yadon.ReadRowFromTable(settings.settingstablename, variable)[1])
        except (IndexError, ValueError):
            settinglevel = settings.maxuserlevel
        if settinglevel > authlevel:
            return
        
        yadon.RemoveRowFromTable(settings.settingstablename, variable)
        delattr(settings, variable)
        return value
    
    #Updates a user's authority level. Returns 0 if successful, -1 if not (i.e. level wasn't an integer)
    def updateuserlevel(self, userid, level):
        #level should be an integer
        try:
            int(level)
        except ValueError:
            return -1
        
        yadon.WriteRowToTable(settings.userlevelstablename, userid, [str(level)])
        return 0
    
    def getuserlevel(self, userid):
        try:
            return int(yadon.ReadRowFromTable(settings.userlevelstablename, str(userid))[0])
        except (TypeError, IndexError, ValueError):
            return settings.defaultuserlevel
    
    #Run a command as if it was triggered by a Discord message
    async def runcommand(self, command, message=None, params=[]):
        try:
            function = self.commands[command][0]
            return await function(message, params)
        except (KeyError, IndexError):
            return
    
    def checkchannelcooldown(self, channelid):
        #calculate time since the last bot output on the given channel
        try:
            TD = datetime.datetime.now() - self.lastmessageDT[channelid]
            return ((TD.microseconds / 1000) + (TD.seconds * 1000) < settings.channelcooldown)
        except KeyError:
            return False
    
    def checkusercooldown(self, userid):
        userlevel = self.getuserlevel(userid)
        userlastoutputs = self.getuserlastoutputs(userid)
        if len(userlastoutputs) > 0:
            #calculate time since the last bot output from the user
            TD = datetime.datetime.now() - userlastoutputs[-1].created_at
            usercooldown = 0
            while usercooldown == 0 and userlevel >= 0:
                try:
                    usercooldown = getattr(settings, "usercooldown_{}".format(userlevel))
                except AttributeError:
                    userlevel -= 1
            return ((TD.microseconds / 1000) + (TD.seconds * 1000) < usercooldown)
        else:
            return False

    def getuserlastoutputs(self, userid):
        try:
            userlastoutputs = self.outputhistory[userid]
        except KeyError:
            self.outputhistory[userid] = []
            userlastoutputs = self.outputhistory[userid]
        return userlastoutputs

#######
#SETUP#
#######
#background task is run every set interval while bot is running
async def backgroundtask():
    await client.wait_until_ready()
    while not client.is_closed():
        if client.user.bot and client.user.name != settings.botname:
            await client.user.edit(username=settings.botname)
        if callable(settings.backgroundtask):
            client.loop.create_task(settings.backgroundtask())
        await asyncio.sleep(settings.backgroundtaskinterval)

@client.event
async def on_ready():
    print("Bot online!")
    print("Name: {}".format(client.user.name))
    print("ID: {}".format(client.user.id))
    await koduckinstance.runcommand("updatecommands")

##############
#INPUT OUTPUT#
##############
#This is where messages come in, whether a command is triggered or not is checked, and parameters are parsed.
#Note: don't use " \ or = as command prefix or param delim, since they are used in parsing, it'll mess stuff up.
@client.event
async def on_message(message):
    #ignore bot messages
    if message.author.bot:
        return
    
    #ignore messages not in whitelist
    if koduckinstance.getuserlevel(message.author.id) < settings.maxuserlevel and (settings.restrictedmode == "true" and message.channel.id not in yadon.ReadTable(settings.channelwhitelisttablename).keys()) and not message.channel.is_private:
        return
    
    try:
        #PARSE COMMAND AND PARAMS
        context, args, kwargs = {"koduck": koduckinstance, "message": message, "command": ""}, [], {}
        
        #PREFIX COMMANDS
        if message.content.startswith(settings.commandprefix):
            context["commandline"] = message.content[len(settings.commandprefix):]
            try:
                context["command"] = context["commandline"][0:context["commandline"].index(" ")].lower()
                context["paramline"] = context["commandline"][context["commandline"].index(" ")+1:]
                context["params"] = []
            except ValueError:
                context["command"] = context["commandline"].lower()
                context["paramline"] = ""
                context["params"] = []
            
            #Reset context if not a valid command
            if context["command"] not in koduckinstance.prefixcommands:
                koduckinstance.log(message, logresult=settings.message_unknowncommand)
                context, args, kwargs = {"message": message, "command": ""}, [], {}
            
            #Else parse params
            else:
                #Things within quotes should escape parsing
                #Find things within quotes, replace them with a number (which shouldn't have param delim)
                temp = context["paramline"]
                quotes = []
                quotematches = list(re.finditer(r'(["])(?:\\.|[^\\])*?\1', temp))
                quotematches.reverse()
                for quote in quotematches:
                    start = quote.span()[0]
                    end = quote.span()[1]
                    temp = temp[0:start] + '"{}"'.format(len(quotes)) + temp[end:]
                    quotes.append(quote.group())
                
                parsedparams = temp.split(settings.paramdelim)
                
                counter = len(quotes) - 1
                #Put the quotes back in, without the quote marks themselves
                def putquotesback(text, quotes, counter):
                    ans = text
                    while text.find('"{}"'.format(counter)) != -1 and counter >= 0:
                        ans = ans.replace('"{}"'.format(counter), quotes[counter][1:-1], 1)
                        counter -= 1
                    return (ans, counter)
                for param in parsedparams:
                    #Find equal signs that aren't preceded by backslash
                    equals = [match.span()[0] for match in filter(lambda match: match.span()[0] == 0 or param[match.span()[0]-1] != "\\", re.finditer(r'=', param))]
                    if len(equals) > 0:
                        keyword, counter = putquotesback(param[:param.index("=")].strip(), quotes, counter)
                        value, counter = putquotesback(param[param.index("=")+1:].strip(), quotes, counter)
                        kwargs[keyword] = value
                        context["params"].append("{}={}".format(keyword, value))
                    else:
                        arg, counter = putquotesback(param.strip(), quotes, counter)
                        args.append(arg)
                        context["params"].append(arg)
        
        #MATCH COMMANDS
        if not context["command"]:
            for commandname in koduckinstance.matchcommands:
                if commandname == message.content.lower():
                    context["command"] = commandname
                    break
        
        #CONTAIN COMMANDS
        if not context["command"]:
            for commandname in koduckinstance.containcommands:
                if commandname in message.content.lower():
                    context["command"] = commandname
                    break
        
        if not context["command"]:
            return
        
        #CHECK PERMISSIONS OF USER
        userlevel = koduckinstance.getuserlevel(message.author.id)
        if userlevel < koduckinstance.commands[context["command"]][2]:
            koduckinstance.log(message, settings.message_restrictedaccess)
            #notify user of restricted access only if it's a prefix command
            if context["command"] in koduckinstance.prefixcommands:
                await koduckinstance.sendmessage(message, sendcontent=settings.message_restrictedaccess)
            return
        
        koduckinstance.log(message)
        #RUN THE COMMAND
        function = koduckinstance.commands[context["command"]][0]
        result = await function(context, *args, **kwargs)
        if isinstance(result, str):
            koduckinstance.log(None, result)
    
    except Exception as e:
        exc_type, exc_value, _ = sys.exc_info()
        errormessage = "{}: {}".format(exc_type.__name__, exc_value)
        traceback.print_exc()
        await koduckinstance.sendmessage(message, sendcontent=settings.message_somethingbroke + "\n``{}``".format(errormessage))
        koduckinstance.log(message, logresult=settings.message_unhandlederror.format(errormessage))