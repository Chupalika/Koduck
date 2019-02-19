import asyncio
import sys, os, random
import koduck
import settings

#Background task is run every set interval while bot is running (by default every 10 seconds)
def backgroundtask():
    pass
settings.backgroundtask = backgroundtask

##################
# BASIC COMMANDS #
##################
async def shutdown(message, params):
    return await koduck.client.logout()

async def sendmessage(message, params):
    if len(params) < 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_sendmessage_noparam)
    channelid = params[0]
    THEchannel = koduck.client.get_channel(channelid)
    THEmessagecontent = settings.paramdelim.join(params[1:]).replace(channelid, "")
    return await koduck.sendmessage(message, sendchannel=THEchannel, sendcontent=THEmessagecontent, ignorecd=True)

async def changestatus(message, params):
    if len(params) < 1:
        return await koduck.client.change_presence(game=koduck.discord.Game(name=""))
    else:
        return await koduck.client.change_presence(game=koduck.discord.Game(name=settings.paramdelim.join(params)))

async def updateuserlevels(message, params):
    koduck.updateuserlevels()
    return

async def updatesettings(message, params):
    koduck.updatesettings()
    return

#note: discord server prevents any user, including bots, from changing usernames more than twice per hour
#bot name is updated in the background task, so it won't update immediately
async def updatesetting(message, params):
    if len(params) < 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_updatesetting_noparam)
    variable = params[0]
    value = settings.paramdelim.join(params[1:])
    result = koduck.updatesetting(variable, value)
    if result is not None:
        return await koduck.sendmessage(message, sendcontent=settings.message_updatesetting_success.format(variable, result, value))
    else:
        return await koduck.sendmessage(message, sendcontent=settings.message_updatesetting_failed)

async def addsetting(message, params):
    if len(params) < 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_updatesetting_noparam)
    variable = params[0]
    value = settings.paramdelim.join(params[1:])
    result = koduck.addsetting(variable, value)
    if result is not None:
        return await koduck.sendmessage(message, sendcontent=settings.message_addsetting_success)
    else:
        return await koduck.sendmessage(message, sendcontent=settings.message_addsetting_failed)

async def admin(message, params):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(message.mentions) != 1:
        return await koduck.sendmessage(message, sendcontent=settings.message_nomentioneduser)
    
    userid = message.mentions[0].id
    currentlevel = koduck.getuserlevel(userid)
    
    #already an admin
    if currentlevel == 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_addadmin_failed.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 2)
        return await koduck.sendmessage(message, sendcontent=settings.message_addadmin_success.format(userid, settings.botname))

async def unadmin(message, params):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(message.mentions) != 1:
        return await koduck.sendmessage(message, sendcontent=settings.message_nomentioneduser)
    
    userid = message.mentions[0].id
    currentlevel = koduck.getuserlevel(userid)
    
    #not an admin
    if currentlevel < 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_removeadmin_failed.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 1)
        return await koduck.sendmessage(message, sendcontent=settings.message_removeadmin_success.format(userid, settings.botname))

async def purge(message, params):
    try:
        limit = min(int(params[0]), settings.purgesearchlimit)
    except (IndexError, ValueError):
        return await koduck.sendmessage(message, sendcontent=settings.message_purge_invalidparam)
    #search the past "limit" number of messages and delete only the bot's messages
    async for message2 in koduck.client.logs_from(message.channel, limit=limit):
        if message2.author.id == koduck.client.user.id:
            await koduck.client.delete_message(message2)

async def restrictuser(message, params):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(message.mentions) != 1:
        return await koduck.sendmessage(message, sendcontent=settings.message_nomentioneduser)
    
    userid = message.mentions[0].id
    currentlevel = koduck.getuserlevel(userid)
    
    #already restricted
    if currentlevel == 0:
        return await koduck.sendmessage(message, sendcontent=settings.message_restrict_failed)
    #don't restrict high level users
    elif currentlevel > 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_restrict_failed2.format(settings.botname))
    else:
        koduck.updateuserlevel(userid, 0)
        return await koduck.sendmessage(message, sendcontent=settings.message_restrict_success.format(userid, settings.botname))

async def unrestrictuser(message, params):
    #need exactly one mentioned user (the order in the mentioned list is unreliable)
    if len(message.mentions) != 1:
        return await koduck.sendmessage(message, sendcontent=settings.message_nomentioneduser)
    
    userid = message.mentions[0].id
    currentlevel = koduck.getuserlevel(userid)
    
    if currentlevel != 0:
        return await koduck.sendmessage(message, sendcontent=settings.message_unrestrict_failed)
    else:
        koduck.updateuserlevel(userid, 1)
        return await koduck.sendmessage(message, sendcontent=settings.message_unrestrict_success.format(userid, settings.botname))

async def oops(message, params):
    try:
        THEmessage = koduck.userlastoutput[message.author.id]
        await koduck.client.delete_message(THEmessage)
        return settings.message_oops_success
    except (KeyError, koduck.discord.errors.NotFound):
        return settings.message_oops_failed
    return

async def commands(message, params):
    #filter out the commands that the user doesn't have permission to run
    currentlevel = koduck.getuserlevel(message.author.id)
    availablecommands = []
    for commandname in koduck.commands.keys():
        command = koduck.commands[commandname]
        if command[1] <= currentlevel:
            availablecommands.append(commandname)
    return await koduck.sendmessage(message, sendcontent=", ".join(availablecommands))

async def help(message, params):
    #Default message if no parameter is given
    if len(params) == 0:
        return await koduck.sendmessage(message, sendcontent=settings.message_help.replace("{cp}", settings.commandprefix).replace("{pd}", settings.paramdelim))
    #Try to retrieve the help message for the query
    else:
        querycommand = params[0]
        try:
            #Use {cp} for command prefix and {pd} for parameter delimiter
            return await koduck.sendmessage(message, sendcontent=getattr(settings, "message_help_{}".format(querycommand)).replace("{cp}", settings.commandprefix).replace("{pd}", settings.paramdelim))
        except AttributeError:
            return await koduck.sendmessage(message, sendcontent=settings.message_help_unknowncommand)

async def userinfo(message, params):
    #if there is no mentioned user (apparently they have to be in the server to be considered "mentioned"), use the message sender instead
    if message.server is None:
        user = message.author
    elif len(message.mentions) == 0:
        user = message.server.get_member(message.author.id)
    elif len(message.mentions) == 1:
        user = message.server.get_member(message.mentions[0].id)
    else:
        return await koduck.sendmessage(message, sendcontent=settings.message_nomentioneduser2)
    
    username = user.name
    discr = user.discriminator
    avatar = user.avatar_url
    creationdate = user.created_at
    
    #these properties only appear in Member object (subclass of User) which is only available from Servers
    if message.server is not None:
        game = user.game
        joindate = user.joined_at
        color = user.color
        if game is None:
            embed = koduck.discord.Embed(title="{}#{}".format(username, discr), description=str(user.status), color=color)
        else:
            embed = koduck.discord.Embed(title="{}#{}".format(username, discr), description="Playing {}".format(game.name), color=color)
        embed.add_field(name="Account creation date", value=creationdate.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.add_field(name="Server join date", value=joindate.strftime("%Y-%m-%d %H:%M:%S UTC"), inline=False)
        embed.set_thumbnail(url=avatar)
        return await koduck.sendmessage(message, sendembed=embed)
    else:
        embed = koduck.discord.Embed(title="{}#{}".format(username, discr), description="Account creation date: {}".format(creationdate.strftime("%Y-%m-%d %H:%M:%S UTC")))
        embed.set_thumbnail(url=avatar)
        return await koduck.sendmessage(message, sendembed=embed)

async def roll(message, params):
    if len(params) >= 1:
        try:
            max = int(params[0])
        except ValueError:
            max = settings.rolldefaultmax
    else:
        max = settings.rolldefaultmax
    
    if max >= 0:
        return await koduck.sendmessage(message, sendcontent=settings.message_rollresult.format(message.author.mention, random.randint(0, max)))
    else:
        return await koduck.sendmessage(message, sendcontent=settings.message_rollresult.format(message.author.mention, random.randint(max, 0)))

def setup():
    koduck.addcommand("shutdown", shutdown, 3)
    koduck.addcommand("sendmessage", sendmessage, 3)
    koduck.addcommand("changestatus", changestatus, 3)
    koduck.addcommand("updateuserlevels", updateuserlevels, 3)
    koduck.addcommand("updatesettings", updatesettings, 3)
    koduck.addcommand("updatesetting", updatesetting, 2)
    koduck.addcommand("addsetting", addsetting, 2)
    koduck.addcommand("admin", admin, 3)
    koduck.addcommand("unadmin", unadmin, 3)
    koduck.addcommand("purge", purge, 3)
    koduck.addcommand("restrictuser", restrictuser, 2)
    koduck.addcommand("unrestrictuser", unrestrictuser, 2)
    koduck.addcommand("oops", oops, 1)
    koduck.addcommand("commands", commands, 1)
    koduck.addcommand("help", help, 1)
    koduck.addcommand("userinfo", userinfo, 1)
    koduck.addcommand("roll", roll, 1)

setup()
koduck.client.run(settings.token)