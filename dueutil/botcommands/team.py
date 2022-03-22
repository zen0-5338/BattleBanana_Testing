import discord
import jsonpickle

import generalconfig as gconf
from .. import commands, util, dbconn
from ..game import players, teams

NOT_IN_TEAM = "You are not in a team!"
ALREADY_IN_TEAM = "You are already in a team!"


def in_a_team(player: players.Player):
    """
    Checks if the player is in a team.
    :param player: The player to check.
    :return: True if the player is in a team, False otherwise.
    """
    if player.team is None:
        return False

    team = teams.find_team(player.team)
    if team is None:
        player.team = None
        player.save()
    
    return player.team is not None

@commands.command(args_pattern="SS?B?C?")
async def createteam(ctx, name, description="This is a new and awesome team!", is_open=True, level=1, **details):
    """
    [CMD_KEY]createteam name (description) (recruiting) (Minimum Level)

    Name: Team's name
    Description: Describe your team
    recruiting: Accepts people?
    Min level: Lowest level for someone to join the team

    Very basic.. isn't it?
    """
    owner = details["author"]

    if in_a_team(owner):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if len(name) > 32 or len(name) < 4:
        raise util.BattleBananaException(ctx.channel, "Team Name must be between 4 and 32 characters")

    if len(description) > 1024:
        raise util.BattleBananaException(ctx.channel, "Description must not exceed 1024 characters!")

    if name != util.filter_string(name):
        raise util.BattleBananaException(ctx.channel, "Invalid team name!")

    if teams.find_team(name.lower()):
        raise util.BattleBananaException(ctx.channel, "That team already exists!")

    if level < 1:
        raise util.BattleBananaException(ctx.channel, "Minimum level cannot be under 1!")

    teams.Team(owner, name, description, level, is_open)

    await util.reply(ctx, f"Successfully created **{name}**!")


@commands.command(args_pattern=None)
async def deleteteam(ctx, **details):
    """
    [CMD_KEY]deleteteam

    Deletes your team
    """
    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(member.team)
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You need to be the owner to delete the team!")

    name = team.name
    team.delete()

    await util.reply(ctx, f"**{name}** successfully deleted!")


@commands.command(args_pattern="P", aliases=["ti"])
async def teaminvite(ctx, member, **details):
    """
    [CMD_KEY]teaminvite (player)

    NOTE: You cannot invite a player that is already in a team!
    """

    inviter = details["author"]

    if inviter == member:
        raise util.BattleBananaException(ctx.channel, "You cannot invite yourself!")

    if not in_a_team(inviter):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if in_a_team(member):
        raise util.BattleBananaException(ctx.channel, "This player is already in a team!")

    team = teams.find_team(inviter.team)
    if not team.is_admin(inviter):
        raise util.BattleBananaException(ctx.channel, "You do not have permissions to send invites!")

    if inviter.team in member.team_invites:
        raise util.BattleBananaException(ctx.channel, "This player has already been invited to join your team!")

    member.team_invites.append(inviter.team)
    member.save()
    await util.reply(ctx, ":thumbsup: Invite has been sent to **%s**!" % member.name)


@commands.command(args_pattern=None, aliases=["si"])
async def showinvites(ctx, **details):
    """
    [CMD_KEY]showinvites

    Display any team invites that you have received!
    """

    member = details["author"]

    invites_embed = discord.Embed(title="Displaying your team invites!", description="You were invited to join these teams!",
                          type="rich", colour=gconf.DUE_COLOUR)
    if len(member.team_invites) == 0:
        invites_embed.add_field(name="No invites!", value="You do not have invites!")
    else:
        for id in member.team_invites:
            team = teams.find_team(id)
            if team:
                owner = players.find_player(team.owner)
                invites_embed.add_field(name=team.name,
                                value="**Owner:** %s (%s)\n**Average level:** %s\n**Members:** %s\n**Required Level:** %s\n**Recruiting:** %s"
                                      % (owner.name, owner.id, team.avgLevel, len(team.members), team.level,
                                         ("Yes" if team.open else "No")),
                                inline=False)
            else:
                member.team_invites.remove(id)

    member.save()
    await util.reply(ctx, embed=invites_embed)


@commands.command(args_pattern="T", aliases=["ai"])
async def acceptinvite(ctx, team, **details):
    """
    [CMD_KEY]acceptinvite (team)

    Accept a team invite.
    """

    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if team.id not in member.team_invites:
        raise util.BattleBananaException(ctx.channel, "Invite not found!")

    team.add_member(ctx, member)

    await util.reply(ctx, "Successfully joined **%s**!" % team)


@commands.command(args_pattern="T", aliases=["di"])
async def declineinvite(ctx, team, **details):
    """
    [CMD_KEY]declineinvite (team index)

    Decline a team invite cuz you're too good for it.
    """

    member = details["author"]

    if team.id not in member.team_invites:
        raise util.BattleBananaException(ctx.channel, "Team not found!")

    member.team_invites.remove(team.id)
    member.save()
    await util.reply(ctx, "Successfully deleted **%s** invite!" % team.name)


@commands.command(args_pattern=None, aliases=["mt"])
async def myteam(ctx, **details):
    """
    [CMD_KEY]myteam

    Display your team!

    Couldn't find 
    a longer description 
    for this than 
    that :shrug:
    So now it is longer
    """

    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(member.team)

    pendings = ""
    members = ""
    admins = ""
    for id in team.admins:
        if id != team.owner:
            admins += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name, str(id))

    if len(pendings) == 0:
        pendings = "Nobody is pending!"
    if len(members) == 0:
        members = "There is no member to display!"
    if len(admins) == 0:
        admins = "There is no admin to display!"

    owner = players.find_player(team.owner)

    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich",
                               colour=gconf.DUE_COLOUR)
    team_embed.add_field(name="Name", value=team.name, inline=False)
    team_embed.add_field(name="Description", value=team.description, inline=False)
    team_embed.add_field(name="Owner", value=f"{owner.name} ({owner.id})", inline=False)
    team_embed.add_field(name="Member Count", value=len(team.members), inline=False)
    team_embed.add_field(name="Average level", value=team.avgLevel, inline=False)
    team_embed.add_field(name="Required level", value=team.level, inline=False)
    team_embed.add_field(name="Recruiting", value="Yes" if team.open else "No", inline=False)
    team_embed.add_field(name="Admins:", value=admins)
    team_embed.add_field(name="Members:", value=members)
    team_embed.add_field(name="Pendings:", value=pendings)

    await util.reply(ctx, embed=team_embed)


@commands.command(args_pattern="P", aliases=["pu"])
async def promoteuser(ctx, user, **details):
    """
    [CMD_KEY]promoteuser (player)

    Promote a member of your team to admin.
    An admin can manage the team: Invite players, kick players, etc.

    NOTE: Only the owner can promote members!
    """

    member = details["author"]

    if member == user:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote yourself!")

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if user.team != member.team:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    team = teams.find_team(member.team)
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to promote users! (You must be owner!)")

    team.add_admin(ctx, user)
    await util.reply(ctx, "Successfully promoted **%s** as an **admin**!" % (user.get_name_possession_clean()))


@commands.command(args_pattern="P", aliases=["du"])
async def demoteuser(ctx, user, **details):
    """
    [CMD_KEY]demoteuser (player)

    Demote an admin of your team to a normal member.

    NOTE: Only the owner can demote members!
    """

    member = details["author"]

    if member == user:
        raise util.BattleBananaException(ctx.channel, "There is no reason to demote yourself!")

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if user.team != member.team:
        raise util.BattleBananaException(ctx.channel, "This user is not in your team!")

    team = teams.find_team(member.team)
    if member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You are not allowed to demote users! (You must be the owner!)")

    if user.id not in team.admins:
        raise util.BattleBananaException(ctx.channel, "This player is already a member!")

    team.remove_admin(ctx, user)
    await util.reply(ctx, "**%s** has been demoted to **Member**" % (user.name))


@commands.command(args_pattern="P", aliases=["tk"])
async def teamkick(ctx, user, **details):
    """
    [CMD_KEY]teamkick (player)

    Allows you to kick a member from your team.
    You don't like him? Get rid of him!

    NOTE: Team owner & admin are able to kick users from their team!
        Admins cannot kick other admins or the owner.
        Only the owner can kick an admin.
    """

    member = details["author"]

    if member == user:
        raise util.BattleBananaException(ctx.channel, "There is no reason to kick yourself!")

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if not in_a_team(user) or user.team != member.team:
        raise util.BattleBananaException(ctx.channel, "This player is not in your team!")

    team = teams.find_team(member.team)
    if not team.is_admin(member):
        raise util.BattleBananaException(ctx.channel, "You must be an admin to use this command!")

    if team.is_admin(user) and member.id != team.owner:
        raise util.BattleBananaException(ctx.channel, "You must be the owner to kick this player from the team!")

    team.kick(ctx, user)
    await util.reply(ctx, "Successfully kicked **%s** from your team, adios amigos!" % user.name)


@commands.command(args_pattern=None, aliases=["lt"])
async def leaveteam(ctx, **details):
    """
    [CMD_KEY]leaveteam

    You don't want to be in your team anymore?

    Congrats you found the right command to leave! 

    :D
    """
    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel,
                                         "You are not in any team.. You can't leave the void.. *My void!* :smiling_imp:")

    team = teams.find_team(member.team)
    if team.owner == member.id:
        raise util.BattleBananaException(ctx.channel,
                                         "You cannot leave this team! If you want to disband it, use `%sdeleteteam`" % (
                                             details["cmd_key"]))

    team.kick(ctx, member)
    await util.reply(ctx, "You successfully left your team!")


@commands.command(args_pattern="C?", aliases=["st", "teams"])
async def showteams(ctx, page=1, **details):
    """
    [CMD_KEY]showteams (page)

    Show all existant teams
    
    Obviously they are existant...
    how would it even display something not existant?
    """

    page_size = 5
    page = page - 1
    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")

    teams_embed = discord.Embed(title="There is the teams lists", description="Display all existant teams", type="rich",
                               colour=gconf.DUE_COLOUR)

    db_teams = list(dbconn.get_collection_for_object(teams.Team).find())
    top = (page * page_size + page_size)
    if page != 0 and page * 5 >= len(db_teams):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    limit = top if top < len(db_teams) else len(db_teams)
    for index in range(page * page_size, limit, 1):
        # TODO: Make this team loading more efficient
        loaded_team = jsonpickle.decode(db_teams[index - 1]["data"])
        if loaded_team.id in teams.teams:
            team = teams.teams[loaded_team.id]
        else:
            teams.teams[loaded_team.id] = util.load_and_update(teams.REFERENCE_TEAM, loaded_team)
            team = teams.teams[loaded_team.id]
        try:
            owner = players.find_player(team.owner)
            teams_embed.add_field(name=team.name,
                                 value="Owner: **%s** (%s)\nDescription: **%s**\nMembers: **%s**\nAverage Level: **%s**\nRequired Level: **%s**\nRecruiting: **%s**" % (
                                     owner.name, owner.id, team.description, len(team.members), team.avgLevel,
                                     team.level,
                                     ("Yes" if team.open else "No")), inline=False)
        except:
            continue

    limit = page_size * page + page_size < len(db_teams)
    teams_embed.set_footer(text="%s" % (("Do %sshowteams %d for the next page!" % (
        details["cmd_key"], page + 2)) if limit else "That's all the teams!"))
    await util.reply(ctx, embed=teams_embed)


@commands.command(args_pattern="T", aliases=["sti"])
async def showteaminfo(ctx, team, **_):
    """
    [CMD_KEY]showteaminfo (team)

    Display information about selected team - Owner, Admins, Members, team name, number of members, etc
    """

    team_embed = discord.Embed(title="Team Information", description="Displaying team information", type="rich",
                               colour=gconf.DUE_COLOUR)
    pendings = ""
    members = ""
    admins = ""
    for id in team.admins:
        if id != team.owner:
            admins += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.members:
        if id not in team.admins and id != team.owner:
            members += "%s (%s)\n" % (players.find_player(id).name, str(id))
    for id in team.pendings:
        if id in team.members:
            team.pendings.remove(id)
        else:
            pendings += "%s (%s)\n" % (players.find_player(id).name, str(id))

    team_embed.add_field(name="Name", value=team.name, inline=False)
    team_embed.add_field(name="Description", value=team.description, inline=False)
    team_embed.add_field(name="Owner", value="%s (%s)" % (players.find_player(team.owner).name, team.owner),
                         inline=False)
    team_embed.add_field(name="Member Count", value=len(team.members), inline=False)
    team_embed.add_field(name="Average level", value=team.avgLevel, inline=False)
    team_embed.add_field(name="Required level", value=team.level, inline=False)
    team_embed.add_field(name="Recruiting", value="Yes" if team.open else "No", inline=False)

    if len(pendings) == 0:
        pendings = "Nobody is pending!"
    if len(members) == 0:
        members = "There is no member to display!"
    if len(admins) == 0:
        admins = "There is no admin to display!"

    team_embed.add_field(name="Admins:", value=admins)
    team_embed.add_field(name="Members:", value=members)
    team_embed.add_field(name="Pendings:", value=pendings)

    await util.reply(ctx, embed=team_embed)


@commands.command(args_pattern="T", aliases=["jt"])
async def jointeam(ctx, team, **details):
    """
    [CMD_KEY]jointeam (team)
    
    Join a team or puts you on pending list
    """

    member = details["author"]

    if in_a_team(member):
        raise util.BattleBananaException(ctx.channel, ALREADY_IN_TEAM)

    if (team.open or team.id in member.team_invites) and member.level >= team.level:
        team.add_member(ctx, member)
        await util.reply(ctx, "You successfully joined **%s**!" % (team.name))

    elif member.level < team.level:
        raise util.BattleBananaException(ctx.channel,
                                         "You must be level %s or higher to join this team!" % (team.level))

    else:
        team.add_pending(ctx, member)
        await util.reply(ctx, "You have been added to **%s** pending list!" % (team.get_name_possession()))


@commands.command(args_pattern='S*', aliases=["ts"])
@commands.extras.dict_command(
    optional={"min level/minimum level/level": "I", "open/recruiting": "B", "description/desc": "S"})
async def editteam(ctx, updates, **details):
    """
    [CMD_KEY]editteam param (value)+

    You can change as many properties as you want at the same time

    Properties:
        __level__, __recruiting__, __description__

    Example usage:

        [CMD_KEY]editteam "minimum level" 10

        [CMD_KEY]editteam recruiting true
    """

    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(member.team)
    if not team.is_admin(member):
        raise util.BattleBananaException(ctx.channel, "You need to be an admin to change settings!")

    for prop, value in updates.items():
        if prop in ("minimum level", "level", "min level"):
            if value >= 1:
                team.level = value
            else:
                updates[prop] = "Must be at least 1!"
        elif prop in ("open", "recruiting"):
            team.open = value
        elif prop in ("description"):
            if len(value) > 1024:
                updates[prop] = "Can't be longer than 1024 characters"
            else:
                team.description = value
        else:
            continue

    if len(updates) == 0:
        await util.reply(ctx, "You need to provide a valid property for the team!")
    else:
        team.save()
        result = "**Settings changed:**\n"

        for prop, value in updates.items():
            result += ("``%s`` → %s\n" % (prop, value))

        await util.reply(ctx, result)


@commands.command(args_pattern="I?", aliases=["pendings", "stp"])
async def showteampendings(ctx, page=1, **details):
    """
    [CMD_KEY]showteampendings (page)

    Display a list of pending users for your team!
    """

    member = details["author"]
    page_size = 10
    page = page - 1

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if page < 0:
        raise util.BattleBananaException(ctx.channel, "Page not found!")

    team = teams.find_team(member.team)
    top = ((page_size * page) + page_size) if ((page_size * page) + page_size < len(team.pendings)) else len(team.pendings)
    if page != 0 and page * page_size >= len(team.pendings):
        raise util.BattleBananaException(ctx.channel, "Page not found")

    pendings_embed = discord.Embed(title="**%s** pendings list" % (team.name),
                                   description="Displaying user pending to your team", type="rich",
                                   colour=gconf.DUE_COLOUR)
    for index in range((page_size * page), top, 1):
        pending_id = team.pendings[index]
        member = players.find_player(pending_id)
        pendings_embed.add_field(name=index, value="%s (%s)" % (member.name, member.id), inline=False)

    if len(pendings_embed.fields) == 0:
        pendings_embed.add_field(name="The list is empty!", value="Nobody is pending to your team!")

    limit = (5 * page) + 5 < len(team.pendings)
    pendings_embed.set_footer(text="%s" % (("Do %sshowpendings %d for the next page!" % (
        details["cmd_key"], page + 2)) if limit else "That's all the pendings!"))

    await util.reply(ctx, embed=pendings_embed)


@commands.command(args_pattern="P", aliases=["ap"])
async def acceptpending(ctx, user, **details):
    """
    [CMD_KEY]acceptpending (index)

    Accept a user pending to your team.
    """

    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    if in_a_team(user):
        raise util.BattleBananaException(ctx.channel, "This player found his favorite team already!")

    team = teams.find_team(member.team)
    if not team.is_pending(user):
        raise util.BattleBananaException(ctx.channel, "Pending user not found!")

    team.add_member(ctx, user)
    await util.reply(ctx, "Accepted **%s** in your team!" % (user.name))


@commands.command(args_pattern="P", aliases=["dp"])
async def declinepending(ctx, user, **details):
    """
    [CMD_KEY]declinepending (index)

    Decline a user pending to your team.
    """

    member = details["author"]

    if not in_a_team(member):
        raise util.BattleBananaException(ctx.channel, NOT_IN_TEAM)

    team = teams.find_team(member.team)
    if not team.is_pending(user):
        raise util.BattleBananaException(ctx.channel, "Pending user not found!")

    team.remove_pending(ctx, user)

    await util.reply(ctx, "Removed **%s** from pendings!" % (user.name))
