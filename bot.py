# -*- coding: utf-8 -*-
import inspect
import logging
import time
import configparser
from threading import Thread

import schedule
from stackapi import StackAPI
from telegram.ext import CommandHandler, Filters, MessageHandler
from telegram.ext import Updater

from models import User

config = configparser.ConfigParser()
config.read('bot.ini')
secret_config = configparser.ConfigParser()
secret_config.read('secret_bot.ini')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=config['logging']['level'])


class StackBot:
    SITE = StackAPI('stackoverflow')

    def __init__(self):
        # 598867467: AAG7zO5v5C7m6N2tkf_lYsV4XqBte3ubM stack_of_bot I
        self.updater = Updater(token=secret_config['bot']['token'])
        self.dispatcher = self.updater.dispatcher
        self.add_handler()
        self._scheduling()
        self.updater.start_polling()

    @staticmethod
    def action_start(bot, update):
        logging.debug('action_start')
        User.get_user(first_name=update.message.from_user.first_name,
                      last_name=update.message.from_user.last_name,
                      chat_id=update.message.from_user.id)

        bot.send_message(chat_id=update.message.chat_id, text="command:\n/set_tag tag1 tag2\n/set_delay hours:minute")

    @staticmethod
    def action_set_tag(bot, update):
        user = User.get_user(chat_id=update.message.chat_id)
        text = update.message.text.replace('/set_tag ', '')
        tags = text.split()
        user.add_tag(*tags)
        bot.send_message(chat_id=update.message.chat_id, text='Your tags are {}'.format(tags))

    @staticmethod
    def action_set_delay(bot, update):
        user = User.get_user(chat_id=update.message.chat_id)
        text = update.message.text.replace('/set_delay ', '')
        hour, minute = text.split(':')
        if not user.mailing:
            user.mailing()
        user.mailing.set_rule(hour, minute)
        bot.send_message(chat_id=update.message.chat_id, text='Your delay is {} hour and {} minute'.format(hour,
                                                                                                           minute))

    @staticmethod
    def message_search(bot, update):
        # tagged = update.message.text,
        questions = StackBot.SITE.fetch('/search/advanced', sort='votes', impose_throttling=True,
                                        q=update.message.text)
        if not questions['items']:
            bot.send_message(chat_id=update.message.chat_id, text='Cant find questions')
            return
        text = StackBot._create_message(questions)
        bot.send_message(chat_id=update.message.chat_id, text=text)

    @staticmethod
    def _create_message(questions):
        message_template = '{title}\n' \
                           'score: {score}, answer_count: {answer_count}, view_count: {view_count}\n' \
                           '{tags}\n' \
                           '{link}'
        questions = [message_template.format(title=question['title'],
                                             link=question['link'],
                                             score=question['score'],
                                             answer_count=question['answer_count'],
                                             view_count=question['view_count'],
                                             tags=question['tags'], ) for question in questions[
                         'items']]
        text = '\n\n'.join(questions[:5])
        logging.debug('{}'.format(text))
        return text

    def add_handler(self):
        methods = inspect.getmembers(StackBot, predicate=inspect.isfunction)
        handler = None
        for name, method in methods:
            if name.startswith('action_'):
                command = name.lstrip('action_')
                handler = CommandHandler(command, method)
            elif name.startswith('message_'):
                handler = MessageHandler(Filters.text, method)
            if handler is not None:
                self.dispatcher.add_handler(handler)

    def _scheduling(self):
        try:
            thr = Thread(target=self._mailing_job, daemon=True)
            thr.start()
        except Exception as erorr:
            logging.error('mailing thread down with error: {}'.format(str(erorr)))
            return False
        return True

    def _mailing_job(self):
        schedule.every(int(config['schedule']['schedule'])).minutes.do(self._mailing)
        while True:
            schedule.run_pending()
            time.sleep(1)

    def _mailing(self):
        logging.debug('start mailing')
        users = User.get_all_users()
        for user in users:
            if user.mailing.is_mailing_time():
                questions = self.SITE.fetch('questions', fromdate=int(user.mailing.last_mailing.timestamp()),
                                            todate=int(user.mailing.next_mailing.timestamp()),
                                            tagged=user.tag, sort='votes')
                if not questions['items']:
                    return
                questions = ['{}\n{}'.format(question['title'], question['link']) for question in questions['items']]
                text = '\n\n'.join(questions)

                self.updater.bot.send_message(chat_id=user.chat_id, text=text)


if __name__ == '__main__':
    StackBot()
