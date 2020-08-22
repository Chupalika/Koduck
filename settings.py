#BOT FILES
commandstablename = "tables/commands"
settingstablename = "tables/settings"
userlevelstablename = "tables/userlevels"
logfile = "log.txt"
formattedlogfile = "formattedlog.txt"

#BOT SETTINGS
botname = "Koduck"
token = ""
commandprefix = "/"
paramdelim = ","
defaultuserlevel = 1
maxuserlevel = 3
logformat = "%t\t%s\t%c\t%U\t%m\t%r"
channelcooldown = 1000
ignorecdlevel = 2
usercooldown_0 = 60000
usercooldown_1 = 3000
outputhistorysize = 10
backgroundtask = None
backgroundtaskinterval = 10

restrictedmode = "false"
channelwhitelisttablename = "tables/channelwhitelist"

#MESSAGES
message_somethingbroke = "Something broke"
message_unknowncommand = "Command not recognized"
message_unhandlederror = "Unhandled error ({})"
message_resulttoolong = "Sorry, the result was too long to output ({}/{} characters)"
message_embedtoolong = "Sorry, the embed was too long to output ({} {}/{} characters)"
message_embedemptyfield = "The output embed was invalid ({} can't be empty)"
message_cooldownactive = "Cooldown active"
message_restrictedaccess = "You do not have permission to use this command"