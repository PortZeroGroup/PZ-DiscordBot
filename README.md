# PZ-DiscordBot
The Public repo for the PZ discord bot

## Getting Started

This bot is built with Python, using the Red framework. Here are the docs for [Red](https://docs.discord.red/en/stable/index.html).

At a high level, bot commands and features are implemented as plugins (Red calls them "cogs" so we'll call them that from here on).

To get started contributing to PZ Bot:
1. Join the [Port Zero discord server](https://discord.gg/jmHWZA4vg5) and join the project (#discord-bot-dev channel)
2. Request to contribute on Github, and team leaders or admins may give you permissions
3. Fork this repository
4. Create your own discord bot application for testing locally. We recommend using an easily identifiable name, like `pzbot_<your_name>`. [Red Docs](https://docs.discord.red/en/stable/bot_application_guide.html)
5. Set up Red bot with your application token and prefix. [Linux](https://docs.discord.red/en/stable/install_linux_mac.html#installing-red) / [Mac](https://docs.discord.red/en/stable/install_linux_mac.html#installing-red) / [Windows](https://docs.discord.red/en/stable/install_windows.html)
6. Assign yourself to a task on our [project board](https://github.com/PortZeroGroup/PZ-DiscordBot/projects/1) or [issue tracker](https://github.com/PortZeroGroup/PZ-DiscordBot/issues)
7. Code and test locally. (**Do not check in your credentials**)
8. Submit a Pull Request from your fork back into [PZ-DiscordBot](https://github.com/PortZeroGroup/PZ-DiscordBot). (**Do not check in your credentials**)

## Deployment

**Summary**
We will automatically deploy release branches ([TODO](https://github.com/PortZeroGroup/PZ-DiscordBot/issues/8)) when commits are made. To do this safely, changes will merge into a "staging" branch ([TODO](https://github.com/PortZeroGroup/PZ-DiscordBot/issues/7)) which is then immediately deployed to our testing environment. After some time, when automated or manual testing is done, the testing branch will merge into the release branch and the production bot will automatically redeploy.
