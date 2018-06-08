# -*- coding: utf-8 -*-
import logging
import re
from datetime import datetime, timedelta

from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session

engine = create_engine('sqlite:///db.sqlite', echo=True)
Session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
# session = Session()

user_tag_rel_table = Table('user_tag_rel', Base.metadata,
                           Column('user_id', Integer, ForeignKey('user.id')),
                           Column('tag_id', Integer, ForeignKey('tag.id'))
                           )


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    first_name = Column(String)
    last_name = Column(String)
    chat_id = Column(Integer, unique=True)
    mailing = relationship('Mailing', backref='user', uselist=False)
    tag = relationship('Tag', secondary=user_tag_rel_table)

    @classmethod
    def get_user(cls, **kwargs):
        """ Create new user if not exist
        :param kwargs: first_name, last_name, chat_id
        :return: user object
        """
        session = Session()
        logging.debug('chat_id = {}'.format(kwargs.get('chat_id')))

        user = session.query(cls).filter_by(chat_id=kwargs.get('chat_id')).first()
        logging.debug('user = {}'.format(user))
        if not user:
            user = User(**kwargs)
            session.add(user)
            user.mailing.append(Mailing())
            session.commit()
        return user

    def add_tag(self, *args):
        """ Add tags to current user
        :param args: list of tags name
        :return: list of tags object
        """
        session = Session()
        tags = [get_or_create(session, Tag, {'name': arg}, **{'name': arg}) for arg in args]
        logging.debug('tags = {}'.format(tags))
        [self.tag.append(tag) for tag in tags]
        session.add(self)
        session.commit()
        return tags

    @classmethod
    def get_all_users(cls):
        session = Session()
        return session.query(cls).all()

    def __repr__(self):
        return "<User(first_name='%s', last_name='%s')>" % (
            self.first_name, self.last_name)


class Tag(Base):
    __tablename__ = 'tag'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def __repr__(self):
        return "{}".format(self.name)


class Mailing(Base):
    __tablename__ = 'mailing'
    id = Column(Integer, primary_key=True)
    rule = Column(String, default='*,*')
    last_mailing = Column(DateTime, default=datetime.now())
    next_mailing = Column(DateTime, default=datetime.now())
    user_id = Column(Integer, ForeignKey('user.id'))

    def is_mailing_time(self):
        """ *,*
        :return:
        """
        session = Session()
        res = False
        re.compile('')
        rule_list = self.rule.split(',')
        now = datetime.now()

        if now >= self.next_mailing:
            next_mailing = self.next_mailing + timedelta(hours=int(rule_list[0]), minutes=int(rule_list[1]))
            res = True
            self.last_mailing, self.next_mailing = self.next_mailing, next_mailing
            session.add(self)
            session.commit()
        print(res)
        return res

    def set_rule(self, hour, minute):
        session = Session()
        self.rule = '{},{}'.format(hour, minute)
        self.last_mailing = datetime.now()
        self.next_mailing = self.last_mailing + timedelta(hours=int(hour), minutes=int(minute))
        print('--------------------', self.next_mailing)
        session.add(self)
        session.commit()
        return self.is_mailing_time()

    def __repr__(self):
        return "{}".format(self.rule.split(','))


def get_or_create(session, model, filters, **kwargs):
    p1 = session.query(model).filter(*filters).one_or_none()
    if p1 is None:
        p1 = model(**kwargs)
        session.add(p1)
    return p1


if __name__ == '__main__':
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)
    users = User.get_user(chat_id=529345770)
    # print('------',users.mailing.last_mailing.timestamp())
    print(users.mailing.last_mailing, '-----', users.mailing.next_mailing)
    next_mailing = users.mailing.next_mailing + timedelta(hours=int(0), minutes=int(1))
    users.mailing.last_mailing, users.mailing.next_mailing = users.mailing.next_mailing, next_mailing
    print(users.mailing.last_mailing, '-----', users.mailing.next_mailing)
    # print(users.mailing.last_mailing)
    # for user in users:
    #     print('user.tag {}'.format(user.tag))
    #     print('str(user.tag) {}'.format(str(user.tag)))
    #     print('repr(user.tag) {}'.format(repr(user.tag)))
