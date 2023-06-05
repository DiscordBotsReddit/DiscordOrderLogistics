import os

import aiosqlite
import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
from dotenv import load_dotenv

load_dotenv()
DB = "shop_orders.db"


intents = discord.Intents.default()

bot = commands.Bot(command_prefix="$", intents=intents)


@bot.event
async def on_ready():
    if not os.path.exists(DB):
        with open(DB, "w") as f:
            f.write("")
            print("Created DB file.")
    async with aiosqlite.connect(DB) as db:
        async with db.cursor() as cur:
            await cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                shop_orders(
                    id INTEGER PRIMARY KEY AUTOINCREMENT
                    , user_id INTEGER NOT NULL
                    , guild_id INTEGER NOT NULL
                    , order_items TEXT NOT NULL
                    , price REAL NOT NULL
                    , completed INTEGER NOT NULL DEFAULT 0
                    , canceled INTEGER NOT NULL DEFAULT 0
                    );
                """
            )
            await db.commit()
    # await bot.tree.sync()
    print("Logged in as", bot.user)


class OrderBtns(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Complete", style=discord.ButtonStyle.green)  # type: ignore
    async def completed_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        order_id = int(interaction.message.content.split("\n")[1].split("`")[1])
        async with aiosqlite.connect(DB) as db:
            async with db.cursor() as cur:
                await cur.execute(
                    f"UPDATE shop_orders SET completed=1 WHERE id={order_id};"
                )
                await db.commit()
        for child in self.children:
            if type(child) == discord.ui.Button and child.label != "Find Open Orders":
                child.disabled = True
            if type(child) == discord.ui.Button and child.label == "Complete":
                child.style = discord.ButtonStyle.grey
                child.label = "Completed"
        await interaction.response.edit_message(
            view=self,
            content=interaction.message.content.replace("added", "**completed**"),
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)  # type: ignore
    async def canceled_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        order_id = int(interaction.message.content.split("\n")[1].split("`")[1])
        async with aiosqlite.connect(DB) as db:
            async with db.cursor() as cur:
                await cur.execute(
                    f"UPDATE shop_orders SET canceled=1 WHERE id={order_id};"
                )
                await db.commit()
        for child in self.children:
            if type(child) == discord.ui.Button and child.label != "Find Open Orders":
                child.disabled = True
            if type(child) == discord.ui.Button and child.label == "Cancel":
                child.style = discord.ButtonStyle.grey
                child.label = "Canceled"
        await interaction.response.edit_message(
            view=self,
            content=interaction.message.content.replace("added", "**canceled**"),
        )

    @discord.ui.button(label="Find Open Orders", style=discord.ButtonStyle.blurple)  # type: ignore
    async def lookuporders_callback(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user = await interaction.guild.fetch_member(
            int(interaction.message.content.split("\n")[2].split("@")[1].split(">")[0])
        )
        orders_embed = discord.Embed(
            title=f"{user.display_name}'s Open Orders",
            color=discord.Color.random(),
        )
        async with aiosqlite.connect(DB) as db:
            async with db.cursor() as cur:
                open_orders = await cur.execute(
                    f"SELECT id,order_items,price FROM shop_orders WHERE user_id={user.id} AND guild_id={interaction.guild.id} AND completed=0 AND canceled=0;"
                )
                open_orders = await open_orders.fetchall()
        orders_embed.set_footer(text=f"Total open orders: {len(open_orders)}")
        try:
            orders_embed.set_thumbnail(url=user.avatar.url)
        except:
            pass
        if len(open_orders) > 25:
            open_orders = open_orders[:25]
        for order in open_orders:
            orders_embed.add_field(
                name=f"ID {order[0]}:  {order[1]}",
                value=f"Price:  {order[2]}",
                inline=False,
            )
        await interaction.response.send_message(embed=orders_embed, ephemeral=True)


class OrderForm(Modal, title="New Order"):
    user_id = TextInput(
        label="Discord UserID", placeholder='Right click the name and pick "Copy ID"'
    )
    order_items = TextInput(label="Order Items")
    price = TextInput(label="Amount Charged", placeholder="3.50")

    async def on_submit(self, interaction: discord.Interaction):
        error = False
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            int(self.user_id.value)
        except:
            error = True
            await interaction.followup.send(
                f"The `Discord UserID` must be an integer.\nYou entered: `{self.user_id.value}`.",
                ephemeral=True,
            )
        try:
            float(self.price.value)
        except:
            error = True
            await interaction.followup.send(
                f"The `Amount Charged` must be a number.\nYou entered: `{self.price.value}`.",
                ephemeral=True,
            )
        try:
            member = await interaction.guild.fetch_member(int(self.user_id.value))
        except:
            error = True
            await interaction.followup.send(
                f"The `Discord UserID` you entered does not return a valid member in this server.",
                ephemeral=True,
            )
        if error is False:
            fulfill_btn = OrderBtns()
            async with aiosqlite.connect(DB) as db:
                async with db.cursor() as cur:
                    order = await cur.execute(
                        f"INSERT INTO shop_orders(user_id,guild_id,order_items,price) VALUES({int(self.user_id.value)}, {interaction.guild.id}, '{self.order_items.value}', {round(float(self.price.value), 2)});"
                    )
                    await db.commit()
            await interaction.followup.send(
                f"Order added!\nOrder ID: `{order.lastrowid}`\nUSER: {member.mention}\nORDER_ITEMS: `{self.order_items.value}`\nAMOUNT CHARGED: `{round(float(self.price.value), 2)}`",
                ephemeral=True,
                view=fulfill_btn,
            )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.followup.send(
            f"**>> ERROR <<**\n`{error}`\nPlease Try again.", ephemeral=True
        )


@bot.tree.command(name="new_order", description="Open a new order")
async def new_order(interaction: discord.Interaction):
    await interaction.response.send_modal(OrderForm())


@bot.tree.command(name="lookup", description="Find all open orders by user")
async def lookup_orders(interaction: discord.Interaction, user: discord.Member):
    orders_embed = discord.Embed(
        title=f"{user.display_name}'s Open Orders", color=discord.Color.random()
    )
    try:
        orders_embed.set_thumbnail(url=user.avatar.url)
    except:
        pass
    async with aiosqlite.connect(DB) as db:
        async with db.cursor() as cur:
            open_orders = await cur.execute(
                f"SELECT id,order_items,price FROM shop_orders WHERE user_id={user.id} AND guild_id={interaction.guild.id} AND completed=0 AND canceled=0;"
            )
            open_orders = await open_orders.fetchall()
    orders_embed.set_footer(text=f"Total open orders: {len(open_orders)}")
    if len(open_orders) > 25:
        open_orders = open_orders[:25]
    for order in open_orders:
        orders_embed.add_field(
            name=f"ID {order[0]}:  {order[1]}",
            value=f"Price:  {order[2]}",
            inline=False,
        )
    await interaction.response.send_message(embed=orders_embed, ephemeral=True)


bot.run(os.environ["TOKEN"])
