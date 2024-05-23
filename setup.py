from cx_Freeze import setup, Executable

setup(
    name="DiscordBotControl",
    version="1.0",
    description="Your application description",
    executables=[Executable("discordbot.py", base="Win32GUI", icon="discordroboticon.ico")],
)
