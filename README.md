# DiscordOrderLogistics
The bot to manage your orders inside Discord!

## Current Commands
- /new_order
  - Opens the new order window where you enter the user's ID, ordered items, and price charged.
  - To get a user's ID, go to your `User Settings`, scroll down to `Advanced` and enable `Developer Mode`.  Go back into your server, right click the user and, at the bottom, select `Copy ID`.
  - Once the order is created, a message will be sent in the channel the command is ran in with the information you entered as well as buttons to `Complete` or `Cancel` the order and to `Lookup Open Orders` for that user.
- /lookup USER
  - Finds all the open (not marked complete or canceled) orders for that user.   
