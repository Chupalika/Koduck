import discord
import asyncio
import sys, os, random
import koduck, yadon
import settings

#Background task is run every set interval while bot is running (by default every 10 seconds)
async def backgroundtask():
    pass
settings.backgroundtask = backgroundtask

##################
# BASIC COMMANDS #
##################
#Be careful not to leave out this command or else a restart might be needed for any updates to commands
async def updatecommands(context, *args, **kwargs):
    tableitems = yadon.ReadTable(settings.commandstablename).items()
    if tableitems is not None:
        koduck.clearcommands()
        for name, details in tableitems:
            try:
                koduck.addcommand(name, globals()[details[0]], details[1], int(details[2]))
            except (KeyError, IndexError, ValueError):
                pass

async def shutdown(context, *args, **kwargs):
    return await koduck.client.logout()

async def sendmessage(context, *args, **kwargs):
    if len(args) < 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_sendmessage_noparam)
    channelid = args[0]
    THEchannel = koduck.client.get_channel(channelid)
    THEmessagecontent = context["paramline"][context["paramline"].index(settings.paramdelim)+1:].strip()
    return await koduck.sendmessage(context["message"], sendchannel=THEchannel, sendcontent=THEmessagecontent, ignorecd=True)

async def changestatus(context, *args, **kwargs):
    if len(args) < 1:
        return await koduck.client.change_presence(game=discord.Game(name=""))
    else:
        return await koduck.client.change_presence(game=discord.Game(name=context["paramline"]))

async def updatesettings(context, *args, **kwargs):
    koduck.updatesettings()
    return

#note: discord server prevents any user, including bots, from changing usernames more than twice per hour
#bot name is updated in the background task, so it won't update immediately
async def updatesetting(context, *args, **kwargs):
    if len(args) < 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_updatesetting_noparam)
    variable = args[0]
    value = context["paramline"][context["paramline"].index(settings.paramdelim)+1:].strip()
    result = koduck.updatesetting(variable, value, koduck.getuserlevel(context["message"].author.id))
    if result is not None:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_updatesetting_success.format(variable, result, value))
    else:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_updatesetting_failed)

async def addsetting(context, *args, **kwargs):
    if len(args) < 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_updatesetting_noparam)
    variable = args[0]
    value = context["paramline"][context["paramline"].index(settings.paramdelim)+1:].strip()
    result = koduck.addsetting(variable, value, koduck.getuserlevel(context["message"].author.id))
    if result is not None:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addsetting_success)
    else:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addsetting_failed)

async def removesetting(context, *args, **kwargs):
    if len(args) < 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removesetting_noparam)
    result = koduck.removesetting(args[0], koduck.getuserlevel(context["message"].author.id))
    if result is not None:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removesetting_success)
    else:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removesetting_failed)

async def admin(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context["message"].raw_mentions) != 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_nomentioneduser)
    
    userid = context["message"].raw_mentions[0]
    userlevel = koduck.getuserlevel(userid)
    
    #already an admin
    if userlevel == 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addadmin_failed.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 2)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addadmin_success.format(userid, settings.botname))

async def unadmin(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context["message"].raw_mentions) != 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_nomentioneduser)
    
    userid = context["message"].raw_mentions[0]
    userlevel = koduck.getuserlevel(userid)
    
    #not an admin
    if userlevel < 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removeadmin_failed.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 1)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removeadmin_success.format(userid, settings.botname))

#Searches through the past settings.purgesearchlimit number of messages in this channel and deletes given number of bot messages
async def purge(context, *args, **kwargs):
    try:
        limit = int(args[0])
    except (IndexError, ValueError):
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_purge_invalidparam)
    
    counter = 0
    async for message in koduck.client.logs_from(context["message"].channel, limit=settings.purgesearchlimit):
        if counter >= limit:
            break
        if message.author.id == koduck.client.user.id:
            await koduck.client.delete_message(message)
            counter += 1

async def restrictuser(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context["message"].raw_mentions) != 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_nomentioneduser)
    
    userid = context["message"].raw_mentions[0]
    userlevel = koduck.getuserlevel(userid)
    
    #already restricted
    if userlevel == 0:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_restrict_failed)
    #don't restrict high level users
    elif userlevel >= 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_restrict_failed2.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 0)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_restrict_success.format(userid, settings.botname))

async def unrestrictuser(context, *args, **kwargs):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(context["message"].raw_mentions) != 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_nomentioneduser)
    
    userid = context["message"].raw_mentions[0]
    userlevel = koduck.getuserlevel(userid)
    
    if userlevel != 0:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_unrestrict_failed)
    else:
        koduck.updateuserlevel(userid, 1)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_unrestrict_success.format(userid, settings.botname))

#When someone says a trigger message, respond with a custom response!
async def customresponse(context, *args, **kwargs):
    response = yadon.ReadRowFromTable(settings.customresponsestablename, context["command"])
    if response:
        return await koduck.sendmessage(context["message"], sendcontent=response[0])

async def addresponse(context, *args, **kwargs):
    if len(args) < 2:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addresponse_noparam)
    trigger = args[0].lower()
    response = args[1]
    result = yadon.AppendRowToTable(settings.customresponsestablename, trigger, [response])
    if result == -1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addresponse_failed)
    else:
        yadon.WriteRowToTable(settings.commandstablename, trigger, ["customresponse", "match", "1"])
        koduck.addcommand(trigger, customresponse, "match", 1)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_addresponse_success.format(trigger, response))

async def removeresponse(context, *args, **kwargs):
    if len(args) < 1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removeresponse_noparam)
    trigger = args[0].lower()
    result = yadon.RemoveRowFromTable(settings.customresponsestablename, trigger)
    if result == -1:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removeresponse_failed.format(trigger))
    else:
        yadon.RemoveRowFromTable(settings.commandstablename, trigger)
        koduck.removecommand(trigger)
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_removeresponse_success)

async def oops(context, *args, **kwargs):
    try:
        THEmessage = koduck.outputhistory[context["message"].author.id].pop()
    except (KeyError, IndexError):
        return settings.message_oops_failed
    try:
        await koduck.client.delete_message(THEmessage)
        return settings.message_oops_success
    except discord.errors.NotFound:
        return await oops(context, *args, **kwargs)

async def commands(context, *args, **kwargs):
    #filter out the commands that the user doesn't have permission to run
    #group the commands by function, multiple aliases for one function will be put in parentheses to indicate that fact to the user
    currentlevel = koduck.getuserlevel(context["message"].author.id)
    availablecommands = {}
    for commandname, command in koduck.commands.items():
        if command[2] <= currentlevel and command[1] == "prefix":
            try:
                availablecommands[command[0]].append(commandname)
            except KeyError:
                availablecommands[command[0]] = [commandname]
    output = ""
    for function, commandnames in availablecommands.items():
        if len(commandnames) > 1:
            output += "({}), ".format(", ".join(commandnames))
        else:
            output += "{}, ".format(commandnames[0])
    output = output[:-2]
    return await koduck.sendmessage(context["message"], sendcontent=output)

async def help(context, *args, **kwargs):
    messagename = args[0] if len(args) > 0 else ""
    helpmessage = gethelpmessage(messagename)
    if not helpmessage:
        helpmessage = gethelpmessage("unknowncommand")
    if helpmessage:
        return await koduck.sendmessage(context["message"], sendcontent=helpmessage)

async def userinfo(context, *args, **kwargs):
    #if there is no mentioned user, use the message sender instead
    if len(context["message"].raw_mentions) == 0:
        if context["message"].server is None:
            user = context["message"].author
        else:
            user = context["message"].server.get_member(context["message"].author.id)
            if user is None:
                user = context["message"].author
    elif len(context["message"].raw_mentions) == 1:
        if context["message"].server is None:
            user = await koduck.client.get_user_info(context["message"].raw_mentions[0])
        else:
            user = context["message"].server.get_member(context["message"].raw_mentions[0])
            if user is None:
                user = await koduck.client.get_user_info(context["message"].raw_mentions[0])
    else:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_nomentioneduser2)
    
    username = user.name
    discr = user.discriminator
    avatar = user.avatar_url
    creationdate = user.created_at
    
    #these properties only appear in Member object (subclass of User) which is only available from Servers
    if isinstance(user, discord.Member):
        game = user.game
        joindate = user.joined_at
        color = user.color
        if game is None:
            embed = discord.Embed(title="{}#{}".format(username, discr), description=str(user.status), color=color)
        else:
            embed = discord.Embed(title="{}#{}".format(username, discr), description="Playing {}".format(game.name), color=color)
        embed.add_field(name="Account creation date", value=creationdate.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="Server join date", value=joindate.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.set_thumbnail(url=avatar)
        return await koduck.sendmessage(context["message"], sendembed=embed)
    else:
        embed = discord.Embed(title="{}#{}".format(username, discr), description="Account creation date: {}".format(creationdate.strftime("%Y-%m-%d %H:%M:%S UTC")))
        embed.set_thumbnail(url=avatar)
        return await koduck.sendmessage(context["message"], sendembed=embed)

async def roll(context, *args, **kwargs):
    if len(args) > 0:
        try:
            max = int(args[0])
        except ValueError:
            max = settings.rolldefaultmax
    else:
        max = settings.rolldefaultmax
    
    if max >= 0:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_rollresult.format(context["message"].author.mention, random.randint(0, max)))
    else:
        return await koduck.sendmessage(context["message"], sendcontent=settings.message_rollresult.format(context["message"].author.mention, random.randint(max, 0)))

def gethelpmessage(messagename):
    if messagename:
        helpmessage = yadon.ReadRowFromTable(settings.helpmessagestable, "message_help_" + messagename)
    #Default message if no parameter is given
    else:
        helpmessage = yadon.ReadRowFromTable(settings.helpmessagestable, "message_help")
    
    #Use {cp} for command prefix and {pd} for parameter delimiter
    if helpmessage:
        return helpmessage[0].replace("{cp}", settings.commandprefix).replace("{pd}", settings.paramdelim).replace("\\n", "\n").replace("\\t", "\t")
    else:
        return None

def setup():
    koduck.addcommand("updatecommands", updatecommands, "prefix", 3)

setup()
koduck.client.run(settings.token)