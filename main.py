#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import configparser
import requests
import datetime
from datetime import timedelta, date
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters


# URL:s for getting temperature data
DATA_URL_BAK = "https://api.thingspeak.com/channels/1068855/fields/1.csv"

NAKKIKAMPPAE_STRING = """<b>{} Nakkikämppävuoro</b>

Ohje:
- Selvitä kaljatilanne
- Pese vieraspyyhkeet
- Osta pyykin- ja astianpesuainetta
- Osta vessapaperia ja käsisaippuaa
- Tyhjennä roskikset ja osta pusseja
- Pahvit/Lasit/Metallit keräyksiin
- Tölkit kauppaan"""

#--------------- CODE BELOW ---------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__) 

config = configparser.ConfigParser()

try:
    config.read('config.ini')

    GROUP_ID = config.get("Settings", "GROUP_ID")
    BOT_TOKEN = config.get("Settings", "BOT_TOKEN")
except:
    logger.error("You must assign GROUP_ID and BOT_TOKEN in config.ini source file.")
    exit()

# Returns weeks since specified date + default offset
def weeks_since_start(date1):
    NAKKIKAMPPAE_OFFSET = 4 # Offset to account for current nakkikämppä turn
    STARTDATE = date(2021, 1, 4) # First monday of 2021

    # Mondays of weeks
    monday1 = (STARTDATE - timedelta(days=STARTDATE.weekday()))
    monday2 = (date1 - timedelta(days=date1.weekday()))
    
    # Return number of weeks
    return ((monday2 - monday1).days / 7) + NAKKIKAMPPAE_OFFSET

# Return current nakkikämppä as string
def nakkikamppae():
    kamppa_number = int((weeks_since_start(date.today()) % 21) + 1)
    
    # Concat letter
    if(kamppa_number <= 9):
        return "A" + str(kamppa_number)
    else:
        return "B" + str(kamppa_number)

# Cron function that sends the nakkikämppämessage
def nakkikamppa_info(context):
    logger.info("Nakkikamppainfo lähetetty")
    context.bot.send_message(chat_id=GROUP_ID, text=NAKKIKAMPPAE_STRING.format(nakkikamppae()), parse_mode=telegram.ParseMode.HTML)

# Handler for /sauna command
def sauna(update, context):
    logger.info("/saunabak: " + str(update.message.chat))

    # Fetch temp .csv
    r = requests.get(DATA_URL_BAK)

    # Get temps from returned csv data
    temps = [l.split(",")[2] for l in r.text.splitlines()][1:]

    # Calculate temp delta from ten datapoints back
    delta_temp = float(temps[-1]) - float(temps[-6])

    # Increase or decrease of one degree
    text = "tasainen"
    if (delta_temp > 1):
        text = "nouseva"
    elif (delta_temp < -0.5):
        text = "laskeva"

    lasttemp = temps[-1]
    update.message.reply_text('Saunan lämpötila on {}°C {}'.format(lasttemp, text))
     
def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    
def echo(update, context):
    logger.info("Message: " + update.message.text)

def unpin(update, context):
    logger.info(update.message.sender_chat)
    if(update.message.sender_chat != None and update.message.sender_chat.type=="channel"):
        context.bot.unpin_chat_message(chat_id=update.message.chat_id, message_id=update.message.message_id)


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    
    # Set nakkikämppä info to be sent at ~12:00 on Mon
    job_queue = updater.job_queue
    job_queue.run_daily(nakkikamppa_info, days=[0], time=datetime.time(hour=10, minute=00, second=00))

    dp = updater.dispatcher
    
    # Command handlers
    dp.add_handler(CommandHandler("sauna", sauna))
    dp.add_handler(MessageHandler(Filters.text, unpin))

    dp.add_error_handler(error)
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()