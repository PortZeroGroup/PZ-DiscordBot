import re
import discord
from typing import Tuple, Dict, Union, List
from discord.ext.commands import Converter, RoleConverter
from redbot.core import commands, Config, checks
from redbot.core.commands import Context
from redbot.core.utils.common_filters import filter_mass_mentions, filter_urls, filter_various_mentions, normalize_smartquotes
from redbot.core.utils.chat_formatting import humanize_list, escape
from redbot.core.utils.menus import menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate
from datetime import datetime
import functools


def compose(*functions):
    return functools.reduce(lambda f, g: lambda x: f(g(x)), functions, lambda x: x)


def sanitize_input(input: str):
    fn = compose(
        filter_mass_mentions,
        filter_urls,
        filter_various_mentions,
        normalize_smartquotes,
    )
    return escape(fn(input))


class RoleHierarchyConverter(commands.RoleConverter):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.me.guild_permissions.manage_roles:
            raise commands.BadArgument(
                "I require manage roles permission to use this command.")
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise
        if ctx.author.id == ctx.guild.owner.id:
            return role
        else:
            if role >= ctx.me.top_role:
                raise commands.BadArgument(
                    "That role is higher than my highest role in the discord hierarchy.")
            if role.position >= ctx.author.top_role.position:
                raise commands.BadArgument(
                    "That role is higher than your own in the discord hierarchy.")
        return role


class RoleEmojiConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Tuple[discord.Role, str]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            role, emoji = arg_split
        except Exception:
            raise commands.BadArgument(
                "Role Emoji must be a role followed by an "
                "emoji separated by either `;`, `,`, `|`, or `-`."
            )
        custom_emoji = None
        try:
            custom_emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.strip())
        except commands.BadArgument:
            pass

        if not custom_emoji:
            try:
                await ctx.message.add_reaction(str(emoji.strip()))
                custom_emoji = emoji
            except discord.errors.HTTPException:
                raise commands.BadArgument(
                    "That does not look like a valid emoji.")

        try:
            role = await RoleHierarchyConverter().convert(ctx, role.strip())
        except commands.BadArgument:
            raise
        return role, custom_emoji


class RoleCategoryConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Tuple[str, discord.Role, str]:
        arg_split = re.split(r";|,|\||-", argument)
        try:
            role, category = arg_split
        except Exception:
            raise commands.BadArgument(
                "Category Role must be a role followed by a category separated by either `;`, `,`, `|`, or `-`."
            )

        category = sanitize_input(category)

        try:
            role = await RoleHierarchyConverter().convert(ctx, role.strip())
        except commands.BadArgument:
            raise
        return role, category


class RoleReact(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self, identifier=28495814093949, force_registration=True)
        default_global = {
            'version': '0.0.0',
        }
        default_guild = {
            'reaction_message_ref': {},
            'roles': {},
            'categories': {
                '': {
                    'roles': {},
                },
            },
        }
        default_role = {}
        default_member = {}
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)
        self.config.register_role(**default_role)
        self.config.register_member(**default_member)

    @commands.group()
    @commands.admin_or_permissions(manage_roles=True)
    async def roles(self, ctx: Context):
        """
        Role reaction commands.
        """
        pass

    @commands.group()
    @commands.admin_or_permissions(manage_roles=True)
    async def categories(self, ctx: Context):
        """
        Role reaction commands.
        """
        pass

    def get_guild_config(self, ctx: Context):
        return self.config.guild(ctx.guild)

    async def get_emoji(self, ctx: Context, message: discord.Message, emoji: str) -> str:
        custom_emoji = None
        try:
            custom_emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.strip())
        except commands.BadArgument:
            pass
        if not custom_emoji:
            try:
                await message.add_reaction(emoji)
            except discord.errors.HTTPException:
                raise BadArgument("That does not look like a valid emoji.")
        else:
            await message.add_reaction(emoji)
        return custom_emoji

    async def get_role(self, ctx: Context, role: str):
        return await RoleConverter().convert(ctx, role)

    async def handle_menu_message_update(self, ctx: Context, message: discord.Message) -> Tuple[List[Tuple[discord.Role, str]], List[Tuple[str, str]]]:
        known_roles = []
        unknown_roles = []
        for line in message.content.split('\n'):
            if not line.startswith('>') and len(line) > 3:
                parts = line.split()
                if len(parts) >= 2:
                    emoji, role = parts[:2]
                    try:
                        emoji = await self.get_emoji(ctx, message, emoji)
                        try:
                            role = await self.get_role(ctx, role)
                            known_roles.append((role, emoji))
                        except commands.BadArgument:
                            unknown_roles.append((role, emoji))
                    except Exception as err:
                        pass
        return known_roles, unknown_roles

    @roles.command(name='add')
    async def add_roles(self, ctx: Context, *role_emoji: RoleEmojiConverter):
        async with self.get_guild_config(ctx).roles() as roles:
            for role, emoji in role_emoji:
                roles[role.name] = {
                    'emoji': emoji,
                }
        # Add to blank category
        async with self.get_guild_config(ctx).categories() as categories:
            for role, emoji in role_emoji:
                categories['']['roles'][role.name] = True
        await ctx.send('Added {}'.format(humanize_list([role.name for role, emoji in role_emoji])))

    @roles.command(name='print')
    async def print_roles(self, ctx: Context):
        async with self.get_guild_config(ctx).roles() as all_roles:
            msg = ''
            for role in sorted(all_roles):
                msg += '> {} - {}\n'.format(all_roles[role]['emoji'], role)
            if msg == '':
                msg = 'No roles configured'
            await ctx.send(msg)

    @roles.command(name='remove')
    async def remove_roles(self, ctx: Context, *roles_to_remove: RoleConverter):
        async with self.get_guild_config(ctx).roles() as roles:
            for role in list(roles_to_remove):
                roles.pop(role.name)

        async with self.get_guild_config(ctx).categories() as categories:
            for category_name in list(categories):
                for role in list(roles_to_remove):
                    try:
                        categories[category_name]['roles'].pop(role)
                        if category_name != '' and len(categories[category_name]) == 0:
                            categories.pop(category_name)
                    except KeyError:
                        pass

    @categories.command()
    async def assign(self, ctx: Context, *role_categories: RoleCategoryConverter):
        msg = ''
        async with self.get_guild_config(ctx).categories() as categories:
            # Remove old categories
            for category_name in list(categories):
                for role, _ in role_categories:
                    try:
                        removed = categories[category_name]['roles'].pop(
                            role.name)
                        if removed and category_name != '':
                            msg += '> - Removed `{}` (category) from `{}` (role)\n'.format(
                                category_name, role.name)
                    except KeyError:
                        pass

            # Clean up empty categories
            for category_name in list(categories):
                if len(categories[category_name]['roles']) == 0:
                    try:
                        categories.pop(category_name)
                    except KeyError:
                        pass

            # Add new categories
            for role, category_name in role_categories:
                try:
                    category = categories[category_name]
                except KeyError:
                    category = {
                        'roles': {},
                    }
                category['roles'][role.name] = True
                categories[category_name] = category
                if category_name != '':
                    msg += '> + Added `{}` (category) to `{}` (role)\n'.format(
                        category_name, role.name)
        await ctx.send(msg)

    @categories.command()
    async def unassign(self, ctx: Context, *roles: RoleConverter):
        async with self.get_guild_config(ctx).categories() as categories:
            for category_name in list(categories):
                # Remove role from categories that have it
                for role in roles:
                    if category_name != '':
                        try:
                            removed = categories[category_name]['roles'].pop(
                                role.name)
                        except KeyError:
                            pass
                    # Add to blank category
                    categories['']['roles'][role.name] = True
                # Clean up empty categories
                if category_name != '' and len(categories[category_name]['roles']) == 0:
                    try:
                        categories.pop(category_name)
                    except KeyError:
                        pass
        role_text = humanize_list(['`{}`'.format(role.name) for role in roles])
        await ctx.send('Removed all categories from roles {}'.format(role_text))

    @categories.command(name='print')
    async def print_categories(self, ctx: Context):
        async with self.get_guild_config(ctx).categories() as categories:
            async with self.get_guild_config(ctx).roles() as roles:
                msg = ''
                for category_name in sorted(list(categories)):
                    if category_name != '':
                        msg += '> \n> **{}**\n'.format(category_name)
                    else:
                        msg += '> \n> **Uncategorized**\n'
                    for role in categories[category_name]['roles']:
                        try:
                            emoji = roles[role]['emoji']
                            msg += '> {} - {}\n'.format(roles[role]['emoji'], role)
                        except KeyError:
                            msg += '> {} (no reaction set)\n'.format(role)
                if msg == '':
                    msg = 'There are no categories configured'
                await ctx.send(msg)

    @categories.command(name='remove')
    async def remove_categories(self, ctx: Context, *category_names: str):
        async with self.get_guild_config(ctx).categories() as categories:
            for category_name in category_names:
                try:
                    categories.pop(category_name)
                except KeyError:
                    pass
            await ctx.send('Removed {}'.format(humanize_list(category_names)))

    @roles.command(name='setmenu')
    async def setmenu_roles(self, ctx: Context, message: discord.Message):
        async with self.get_guild_config(ctx).reaction_message_ref() as reaction_message_ref:
            reaction_message_ref['message_id'] = message.id
            reaction_message_ref['channel_id'] = message.channel.id
            async with self.get_guild_config(ctx).roles() as roles:
                for role in roles:
                    await message.add_reaction(roles[role]['emoji'])
            await ctx.send(message.jump_url)

    @roles.group(name='link')
    async def link_roles(self, ctx: Context):
        async with self.get_guild_config(ctx).reaction_message_ref() as reaction_message_ref:
            url = 'https://discord.com/channels/{}/{}/{}'.format(
                ctx.guild.id, reaction_message_ref['channel_id'], reaction_message_ref['message_id'])
            await ctx.send('Self-assign roles here: {}'.format(url))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print('Raw reaction add:\n{}'.format(str(payload)))
        if payload.guild_id is None:
            print('Raw reaction add - no guild id')
            return
        guild_config = self.config.guild_from_id(payload.guild_id)

        async with guild_config.reaction_message_ref() as reaction_message_ref:
            if payload.channel_id != reaction_message_ref['channel_id'] or payload.message_id != reaction_message_ref['message_id']:
                print('Raw reaction add - no match')
                return

        print('Raw reaction add - checking roles')
        async with guild_config.roles() as roles:
            for role_name in roles:
                role_emoji = roles[role_name]['emoji']
                print('Raw reaction add - does {} match {} ({})?'.format(payload.emoji, role_emoji, role_name))
                if str(payload.emoji) == str(role_emoji):
                    print('Raw reaction add - emoji matches {}'.format(role_name))
                    user_id = payload.user_id
                    channel = self.bot.get_channel(payload.channel_id)
                    member = channel.guild.get_member(payload.user_id)
                    message = await channel.fetch_message(payload.message_id)
                    ctx = await self.bot.get_context(message)
                    role = await RoleConverter().convert(ctx, role_name)
                    await member.add_roles(role)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        print('Raw reaction add:\n{}'.format(str(payload)))
        if payload.guild_id is None:
            print('Raw reaction add - no guild id')
            return
        guild_config = self.config.guild_from_id(payload.guild_id)

        async with guild_config.reaction_message_ref() as reaction_message_ref:
            if payload.channel_id != reaction_message_ref['channel_id'] or payload.message_id != reaction_message_ref['message_id']:
                print('Raw reaction add - no match')
                return

        print('Raw reaction add - checking roles')
        async with guild_config.roles() as roles:
            for role_name in roles:
                role_emoji = roles[role_name]['emoji']
                print('Raw reaction add - does {} match {} ({})?'.format(payload.emoji, role_emoji, role_name))
                if str(payload.emoji) == str(role_emoji):
                    print('Raw reaction add - emoji matches {}'.format(role_name))
                    user_id = payload.user_id
                    channel = self.bot.get_channel(payload.channel_id)
                    member = channel.guild.get_member(payload.user_id)
                    message = await channel.fetch_message(payload.message_id)
                    ctx = await self.bot.get_context(message)
                    role = await RoleConverter().convert(ctx, role_name)
                    await member.remove_roles(role)