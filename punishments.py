import discord
from discord.ext import commands
from discord import app_commands
import mysql.connector
from datetime import datetime, timedelta


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
db = mysql.connector.connect(
    host="localhost",
    user="REDACTED_GITHUB",
    password="REDACTED_GITHUB",
    database="REDACTED_GITHUB"
)
cursor = db.cursor()


ALLOWED_ROLES = {1285762541490016456, 1274153694686085223}  # AOJ in Court and NYPD High Rank in PD
def has_allowed_role(interaction: discord.Interaction):
    user_roles = {role.id for role in interaction.user.roles}
    return bool(ALLOWED_ROLES & user_roles)



# Punishment Logging
def log_punishment(hr_id, user_id, reason, action, expiration_time, proof, note):
    query = """
        INSERT INTO punishments (hr_id, user_id, reason, action, expiration_time, proof, note, logged_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (hr_id, user_id, reason, action, expiration_time, proof, note, datetime.utcnow()))
    db.commit()


def view_punishments(user_id):
    cursor.execute("SELECT * FROM punishments WHERE user_id = %s", (user_id,))
    return cursor.fetchall()



@bot.tree.command(name="punish", description="Log a punishment for a user.")
@app_commands.describe(
    user="The user being punished.",
    reason="The reason for the punishment.",
    action="The type of punishment (e.g., Strike, Warning).",
    duration="Duration of the punishment (e.g., 7d, 30m, Perm).",
    proof="Link to proof of the punishment.",
    note="Optional note about the punishment."
)
async def punish(interaction: discord.Interaction, user: discord.Member, reason: str, action: str, duration: str, proof: str, note: str = None):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    expiration_time = None
    if duration.lower() != "perm":
        duration_minutes = int(duration.replace("d", "")) * 1440 if "d" in duration else int(duration.replace("m", ""))
        expiration_time = datetime.utcnow() + timedelta(minutes=duration_minutes)

    log_punishment(interaction.user.id, user.id, reason, action, expiration_time, proof, note)

    # Punishment Messages (PD and log)
    dm_message = (
        f"You have been punished.\n"
        f"Reason: {reason}\n"
        f"Action: {action}\n"
        f"Duration: {duration}\n\n"
        f"Make a ticket if you want more details or to appeal this punishment."
    )
    await user.send(dm_message)


    channel_message = (
        f"**HR**: {interaction.user.mention}\n"
        f"**User**: {user.mention}\n"
        f"**Reason**: {reason}\n"
        f"**Action**: {action}\n"
        f"**Duration**: {duration}\n"
        f"**Proof**: {proof}\n"
        f"**Note**: {note or 'None'}"
    )
    await interaction.response.send_message(channel_message)


@bot.tree.command(name="viewpunishments", description="View punishments for a specific user.")
@app_commands.describe(user="The user whose punishments you want to view.")
async def viewpunishments(interaction: discord.Interaction, user: discord.Member):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    punishments = view_punishments(user.id)
    if punishments:
        response = "\n".join([
            f"**HR**: <@{row[1]}>\n"
            f"**User**: <@{row[2]}>\n"
            f"**Reason**: {row[3]}\n"
            f"**Action**: {row[4]}\n"
            f"**Expires**: {row[5] or 'Permanent'}\n"
            f"**Proof**: {row[6]}\n"
            f"**Note**: {row[7] or 'None'}\n"
            for row in punishments
        ])
    else:
        response = "No punishments found."
    await interaction.response.send_message(response)

# View your own punishments (Anyone can use)
@bot.tree.command(name="punishments", description="View your own punishments.")
async def punishments(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    punishments = view_punishments(user_id)
    if not punishments:
        await interaction.response.send_message("You have no active punishments.", ephemeral=True)
        return

    response = "**Your Punishments:**\n"
    for punishment in punishments:
        expiration_time = punishment[5]
        try:
            if isinstance(expiration_time, str):
                expiration_time = datetime.strptime(expiration_time, "%Y-%m-%d %H:%M:%S")
            now = datetime.utcnow()
            remaining = expiration_time - now
            if remaining.total_seconds() > 0:
                time_left = str(timedelta(seconds=remaining.total_seconds()))
            else:
                time_left = "Expired"
        except Exception as e:
            time_left = f"Error parsing expiration time: {e}"

        response += (
            f"**HR**: <@{punishment[1]}>\n"
            f"**Reason**: {punishment[3]}\n"
            f"**Action**: {punishment[4]}\n"
            f"**Expires**: {time_left}\n"
            f"**Proof**: {punishment[6]}\n"
            f"**Note**: {punishment[7] or 'None'}\n\n"
        )

    await interaction.response.send_message(response, ephemeral=True)


@bot.tree.command(name="clearpunishments", description="Clear all punishments for a specific user.")
@app_commands.describe(user="The user whose punishments you want to clear.")
async def clearpunishments(interaction: discord.Interaction, user: discord.Member):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    cursor.execute("DELETE FROM punishments WHERE user_id = %s", (str(user.id),))
    db.commit()
    await interaction.response.send_message(f"All punishments for {user.mention} have been cleared.", ephemeral=True)

# DEBUG MAKE SURE THIS SHOWS EVERYTIME YOU REBOOT THE BOT OR SOMETHING IS WRONG
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user} and commands are synced globally.")
    for command in bot.tree.get_commands():
        print(f"Registered command: {command.name}")

bot.run("REDACTED_GITHUB")
