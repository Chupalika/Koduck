import asyncio
import sys, os
import koduck
import settings

#Background task is run every set interval while bot is running (by default every 10 seconds)
def backgroundtask():
    okay = "okay"
settings.backgroundtask = backgroundtask

#COMMANDS
async def shutdown(message, params):
    await koduck.client.logout()
    return

async def sendmessage(message, params):
    if len(params) < 2:
        return await koduck.sendmessage(message, sendcontent=settings.message_sendmessage_noparam)
    channelid = params[0]
    THEchannel = koduck.client.get_channel(channelid)
    THEmessagecontent = settings.paramdelim.join(params[1:]).replace(channelid, "")
    return await koduck.sendmessage(message, sendchannel=THEchannel, sendcontent=THEmessagecontent)

#note: discord server prevents any user, including bots, from changing usernames more than twice per hour
async def changeusername(message, params):
    if len(params) == 0:
        return await koduck.sendmessage(message, sendcontent=settings.message_changeusername_noparam)
    return await koduck.client.edit_profile(username=settings.paramdelim.join(params))

async def changestatus(message, params):
    if len(params) == 0:
        await koduck.client.change_presence(game=discord.Game(name=""))
    else:
        await koduck.client.change_presence(game=discord.Game(name=settings.paramdelim.join(params)))
    return

async def updateuserlevels(message, params):
    koduck.updateuserlevels()
    return

async def updatesettings(message, params):
    koduck.updatesettings()
    return

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
        return await koduck.sendmessage(message, sendcontent=settings.message_help)
    #Try to retrieve the help message for the queried command
    else:
        querycommand = params[0]
        if querycommand not in koduck.commands.keys():
            return await koduck.sendmessage(message, sendcontent=settings.message_help_unknowncommand)
        else:
            try:
                return await koduck.sendmessage(message, sendcontent=getattr(settings, "message_help_{}".format(querycommand)))
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

def setup():
    koduck.addcommand("shutdown", shutdown, 3)
    koduck.addcommand("sendmessage", sendmessage, 3)
    koduck.addcommand("changeusername", changeusername, 3)
    koduck.addcommand("changestatus", changestatus, 3)
    koduck.addcommand("updateuserlevels", updateuserlevels, 3)
    koduck.addcommand("updatesettings", updatesettings, 3)
    koduck.addcommand("admin", admin, 3)
    koduck.addcommand("unadmin", unadmin, 3)
    koduck.addcommand("restrictuser", restrictuser, 2)
    koduck.addcommand("unrestrictuser", unrestrictuser, 2)
    koduck.addcommand("oops", oops, 1)
    koduck.addcommand("commands", commands, 1)
    koduck.addcommand("help", help, 1)
    koduck.addcommand("userinfo", userinfo, 1)

setup()
koduck.client.run(settings.token)