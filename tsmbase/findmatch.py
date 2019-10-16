# -*- coding: utf-8 -*-

from pprint import pprint
from time import sleep, time
import json

from threading import Thread

from tsmbase.sm import Api as SteemMonstersApi
from tsteembase.api import Api as SteemApi


class FindMatch():

	step_part = 14						### Количество выводимых строк

	def __init__(self):
		
		self.sm_custom_cmd = {	'sm_find_match': self.sm_find_match,
								'sm_submit_team': self.sm_submit_team,
								'sm_team_reveal': self.sm_team_reveal,
								}
								
		self.liga_active = 'chemp'
		self.sm_find_match_list = []	### Кто подал заявку на батл
		self.sm_battles_list = {}		### Список trx_id ожидающих и не только
		self.sm_players_list = []
		self.sm_vs_list = []
		
		self.accounts_list = []			### Список аккантов для отслеживания

		self.replay = True
		self.timestamp = '1983-03-26T12:12:12'
						
		self.flag = True
		self.sm = SteemMonstersApi()
		#self.api = SteemApi()
		#self.sm.load_cards()
		
	##### ##### #####
	
	def run(self, liga):
		#self.scan_blocks(self.resolve_block)
		print('connect to', self.node)
		self.api = SteemApi(nodes = [self.node])
		self.liga_active = liga
		self.flag = True
		self.players = {acc: {} for acc in self.accounts_list}	### Список своих аккаунтов для отслеживания {player:}
		
		sm_thread = Thread(target = self.scan_blocks, args = [self.resolve_block], daemon = True)
		sm_thread.start()
		print('run scan')
		
		
	def stop(self):
		self.flag = False
		self.sm_find_match_list = []
		self.sm_battles_list = {}
		self.sm_players_list = []
		self.sm_vs_list = []
		self.players = {acc: {} for acc in self.accounts_list}
		self.replay = True
		
		
	def scan_blocks(self, cmd):
		print('reconnect')
		last_block = self.api.get_head_block() - 1 * 20		#aka 1 min	###
		print('replay... wait')
		self.replay = True
		
		while self.flag:
			time_start = time()
			head_block = self.api.get_head_block()

			for b in range(last_block, head_block):
				#print('next block', b)
				cmd(self.api.get_block(b))		#resolve_block
				
			###pprint(self.players)
			self.check_battles()
			
			time_end = time()
			d = round(time_end - time_start)
			tt = 3 - d
			tt = 0 if tt < 0 else tt
			last_block = head_block
			#print('sleep', tt, 'sec')
			self.replay = False
			sleep(tt)
		print('stop scan')	###
		
		
	def resolve_block(self, block):
		#self.timestamp = block["timestamp"].split('T')[1]
		try:
			self.timestamp = block["timestamp"]
		except:
			print('ERROR not correct block from b4')
			sleep(3)
		# check custom
		for tx in block["transactions"]:	###
			for op in tx["operations"]:
				if op[0] == 'custom_json':
					id = op[1].get('id')
					if id in self.sm_custom_cmd:
						player = op[1].get('required_posting_auths')[0]
						#player = op[1].get('required_posting_auths', [None])[0]
						data = json.loads(op[1].get('json', None))
						trx_id = tx.get('transaction_id')
						self.sm_custom_cmd[id](player, data, trx_id, self.timestamp)	#sm_find_match and other
		
		
	def sm_find_match(self, player, data, trx_id, timestamp):
		if data["match_type"] == 'Ranked':
			rating = self.sm.get_player_login(player)["rating"]
			liga = self.sm.is_rating(rating)
			if liga == self.liga_active:
				
				hide = '' if self.sm.is_submit_hashed_team(player) else '*'
				### Кто подал заявку на батл
				self.sm_find_match_list.append({"timestamp": timestamp.split('T')[1], "player": player, "liga": liga, "rating": rating,})
				if len(self.sm_find_match_list) > self.step_part:
					self.sm_find_match_list = self.sm_find_match_list[-self.step_part:]
						
				### Список trx_id ожидающих и не только
				self.sm_battles_list[trx_id] = {"player": player, "rating": rating, "timestamp": timestamp, "hide": hide}
				#print('add trx', trx_id)
				print(timestamp, player, liga, rating)
				
				
	def check_battles(self):
	
		list_for_del = []
		sm_players_list = []
		for trx_id, value in self.sm_battles_list.items():	### error
			battle = self.sm.get_battle_status(trx_id)
			if isinstance(battle, dict):
				status = int(battle["status"])
					
				if status == 0:
					sm_players_list.append([value["rating"], value["player"], value["timestamp"], value["hide"]])
				elif status == 1:
					
					#pprint(battle)	###
					
					player = battle["player"]
					opponent_player = battle["opponent_player"]
					timestamp = str(battle["match_date"])
					timestamp = timestamp.split('.')[0].split('T')[1]
					
					mana_cap = battle["mana_cap"]
					ruleset = battle["ruleset"]
					inactive = battle["inactive"]
					
					if player in self.players:
						self.players[player]["opponent_player"] = opponent_player
						self.players[player]["submit_hashed_team"] = self.sm.is_submit_hashed_team(opponent_player)						
						#print(player, 'VS', opponent_player)
					else:
						self.sm_vs_list.append([timestamp, player, 'VS', opponent_player])
						list_for_del.append(trx_id)
					
				elif status == 2:
					list_for_del.append(trx_id)

					player = battle["player"]
					opponent_player = battle["opponent_player"]
					timestamp = str(battle["created_date"])
					timestamp = timestamp.split('.')[0].split('T')[1]
					
					if player in self.players:
						print('round complete')
						self.players[player] = {}		# Обнуление
						#pprint(battle)
					self.sm_vs_list.append([timestamp, player, 'VS', opponent_player])
					
				else:
					list_for_del.append(trx_id)
					
					player = battle["player"]
					#pprint(battle)
					if player in self.players:
						print('round NOT complete')
						self.players[player] = {}
			
		if len(self.sm_vs_list) > self.step_part:
			self.sm_vs_list = self.sm_vs_list[-self.step_part:]
			
		for trx_id in list_for_del:
			self.sm_battles_list.pop(trx_id)
			
		self.sm_players_list = sm_players_list[:]
		self.sm_players_list.sort(reverse = True)
			
			
	def sm_submit_team(self, player, data, trx_id, timestamp):
		for acc in self.players:
			if player == self.players[acc].get("opponent_player", None):
				try:
					team = [data["summoner"]] + data["monsters"]
					csv = self.sm.resolve_team(team, player)
					print(self.timestamp, 'submit', player, csv)
				except:
					print(self.timestamp, 'hash team from', player)
					csv = 'hash'
				self.players[acc]["team"] = csv
		
		
	def sm_team_reveal(self, player, data, trx_id, timestamp):
		for acc in self.players:
			if player == self.players[acc].get("opponent_player", None):
				team = [data["summoner"]] + data["monsters"]
				csv = self.sm.resolve_team(team, player)
				print(self.timestamp, 'reveal', player, csv)
				self.players[acc]["team"] = csv
		
		
	
