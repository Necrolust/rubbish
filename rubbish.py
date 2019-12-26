import json
import requests
import creds
import os
import time
import logging

from itertools import islice
from bs4 import BeautifulSoup
from termcolor import colored
from collections import OrderedDict
from datetime import datetime
from multiprocessing import Process
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import (TelegramError, Unauthorized, BadRequest, TimedOut, ChatMigrated, NetworkError)

file_path = ''

date1 = []
date2 = []
now = []
date1_type1 = []
date1_type2 = []
date2_type1 = []
date2_type2 = []


def get_dates():
    global now
    global date1
    global date2
    global date1_type1
    global date1_type2
    global date2_type1
    global date2_type2

    now = datetime.now()
    page = requests.get(creds.url, "rubbish.html")
    soup = BeautifulSoup(page.text, "html.parser")
    get_webpage_as_text = soup.get_text()

    text_file = open(os.path.join(file_path, 'webpage_stripped_to_text.txt'), "wb")
    text_file.write(get_webpage_as_text.encode('utf-8'))
    text_file.close()

    # find only the relevant lines (household collection - not commercial collection)
    with open(os.path.join(file_path, 'webpage_stripped_to_text.txt'), 'r') as f:
        for line in f:
            seen = [0]
            if line == 'Your next collection dates:\n' and not seen[0]:
                dates_as_text = ''.join(islice(f, 2))
                seen[0] = 1
            if all(seen):
                break

    # split the result into separate variables
    date_lines = dates_as_text.splitlines()
    date1_unparsed = date_lines[0]
    date2_unparsed = date_lines[1]

    # find the length of these strings
    date1_length = len(date1_unparsed)
    date2_length = len(date2_unparsed)

    # separate out the date from the collection type
    global date1
    date1 = date1_unparsed[:date1_unparsed.find('Rubbish')] + ' ' + str(datetime.now().year)
    # TODO: Change the below to use datetime once we actually hit the year 2020. Uncomment the line following the below.
    date2 = date2_unparsed[:date2_unparsed.find('Rubbish')] + ' 2020'
    # date2 = date2_unparsed[:date2_unparsed.find('Rubbish')] + ' ' + str(datetime.now().year)

    # separate out the collection type from the date
    date1_type = date1_unparsed[date1_unparsed.find('Rubbish'):date1_length]
    date2_type = date2_unparsed[date2_unparsed.find('Rubbish'):date2_length]

    if len(date2_type.split()) == 1:
        date2_type1 = date2_type
        date2_type2 = []
    elif len(date2_type.split()) > 1:
        date2_type1 = date2_type[:date2_type.find('Recycle')]
        date2_type2 = date2_type[date2_type.find('Recycle'):]

    if len(date1_type.split()) == 1:
        date1_type1 = date1_type
        date1_type2 = []
    elif len(date1_type.split()) > 1:
        date1_type1 = date1_type[:date1_type.find('Recycle')]
        date1_type2 = date1_type[date1_type.find('Recycle'):]


def update_rubbish_dates():
    while True:
        try:
            get_dates()

            # print nicely formatted output
            print(colored('Your collection dates are as follows:', 'green'))
            print(colored(date1, 'yellow'))
            if date1_type2 == []:
                unordered_dict = (
                ("Title", "Your next collection dates:"), ("Date1", date1), ("Date1_type1", date1_type1),
                ("Date2", date2), ("Date2_type1", date2_type1),
                ("Date2_type2", date2_type2))
                print(colored(date1_type1, 'yellow'))
            else:
                unordered_dict = (
                ("Title", "Your next collection dates:"), ("Date1", date1), ("Date1_type1", date1_type1),
                ("Date1_type2", date1_type2),
                ("Date2", date2), ("Date2_type1", date2_type1))
                print(colored(date1_type1, 'yellow'))
                print(colored(date1_type2, 'yellow'))
            print(colored(date2, 'yellow'))
            if date2_type2 == []:
                unordered_dict = (
                ("Title", "Your next collection dates:"), ("Date1", date1), ("Date1_type1", date1_type1),
                ("Date1_type2", date1_type2),
                ("Date2", date2), ("Date2_type1", date2_type1))
                print(colored(date2_type1, 'yellow'))
            else:
                unordered_dict = (
                ("Title", "Your next collection dates:"), ("Date1", date1), ("Date1_type1", date1_type1),
                ("Date2", date2),
                ("Date2_type1", date2_type1), ("Date2_type2", date2_type2))
                print(colored(date2_type1, 'yellow'))
                print(colored(date2_type2, 'yellow'))

            # convert stored values into JSON file and format (so I don't have to fuck around with the HASS template sensors)
            ordered_dict = OrderedDict(unordered_dict)
            print('\n')
            print(colored('Printing results in JSON format', 'red'))
            print('\n')
            print(json.dumps(ordered_dict, indent=4))
            print('\n')
            print('Generated at ' + str(now))

            text_file = open(os.path.join(file_path, 'result.json'), "w")
            text_file.write(json.dumps(ordered_dict, indent=4))
            text_file.close()

            time.sleep(3600)
        except KeyboardInterrupt:
            raise ('exit')


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a perky. Please bare with me ^_^ ")


def echo(update, context):
    global date1
    global date1_type1
    global date1_type2
    global date2
    global date2_type1
    global date2_type2
    global now

    get_dates()
    condition_text = str(update.message.text)

    if condition_text.find('rubbish') > -1:
        if str(now) < date2:
            if date1_type2 == []:
                update.message.reply_text(format(date1) + ' ' + format(date1_type1))
            elif date1_type2 != []:
                update.message.reply_text(format(date1) + ' ' + format(date1_type1) + ' ' + format(date1_type2))

    if condition_text.find('rubbish') > -1:
        if str(now) >= date2:
            if date2_type2 == []:
                update.message.reply_text(format(date2) + ' ' + format(date2_type1))
            elif date2_type2 != []:
                update.message.reply_text(format(date2) + ' ' + format(date2_type1) + ' ' + format(date2_type2))


def telegram_perky_bot():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
    updater = Updater(token=creds.telegram_token, use_context=True)
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    echo_handler = MessageHandler(Filters.text, echo)
    dispatcher.add_handler(echo_handler)
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    p1 = Process(target=update_rubbish_dates)
    p1.start()
    p2 = Process(target=telegram_perky_bot)
    p2.start()