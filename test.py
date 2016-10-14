#!/usr/bin/env python
# coding: utf-8

from wxbot import *
import EXBOT
import json
import os


def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv


def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode('utf-8')
        if isinstance(value, unicode):
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv



class MyWXBot(WXBot):
    def __init__(self):
        WXBot.__init__(self)
        self.configFolder = os.path.join(os.getcwd(), 'config')
        self.exBotList = []
        self.loadConfig()

    def loadConfig(self):
        fileName = 'config.json'
        fn = os.path.join(self.configFolder, fileName)
        with open(fn, 'r') as f:
            config = json.load(f, object_hook=_decode_dict)
        if config['DEBUG']:
            self.DEBUG = config['DEBUG']
        if config['autoReplyMode']:
            self.autoReplyMode = config['autoReplyMode']
        if config['user_agent']:
            self.user_agent = config['user_agent']
        if config['interactive']:
            self.interactive = config['interactive']
        if config['autoOpen']:
            self.autoOpen = config['autoOpen']
        if config['NoReplyGroupList']:
            self.noReplyGroupList = config['NoReplyGroupList']
        if config['NoReplyContactList']:
            self.noReplyContactList = config['NoReplyContactList']
        if config['GameGroupList']:
            self.gameGroupList = config['GameGroupList']
        return True

    def handle_raw_msg(self, msg):
        for exbot in self.exBotList:
            if exbot.handleMsg(msg):
                print '[*] 机器人已经处理该消息'
                return True
        return False

    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            self.send_msg_by_uid(u'hi', msg['user']['id'])


    def afterRun(self):
        self.createExBots()

    def createExBots(self):
        print '创建机器人...'
        self.exBotList = []
        for group in self.group_list:
            for gamegroup in self.gameGroupList:
                if group['NickName'].encode('utf8') == gamegroup['GroupName']:
                    groupID = group['UserName']
                    groupName = group['NickName']
                    adminName = gamegroup['Admin']
                    adminID = self.get_user_id(adminName)
                    exBot = EXBOT.EXBOT(groupID,groupName,adminID,adminName,self)
                    self.exBotList.append(exBot)
                    print '为群＊%s＊创建一个机器人,管理员为*%s*\n'%(groupName.encode('utf8'),adminName.encode('utf8'))
        return True


def main():
    bot = MyWXBot()
    bot.DEBUG = True
    bot.conf['qr'] = 'png'
    bot.run()


if __name__ == '__main__':
    main()
