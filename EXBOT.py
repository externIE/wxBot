#!/usr/bin/env python
# coding: utf-8
import os
import json
import threading
import time
import re

def calcAnswer(content):
	answer = None
	if content.find('凌志') != -1:
		answer = '星翔是傻钟最爱的人'
	if content.find('丁星') != -1 or content.find('星翔') != -1:
		answer = '沙中是星翔最爱的人儿'

	return answer


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
Status_White 		= 0

Status_QiangZhuang 	= 1
Status_QZ_END		= 2 

Status_XiaZhu 		= 3
Status_XZ_END		= 4

Status_QiangBao 	= 5
Status_QB_END		= 6

Status_Wait         = 7


StatusProfile = {Status_White:u'空白',Status_Wait:u'等待中',Status_QiangZhuang:u'上庄中',Status_XiaZhu:u'下注中',Status_QiangBao:u'抢包中',Status_QZ_END:u'抢庄结束',Status_XZ_END:u'下注结束',Status_QB_END:u'抢包结束'}




#游戏管理机器人,处理某个群的群消息
class EXBOT(object):
	

	def __init__(self, groupid, groupname, admin, adminname, weixin):
		self.groupid = groupid
		self.groupname = groupname
		self.admin = admin
		self.adminname = adminname
		self.weixin = weixin
		self.qiangzhuangtimelimit = 20
		self.xiazhutimelimit = 20
		self.qiangbaotimelimit = 20
		self.status = Status_White

		self.qzPlayerList = {}
		self.xzPlayerList = {}
		self.csPlayerList = {}

		self.timeLine = None

		self.waitForRedBaoProfile = True
		self.qiangbaoCostTime = 0

		self.loadConfig()
		self.loadPlayerInfo()

	def __str__(self):
		description = \
		"=========================\n"\
		"[#] 我是［" + str(self.groupname) + "］群的机器人\n"\
		"[#] 该群的管理员是［" + str(self.adminname) + "］\n"\
		"========================="
		return description

	def loadConfig(self):
		filename = 'config.json'
		dirname = os.path.join(os.getcwd(), 'config')
		fn = os.path.join(dirname, filename)
		with open(fn, 'r') as file:
			config = json.load(file, object_hook=_decode_dict)
		self.qiangzhuangtimelimit = config["QiangZhuangTimeLimit"]
		self.xiazhutimelimit = config["XiaZhuTimeLimit"]
		self.qiangbaotimelimit = config["QiangBaoTimeLimit"]
		self.boutintervaltime = config["每局间隔时间"]
		self.zLowLimit = config["上庄下限"]
		self.xzLowLimit = config["下注下限"]

		self.qzRatio = config["上庄抽水百分比"]
		self.stRatio = config["庄家赢抽水百分比"]

		self.blList = config["倍率"]
		self.maxBL = self.blList["豹子"]

		self.tpOutZhuangTip = config["溢庄提醒"]
		self.tpOutScoreTip = config["溢分提醒"]

		self.tpNewboutTip = config["新局提示"]
		self.tpPlayersScoreList = config["玩家积分榜"]
		self.tpPlayerScore = config["玩家积分"]
		self.tpQZEnd = config["抢庄结束"]

		self.tpXZTip = config["下分提示"]
		self.tpXZList = config["下分列表"]
		self.tpXZRes = config["下分结果"]

		self.tpFBTip = config["发包提示"]
		self.tpEndFBTip = config["提醒发包人发布结果"]

		self.tpNPRez = config["抢包人"]
		self.tpFPRez = config["未抢包人"]
		self.tpRez = config["抢包结束"]

		self.strEndGame = config["结束游戏提示"]

		self.autoCtrl = config["自动控制"]

	def loadPlayerInfo(self):
		filename = 'playerinfo.json'
		dirname = os.path.join(os.getcwd(), 'playerinfo')
		fn = os.path.join(dirname, filename)
		with open(fn, 'r') as file:
			self.jsonPlayersInfo = config = json.load(file, object_hook=_decode_dict)
		self.playersinfo = config['playersinfo']
		self.playersName = []
		for index, playerinfo in enumerate(self.playersinfo):
			self.playersName.append(playerinfo['name'])


	def setStatus(self, status):
		self.status = status

	def isStatus(self, status):
		return self.status == status

    #向自己管理的组里面发送消息
	def sendMsgToMyGroup(self, text):
		weixin = self.weixin
		if not weixin :
			print '[error!] connector is none'
			return
		return weixin.send_msg_by_uid(text, self.groupid)

	def parseMsgContent(self, content):
		li = content.split(':<br/>')
		fromUserName = li[0]
		msgContent = li[1]
		return fromUserName, msgContent

	def parseMsg(self, msg):
		content = msg['Content'].replace('&lt;', '<').replace('&gt;', '>')
		memberID, memberSay = self.parseMsgContent(content)
		memberName = self.weixin.get_group_member_name(self.groupid,memberID)
		memberName = memberName['display_name'] if 'display_name' in memberName and memberName[
                        'display_name'] else memberName['nickname']
		return memberID, memberName.encode('utf-8'), memberSay.encode('utf-8')

	def getPlayerScoreByName(self, name):
		for index, playerinfo in enumerate(self.playersinfo):
			print 'playerInfo[name]:', playerinfo["name"]
			if playerinfo["name"] == name:
				return playerinfo['score']
		return 0

	def setPlayerScoreByName(self, name, score):
		for index, playerinfo in enumerate(self.playersinfo):
			if playerinfo["name"] == name:
				self.playersinfo[index]["score"] = int(score)
				break

	def setPlayerDiffScoreByName(self, name, diffScore):
		for index, playerinfo in enumerate(self.playersinfo):
			if playerinfo["name"] == name:
				self.playersinfo[index]["score"] += int(diffScore)
				break

	def restoreShui(self):
		filename = 'shui.json'
		dirname = os.path.join(os.getcwd(), 'shui')
		fn = os.path.join(dirname, filename)
		totalShui = 0
		totalShui += self.csPlayerList[self.zPlayerName]
		with open(fn, 'r') as file:
			jsonShui = json.load(file, object_hook=_decode_dict)
			jsonShui['totalshui'] += totalShui
			file.close()
			print jsonShui['totalshui']
			with open(fn, 'w') as filew:
				filew.write(json.dumps(jsonShui, indent=4))
				filew.close()

	def restorePlayersScore(self):
		filename = 'playerinfo.json'
		dirname = os.path.join(os.getcwd(), 'playerinfo')
		fn = os.path.join(dirname, filename)
		with open(fn, 'w') as file:
			file.write(json.dumps(self.jsonPlayersInfo, ensure_ascii=False , indent=4))

	def sendPlayersScore(self):
		template = self.tpPlayersScoreList
		content = ''
		for playerinfo in self.playersinfo:
			content += self.tpPlayerScore%(playerinfo['name'], playerinfo['score'])
		text = template%(content,)
		if self.sendMsgToMyGroup(text):
			print '玩家积分发送成功'
		else:
			print '[error!] 玩家积分发送失败，正在重新发送...'
			self.sendPlayersScore()

	def sendPlayerScore(self, name):
		for playerinfo in self.playersinfo:
			if name == playerinfo['name']:
				self.sendMsgToMyGroup("[@%s]当前积分：%s"%(name, playerinfo['score']))
				return
		self.sendMsgToMyGroup('[Sorry]后台没有您的积分纪录')

	def startQZ(self):
		#发送新局消息
		if not self.isStatus(Status_QiangZhuang - 1):
			print u'当前状态为[%s]'%(StatusProfile[self.status])
			self.sendMsgToMyGroup('当前状态为[%s],不能开始上庄'%(StatusProfile[self.status]))
			return

		print '发送抢庄消息，抢庄开始'
		self.qzPlayerList = {}
		template = self.tpNewboutTip
		text = template%(self.adminname, self.qiangzhuangtimelimit)
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_QiangZhuang)
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.startQZ()

	def endQZ(self):
		#抢庄结束
		if not self.isStatus(Status_QZ_END - 1):
			print u'当前状态为[%s]'%(StatusProfile[self.status])
			self.sendMsgToMyGroup('当前状态为[%s],不能开始结束上庄'%(StatusProfile[self.status]))
			return

		if len(self.qzPlayerList) == 0:
			#没有人抢庄，游戏提前结束
			self.sendMsgToMyGroup('[*]没人抢庄，游戏提前结束')
			self.initData()
			return False
		template = self.tpQZEnd
		zPlayerName = None
		zZhu = -1000
		for name, zhu in self.qzPlayerList.items():
			if zhu > zZhu:
				zPlayerName = name
				zZhu = zhu
		print '庄', zPlayerName, ' 庄注', zZhu
		self.zPlayerName = zPlayerName
		#扣掉茶水费的庄注
		self.zZhu = zZhu * (1 - self.qzRatio)
		#原始庄注
		self.ozZhu = zZhu

		self.csPlayerList[zPlayerName] = zZhu*self.qzRatio

		text = template%(zPlayerName,zZhu,self.ratio2percent(self.qzRatio))
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_QZ_END)
			return True
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.endQZ()

	def ratio2percent(self, ratio):
		strRatio = str(ratio*100)+'%'
		return strRatio


	def startXZ(self):
		#开始下注
		if not self.isStatus(Status_XiaZhu - 1):
			print u'当前状态为[%s]'%(StatusProfile[self.status])
			self.sendMsgToMyGroup('当前状态为[%s],不能开始结束下注'%(StatusProfile[self.status]))
			return

		print '开始下注'
		self.xzPlayerList = {}
		template = self.tpXZTip
		text = template%(self.adminname, self.xiazhutimelimit, self.maxBL)
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_XiaZhu)
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.startXZ()

	def endXZ(self):
		#下注结束
		if not self.isStatus(Status_XZ_END - 1):
			print u'当前状态为[%s]'%(StatusProfile[self.status])
			self.sendMsgToMyGroup('当前状态为[%s],不能开始结束下注'%(StatusProfile[self.status]))
			return

		if len(self.xzPlayerList) == 0:
			#没人下分，游戏提前结束
			self.sendMsgToMyGroup("[*]没人下注，游戏提前结束")
			self.initData()
			return False
		template = self.tpXZList
		content = ''
		for name, zhu in self.xzPlayerList.items():
			content += self.tpXZRes%(name, zhu)
		text = template%(content,)
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_XZ_END)
			return True
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.endXZ()

	def startFB(self):
		#开始发包
		if not self.isStatus(Status_QiangBao - 1):
			warning = u'当前状态为[%s]'%(StatusProfile[self.status])
			print unicode(warning, 'utf-8')
			self.sendMsgToMyGroup(unicode(warning, 'utf-8'))
			return

		template = self.tpFBTip
		text = template%(self.adminname, len(self.xzPlayerList) + 1)
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_QiangBao)
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.startFB()

	def endFB(self):
		#提醒发包人应该结束抢包了
		template = self.tpEndFBTip
		text = template%(self.adminname, )
		if self.sendMsgToMyGroup(text):
			pass
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.endFB()

	def showResult(self):
		#发送结果
		self.calcType()
		self.buildResult()
		self.restorePlayersScore()
		self.restoreShui()
		normalResults = ""
		for name, bl in self.blPlayerList.items():
			strName = name
			strZX = "庄" if name == self.zPlayerName else "闲"
			strXZ = str(self.xzPlayerList[name])
			strDS = str(self.dsPlayerList[name])
			strType = self.typePlayerList[name]
			strBL = str(self.blPlayerList[name])
			strSign = '赢' if self.diffPlayerList[name] > 0 else '输'
			strDiff = str(abs(self.diffPlayerList[name]))
			strShui = str(self.csPlayerList[name])
			strScore = str(self.getPlayerScoreByName(name))
			normalResults += self.tpNPRez%(strName,strZX,strXZ,strDS,strType,strBL,strSign,strDiff,strShui,strScore)

		abortResults = ""
		for name, xzScore in self.xzPlayerList.items():
			#看看谁下注但没有抢包
			if name not in self.blPlayerList.keys():
				strName = name
				strZX = "庄" if name == self.zPlayerName else "闲"
				strSign = '赢' if self.diffPlayerList[name] > 0 else '输'
				strDiff = str(abs(self.diffPlayerList[name]))
				strScore = str(self.getPlayerScoreByName(name))
				abortResults += self.tpFPRez%(strName,strZX,strSign,strScore)

		template = self.tpRez
		text = template%(normalResults, abortResults, self.boutintervaltime)
		if self.sendMsgToMyGroup(text):
			pass
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.showResult()

	def initData(self):
		self.setStatus(Status_White)


	#抢庄
	def handleQiangZhuang(self, memberID, memberName, memberSay):
		if memberSay.isdigit() and int(memberSay) > self.zLowLimit:
			if int(memberSay) <= self.getPlayerScoreByName(memberName):
				if memberName not in self.qzPlayerList.keys():
					self.qzPlayerList[memberName] = int(memberSay)
					print memberName, '抢庄', memberSay
				else:
					self.qzPlayerList[memberName] = self.qzPlayerList[memberName] if self.qzPlayerList[memberName] > int(memberSay) else int(memberSay)
					print memberName, '抢庄'
			else:
				template = self.tpOutZhuangTip
				text = template%(memberName, self.getPlayerScoreByName(memberName))
				self.sendMsgToMyGroup(text)
		else:
			if not memberSay.isdigit():
				self.sendMsgToMyGroup('[%s]抢庄无效！'%(memberName,))
			else:
				self.sendMsgToMyGroup('[%s]庄下限%s起，本次上庄无效'%(memberName, self.zLowLimit))
		if memberSay == '取消':
			if memberName in self.qzPlayerList.keys():
				self.qzPlayerList.pop(memberName)
				self.sendMsgToMyGroup('[%s]取消上庄成功'%(memberName,))
				print '[%s]取消上庄成功'%(memberName,)

	#下注
	def handleXiaZhu(self, memberID, memberName, memberSay):
		if memberSay.isdigit() and int(memberSay) > self.xzLowLimit:
			if memberName == self.zPlayerName:
				self.sendMsgToMyGroup('[@%s ]庄不参与下注'%(memberName,))
				return
			if int(memberSay)*self.maxBL <= self.getPlayerScoreByName(memberName):
				self.xzPlayerList[memberName] = int(memberSay)
				print memberName, '下注', memberSay
				# if memberName not in self.qzPlayerList.keys():
				# 	self.xzPlayerList[memberName] = int(memberSay)
				# 	print memberName, '下注', memberSay
				# else:
				# 	self.xzPlayerList[memberName] = self.qzPlayerList[memberName] if self.xzPlayerList[memberName] > int(memberSay) else int(memberSay)
				# 	print memberName, '下注'
			else:
				template = self.tpOutScoreTip
				text = template%(memberName, self.getPlayerScoreByName(memberName)/self.maxBL)
				self.sendMsgToMyGroup(text)
		else:
			if not memberSay.isdigit():
				self.sendMsgToMyGroup('[%s]下注无效！'%(memberName,))
			else:
				self.sendMsgToMyGroup('[%s]押注下限%s起，本次押注无效'%(memberName, self.xzLowLimit))
		if memberSay == '取消':
			if memberName in self.xzPlayerList.keys():
				self.xzPlayerList.pop(memberName)
				print memberName , '取消下注'

	def handleRedBaoProfile(self, memberID, memberName, memberSay):
		if memberID == self.admin and memberName == self.adminname:
			if memberSay.find('抢包情况') != -1 :
				ret = self.parseRedBaoProfile(memberSay)
				if ret :
					self.waitForRedBaoProfile = False
					self.setStatus(Status_White)
					if not self.autoCtrl:
						self.showResult()
				else :
					return
		else:
			return

	def parseRedBaoProfile(self, memberSay):
		pattern = ur'名字：\*(\S+)\* -- 点数：\*(\S+)元\*'
		pm = re.findall(pattern.encode("utf-8"), memberSay)
		self.dsPlayerList = {}
		print pm
		for group in pm:
			print '名字', group[0]
			print '点数', group[1]
			#在python中字符编码的转换都是通过unicode作为中间值实现的
			self.dsPlayerList[unicode(group[0], 'utf-8')] = group[1]
		print self.dsPlayerList
		if len(self.dsPlayerList) != 0 :
			return True
		else :
			return False

	def calcType(self):
		dsPlayerList = self.dsPlayerList
		self.typePlayerList = {}
		self.blPlayerList = {}
		for name, score in dsPlayerList.items():
			num0, num1, num2 = self.splitScore(score)
			if (num1 == 0 and num2 == 0) or (num1 == 1 and num2 == 0):
				#牛牛
				self.typePlayerList[name] = "牛牛"
				self.blPlayerList[name] = self.blList["牛牛"]
				continue
			if num0 == num1 == num2:
				#豹子 15
				self.typePlayerList[name] = "豹子"
				self.blPlayerList[name] = self.blList["豹子"]
				continue
			if num0 != 0 and num1 == 0 and num2 == 0 :
				#满牛 14
				self.typePlayerList[name] = "满牛"
				self.blPlayerList[name] = self.blList["满牛"]
				continue
			if num0 != 0 and num0 + 1 == num1 and num1 + 1 == num2:
				#顺子 13
				self.typePlayerList[name] = "顺子"
				self.blPlayerList[name] = self.blList["顺子"]
				continue
			if num1 == num2:
				#对子 12
				self.typePlayerList[name] = "对子"
				self.blPlayerList[name] = self.blList["对子"]
				continue
			if num2 == 0:
				#金牛 11
				self.typePlayerList[name] = "金牛"
				self.blPlayerList[name] = self.blList["金牛"]
				continue
			if (num1 + num2)%10 == 0 :
				#牛牛 10
				self.typePlayerList[name] = "牛牛"
				self.blPlayerList[name] = self.blList["牛牛"]
				continue

			self.typePlayerList[name] = "牛%d"%((num1+num2)%10,)
			self.blPlayerList[name] = self.blList["牛%d"%((num1+num2)%10,)]

	def buildResult(self):
		zBL = self.blPlayerList[self.zPlayerName]
		zPlayerName = self.zPlayerName
		self.diffPlayerList = {}
		self.diffPlayerList[zPlayerName] = 0

		#先检查有没有人没下注但是抢了包
		for qbName in self.blPlayerList.keys():
			if qbName != zPlayerName and qbName != self.adminname and qbName not in self.xzPlayerList.keys():
				print '[@%s]没有押注但是抢了包，当局无效，赔付所有闲家一赔一，赔付庄家588'%(qbName,)
				self.sendMsgToMyGroup('[@%s]没有押注但是抢了包，当局无效，赔付所有闲家一赔一，赔付庄家588'%(qbName,))



		for name, bl in self.blPlayerList.items():
			#这一次循环先把所有输的闲家的钱收过来
			if zPlayerName == name :
				continue
			if bl <= zBL :
				#庄家赢
				xzScore = self.xzPlayerList[name]
				csRatio = 0
				if zBL >= 11:
					csRatio = self.csRatio
				self.setPlayerDiffScoreByName(zPlayerName, xzScore*zBL*(1-csRatio))
				self.setPlayerDiffScoreByName(name, -xzScore*zBL)
				self.diffPlayerList[name] = -xzScore*zBL
				self.diffPlayerList[zPlayerName] += xzScore*zBL*(1-csRatio)
				#抽水
				self.csPlayerList[zPlayerName] += xzScore*zBL*csRatio


		for name, xzScore in self.xzPlayerList.items():
			#看看谁下注但没有抢包
			if name not in self.blPlayerList.keys():
				#按庄家的倍率赔
				csRatio = 0
				if zBL >= 11:
					csRatio = self.csRatio
				self.setPlayerDiffScoreByName(zPlayerName, xzScore*zBL*(1-csRatio))
				self.setPlayerDiffScoreByName(name, -xzScore*zBL)
				self.diffPlayerList[name] = -xzScore*zBL
				self.diffPlayerList[zPlayerName] += xzScore*zBL*(1-csRatio)
				#抽水
				self.csPlayerList[zPlayerName] += xzScore*zBL*csRatio

		xjWinTotal = 0
		xjWin = {}
		for name, bl in self.blPlayerList.items():
			#这一次循环庄家赔钱
			if zPlayerName == name :
				continue
			if bl > zBL :
				csRatio = 0
				if bl >= 11:
					csRatio = self.csRatio
				#庄家赔
				xzScore = self.xzPlayerList[name]
				self.setPlayerDiffScoreByName(zPlayerName, -xzScore*bl)
				self.setPlayerDiffScoreByName(name, xzScore*bl)

				self.diffPlayerList[name] = xzScore*bl
				self.diffPlayerList[zPlayerName] += -xzScore*bl
				#抽水
				# self.csPlayerList[name] = xzScore*bl*csRatio

				xjWin[name] = xzScore*bl
				xjWinTotal += xzScore*bl

		if -self.diffPlayerList[zPlayerName] > self.zZhu :
			diffScore = - self.zZhu + self.diffPlayerList[zPlayerName]
			self.setPlayerDiffScoreByName(zPlayerName, diffScore)
			self.diffPlayerList[zPlayerName] += diffScore
			for name, bl in self.blPlayerList.items():
				#
				if zPlayerName == name :
					continue
				if bl > zBL :
					#
					xzScore = self.xzPlayerList[name]
					self.setPlayerDiffScoreByName(name, -diffScore*xjWin[name]/xjWinTotal)
					self.diffPlayerList[name] -= diffScore*xjWin[name]/xjWinTotal

		if self.diffPlayerList[zPlayerName] > 0 :
			#庄家赢钱，抽10%
			diffScore = self.diffPlayerList[zPlayerName]
			self.setPlayerDiffScoreByName(zPlayerName, -diffScore*self.stRatio)
			self.diffPlayerList[zPlayerName] -= diffScore*self.stRatio
			self.csPlayerList[zPlayerName] += diffScore*self.stRatio



	def splitScore(self, score):
		pm = re.search(r'(\d).(\d)(\d)', score)
		return int(pm.group(1)), int(pm.group(2)), int(pm.group(3))

	def startTimeLine(self):
		self.startLine = True
		self.timeLine = threading.Thread(target=self.commander)
		self.timeLine.setDaemon(True)
		self.timeLine.start()

	def stopTimeLine(self):
		self.startLine = False
		self.timeLine = None
		text = self.strEndGame
		if self.sendMsgToMyGroup(text):
			self.setStatus(Status_White)
		else:
			print '[error!] 发送开始消息失败,正在重新发送...'
			self.stopTimeLine()

	def commander(self):
		while self.startLine:
			self.sendPlayersScore()
			time.sleep(2)

			self.startQZ()
			time.sleep(self.qiangzhuangtimelimit)
			ret = self.endQZ()
			if not ret:
				break

			time.sleep(2)

			self.startXZ()
			time.sleep(self.xiazhutimelimit)
			ret = self.endXZ()
			if not ret:
				break

			time.sleep(2)

			self.startFB()
			self.waitForRedBaoProfile = True
			while self.waitForRedBaoProfile:
				self.qiangbaoCostTime += 0.1
				if self.qiangbaoCostTime % self.qiangbaotimelimit == 0 :
					self.endFB()
				#每0.01秒检查一次
				time.sleep(0.1)

			time.sleep(1)

			self.showResult()
			time.sleep(self.boutintervaltime)



    #处理消息
	def handleMsg(self, msg):
		if msg['FromUserName'] != self.groupid:
			#丢弃不是自己管理的消息
			return False
		weixin = self.weixin
		msgType = msg['MsgType']

		if msgType != 1: 
			#丢弃非文本消息
			print '非文本消息被丢弃'
			return False

		memberID, memberName, memberSay = self.parseMsg(msg)
		memberSay = memberSay.strip()
		if memberName not in self.playersName:
			#丢弃不在玩家列表中的人的消息
			print memberName, "不在游戏中..."
			print '全部成员', self.playersName
			return True
		if memberID == self.admin and memberSay == '结束游戏' :
			if self.autoCtrl:
				self.stopTimeLine()
				print '[*]结束游戏',memberName,memberSay
			else:
				self.sendMsgToMyGroup('当前为手动控制游戏，无须结束。')
			
			return True

		if memberSay == '我的积分':
			self.sendPlayerScore(memberName)
			return True
		if memberSay == '积分':
			self.sendPlayersScore()
			return True

		if memberID == self.admin and not self.autoCtrl:
			if memberSay == '开始游戏':
				self.sendPlayersScore()
				return True
			if memberSay == '开始上庄' or memberSay == '上庄开始':
				self.startQZ()
				return True
			if memberSay == '上庄结束' or memberSay == '结束上庄':
				self.endQZ()
				return True
			if memberSay == '开始下分' or memberSay == '下分开始':
				self.startXZ()
				return True
			if memberSay == '结束下分' or memberSay == '下分结束':
				self.endXZ()
				return True
			if memberSay == '准备发包' or memberSay == '发包准备':
				self.startFB()
				return True


		if self.isStatus(Status_White):
			if memberID == self.admin and memberSay == '开始游戏' :
				self.startTimeLine()
				print '[*]开始游戏',memberName,memberSay
		elif self.isStatus(Status_QiangZhuang):
			self.handleQiangZhuang(memberID, memberName, memberSay)
			print '[*]抢庄',memberName,memberSay
		elif self.isStatus(Status_XiaZhu):
			self.handleXiaZhu(memberID, memberName, memberSay)
			print '[*]下注',memberName,memberSay
		elif self.isStatus(Status_QiangBao):
			self.handleRedBaoProfile(memberID, memberName, memberSay)
			print '[*]抢包',memberName,memberSay
		else:
			print '[*]其他',memberName,memberSay
		return True
