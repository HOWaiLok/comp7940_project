from telegram import Update
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, 
                          CallbackContext)
# import configparser
import logging
import redis
from chatbot_ChatGPT import HKBU_ChatGPT

import os

TEL_ACCESS_TOKEN = os.environ["TEL_ACCESS_TOKEN"]
HOST = os.environ["HOST"]
REDISPORT = os.environ["REDISPORT"]
PASSWORD = os.environ["PASSWORD"]
BASICURL = os.environ["BASICURL"]
MODELNAME = os.environ["MODELNAME"]
APIVERSION =os.environ["APIVERSION"]
GPT_ACCESS_TOKEN = os.environ["GPT_ACCESS_TOKEN"]

global redis1

def main():

    # config = configparser.ConfigParser()
    # config.read('config.ini')
    updater = Updater(token=(TEL_ACCESS_TOKEN), use_context=True)
    dispatcher = updater.dispatcher
    global redis1
    redis1 = redis.Redis(host=(HOST), password=(PASSWORD), port=(REDISPORT))
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    # Here are the list of dispatchers.
    global chatgpt
    chatgpt = HKBU_ChatGPT()
    chatgpt_handler = MessageHandler(Filters.text & (~Filters.command), equiped_chatgpt)
    dispatcher.add_handler(chatgpt_handler)

    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("list", list))
    dispatcher.add_handler(CommandHandler("recommend", recommend))
    dispatcher.add_handler(CommandHandler("append", append))
    dispatcher.add_handler(CommandHandler("read", read))

    # turn on the chatbot
    updater.start_polling()
    updater.idle()

def equiped_chatgpt(update, context): 
    global chatgpt
    reply_message = chatgpt.submit(update.message.text)
    logging.info("Update: " + str(update))
    logging.info("context: " + str(context))
    context.bot.send_message(telegram_id=update.effective_chat.id, text=reply_message)

# Here are the handler functions.
    
# The string printed in "/help command" 
help_str = 'Welcome to FilmBuffDB_bot! The functionalities are described as follows.\n1. /list: a list of genres and actor/actress for a film recommendation\n2. /recommend: input some keyword(s) and provide you a film recommendation.\n3. /append film_title: add the film to your film list database.\n4. /read film_title: read the film description based on a film title.'
# Print a description of the functionalities of the chatbot
def help(update: Update, context: CallbackContext):

    update.message.reply_text(help_str)

# list of gneres and actor/actress for film recommendation
def list(update, context):

    # the prompt for ChatGPT provide a list of genres and actor/actress for film suggestion
    genres = chatgpt.submit("Please give me at least 7 movie genres. Answer in the following format: genre1, genre2, ... Don't provide any additional sentence for ouput.")
    actors = chatgpt.submit("Please give me at least 10 film famous actor/actress names. Answer in the following format: name1, name2, ... Don't provide any additional sentence for ouput.")
    
    if genres.startswith('Error') or actors.startswith('Error'): # failure for ChatGPT to provide a list of genres and actor/actress as response 
        update.message.reply_text('Failed to provide a list of genres and actor/actress.')
    else:
        genres = genres.lower().split(',')
        actors = actors.lower().split(',')

        genre_decomposition = 'Genres - ' + ' '.join([f"{index + 1}. {genre.strip()}" for index, genre in enumerate(genres)])
        actor_decomposition = 'Actors/Actresses - ' + ' '.join([f"{index + 1}. {actor.strip()}" for index, actor in enumerate(actors)])
        
        update.message.reply_text(genre_decomposition + '\n' + actor_decomposition)

# generate a film recommendation based on the keyword inputted
def recommend(update: Update, context: CallbackContext):

    global chatgpt

    if len(context.args) > 0:
        keywords = ", ".join(context.args)
        msg = f"Please write a film suggestion based on the following keywords: {keywords}"
        suggestion = chatgpt.submit(msg)
        update.message.reply_text(suggestion)
    else:
        update.message.reply_text("Please provide keywords (separated by comma's) after the /suggest command.") 

# add the film to your film list datatbase
def append(update: Update, context: CallbackContext):

    global chatgpt, redis1

    # obtain the telegram user ID from the user
    telegram_id = update.effective_chat.id

    try:

        film_name = ' '.join(context.args)
        if film_name == None:
            update.message.reply_text('Please add the film title folowed by the /append command.')
            return

        film_description = chatgpt.submit(f"Please generate a film description for the film title: '{film_name}'.")

        if film_description.startswith("Error"):
            update.message.reply_text(f"Cannot generate a film description for '{film_name}'. Please check if the film title is valid.")
        else:
            # insert the user telegram ID, film title, film description to the Reis database
            redis1.hset(str(telegram_id).lower(), film_name, film_description)
            update.message.reply_text(f"Already insert '{film_name}' to the DB with the following description:\n{film_description}")

    except Exception as e:

        logging.error(f"Error: {e}.")
        update.message.reply_text("An error for adding the film to DB. Please try again.")

# Read the film description from Redis DB given a film title
def read(update: Update, context: CallbackContext):

    global redis1

    # obtain the Telegram user ID
    telegram_id = update.effective_chat.id

    try:
        if len(context.args) == 0:
            update.message.reply_text('Please give a film title after the /read command.')
            return

        film_name = ' '.join(context.args)
        film_txt = redis1.hget(str(telegram_id), film_name)

        if film_txt is None:
            update.message.reply_text("No " + film_name + "in the DB.")
        else:
            update.message.reply_text(f"Here is the film description for '{film_name}':\n{film_txt.decode('utf-8')}")

    except Exception as e:

        logging.error(f"Error: {e}")
        update.message.reply_text("Cannot read the film description. Please try again.")

if __name__ == '__main__':
    main()
