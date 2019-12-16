# -*- coding: utf-8 -*-

from pprint import pprint
from time import sleep, time
import json
from datetime import date, datetime, timedelta

from requests import Session

from threading import Thread
from tkinter import *

from itertools import combinations

time_step = 2
n_step = 10
timeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'


class Http():

	http = Session()
	
	
class Root():

	root = None
	def run(self):
		self.root = Tk()
	

class Api(Http, Root):

	url = 'https://steemmonsters.com/'
	url_api = 'https://api.steemmonsters.io/'		# нет левела карт в коллекции юнита url
	url_png = 'https://d36mxiodymuqjm.cloudfront.net/'
	
	from pathlib import Path
	path_sm = str(Path(__file__).parent)
	path_img = path_sm + '/png/small/'
	
	ratings = {"chemp": [2800, 10000], "gold": [1900, 2799], "silver": [1000, 1899], "bronze": [100, 999]}
	colors = ['Red', 'Blue', 'Green', 'White', 'Black', 'Gold', 'Gray']
	state = ["attack", "ranged", "magic", "armor", "health", "speed"]
	png = {"0": 'cards_beta/', "1": 'cards_beta/', "3": 'cards_beta/', "2": 'cards_v2.2/', "4": 'cards_untamed/'}

	
	# Если нужно графическая оболочка, то необходимо выполнить load_cards
	
	battles = {}
	
	def __init__(self):
	
		print('load steemmonsters')
		data = self.settings()
		
		self.version = 	data["version"]
		self.rulesets = {rule["name"]: rule["description"] for rule in data["battles"]["rulesets"] if rule["active"]}
		### Aim True, Armored Up, Back to Basics, Broken Arrows, Earthquake, Fog of War, Healed Out, Keep Your Distance, Little League
		### Lost Legendaries, Melee Mayhem, Reverse Speed, Rise of the Commons, Silenced Summoners, Standard, Super Sneak, Taking Sides
		### Target Practice, Unprotected, Up Close & Personal, Weak Magic
		
		### summoner_rarity:summoner_level:monster_rarity - 1
		self.draft_liga = {
							"bronze": [3, 2, 2, 1],
							"silver": [5, 4, 3, 2],
							"gold": [8, 6, 5, 3],
							"chemp": [10, 8, 6, 4],
							}
		self.draft = {}
		for summoner_rarity in [1, 2, 3, 4]:
			self.draft[str(summoner_rarity)] = []
			for summoner_level in range(2 * (6 - summoner_rarity)):
				m = []
				for monster_rarity in [1, 2, 3, 4]:
					monster_level = (summoner_level + 1.001) * ( (6 / (6 - summoner_rarity)) - (monster_rarity / (6 - summoner_rarity)) )
					m.append(round(monster_level)) 
				self.draft[str(summoner_rarity)].append(m)
		##### ##### ##### ##### #####
		
		
		self.cards = self.get_card_details()
		self.card_names = {card["id"]: card["name"] for card in self.cards}
		
		#self.card_colors = {str(card["id"]): card["color"] for card in self.cards}
		self.card_colors = {card["name"]: card["color"] for card in self.cards}
		
		self.card_stats = {"Monster": {}, "Summoner": {}}
		for card in self.cards:
			self.card_stats[card["type"]][card["name"]] = card["stats"]
			for cmd in ['rarity', 'id', 'color']:
				self.card_stats[card["type"]][card["name"]][cmd] = card[cmd]
			self.card_stats[card["type"]][card["name"]]["monsters"] = self.draft[ str(card["rarity"]) ]
				
		self.card_mana = {}
		for card in self.cards:
			mana = card["stats"]["mana"]
			if isinstance(mana, list):
				mana = mana[0]
			#self.card_mana[ str(card["id"]) ] = mana
			self.card_mana[ card["name"] ] = mana
			
		#with open('quests.ini', 'w') as f:
		#	json.dump(data["quests"], f, ensure_ascii = False)
		
		# Цветовая гамма квестов
		self.quests = {	
						"Lyanna's Call": 'Green',
						"Rising Dead": 'Black',
						"Defend the Borders": 'White',
						"Pirate Attacks": 'Blue',
						"Stir the Volcano": 'Red',
						"Gloridax Revenge": 'Gold',
						"Proving Grounds": 'Tournament',
						"Stubborn Mercenaries": 'Gray',
							}
		
		print('version', self.version, self.url,  self.url_api, len(self.cards))
		#pprint(self.rulesets)
		
		# Фантомные карты
		self.starters = {}
		for card in self.cards:
			editions = card["editions"].split(',')
			if '1' in editions or '4' in editions:
				rare = card["rarity"]
				if rare in [1, 2]:
					name = card["name"]
					id = card["id"]
					self.starters[name] = '-'.join(['starter', str(id), '12345'])
		
		
		
	### TOTAL ###
	
	def settings(self):
		cmd = ''.join([self.url, 'settings'])
		return(self.get_response(cmd))
		
	def get_from_block(self, block_num):
		cmd = ''.join([self.url_api, 'transactions/history?from_block=', str(block_num)])
		return(self.get_response(cmd))
		
	def is_rating(self, rating):
		# По рейтингу возвращает тип лиги chemp, gold, silver, bronze или None
		# ratings = {"chemp": [2800, 10000], "gold": [1900, 2799], "silver": [1000, 1899], "bronze": [100, 999]}
		liga = [cmd for cmd, value in self.ratings.items() if value[0] <= int(rating) <= value[1]]
		return(liga[0] if liga else None)
	
	def get_transaction(self, trx):
		cmd = ''.join([self.url, 'transactions/lookup?trx_id=', trx])
		return(self.get_response(cmd))
	
	
	### PLAYER ###
	
	def get_collection(self, player):
		cmd = ''.join([self.url, 'cards/collection/', player])
		return(self.get_response(cmd))
		
	def get_player_collection(self, player):							### resolve {uid: {name:, level:}}
		return(self.resolve_collection(self.get_collection(player)))

	def get_player_login(self, player):
		cmd = ''.join([self.url, 'players/login?name=', player])
		return(self.get_response(cmd))
		
	def is_submit_hashed_team(self, player):
		# Скрывает ли юнит свои карты перед боем
		data = self.get_player_login(player)
		try:
			hide = data["settings"]["submit_hashed_team"]
		except:
			hide = False
		return(hide)
		
	def is_player_liga(self, player):
		# В какой лиге играет юнит
		data = self.get_player_login(player)
		return(self.is_rating(data["rating"]))
		
	def get_player_details(self, player):
		cmd = ''.join([self.url, 'players/details?name=', player])
		return(self.get_response(cmd))
		
	def get_player_quests(self, player):
	
		cmd = ''.join([self.url, 'players/quests?username=', player])
		tx = self.get_response(cmd)
		if isinstance(tx, list):
			data = tx[0]
			data["color"] = self.quests[data["name"]]
			data["time_for_new_quest"] = 23 * 60 - int((datetime.utcnow() - datetime.strptime(data["created_date"], timeFormat)).total_seconds() / 60)
		else:
			print('error quest', data)
			return False
		return(data)

	def is_player_quests(self, player):
		data = self.get_player_quests(player)
		if data:
			if int(data["completed_items"]) < int(data["total_items"]):
				return({data["name"]: int(data["completed_items"])})
		else:
			print('error quest', data)
		return False
		
	def get_player_all(self, player):
		login = self.get_player_login(player)
		rating = int(login["rating"])
		data = {
					"rating": rating,
					"hide": login["settings"].get("submit_hashed_team", None),
					"liga": self.is_rating(rating),
					"timestamp": time(),
					#"quest": self.is_player_quests(player),
					#"battle": None,
					#"collection": self.resolve_collection(self.get_collection(player)),
				}
		return(data)
		
	def get_player_dec(self, player):
		tx_acc = self.get_player_login(player)
		amount = 0
		for balance in tx_acc["balances"]:
			if balance["token"] == 'DEC':
				amount = float(balance["balance"])
		return(amount)
	
		
	### CARDS ###
	
	def get_card_details(self, reload = False):
		try:
			with open('get_details.json', 'r', encoding = 'utf8') as f:
				cards = json.load(f)
				#print('load card_details ok')
		except:
			reload = True				# not exist file
		if reload:
			cmd = ''.join([self.url, 'cards/get_details'])
			cards = self.get_response(cmd)
			for card in cards:
				id = card["id"]
			print('total cards', id)
			with open('get_details.json', 'w', encoding = 'utf8') as f:
				json.dump(cards, f, ensure_ascii = False)
		return(cards)
		
	def get_cards_stats(self):
		cmd = ''.join([self.url, 'cards/stats'])
		return(self.get_response(cmd))
		
	def get_cards_reward(self, trx_id):
		tx = self.get_transaction(trx_id)
		uids = []
		error = tx.get("error", None)
		if error:
			pprint(tx)
			return False
		else:
			data = json.loads(tx["trx_info"]["result"])
			
			for card in data:
				name = self.card_names[card["card_detail_id"]]
				gold = 'Gold' if card["gold"] else 'Common'
				print(gold, name, card["uid"])
				uids.append(card["uid"])

		return(uids)
		
		
	def find_cards(self, id):
		ids = ','.join(id) if isinstance(id, list) else id
		cmd = ''.join([self.url, 'cards/find?ids=', ids])
		return(self.get_response(cmd))
		
	def load_cards(self):
		print('load cards')
		### self.run()		# Инициализация Tkinter
		
		#self.cards = self.get_card_details()
		#self.card_names = {card["id"]: card["name"] for card in self.cards}
		self.card_files = {name: ''.join([self.path_img, name, '.png']) for id, name in self.card_names.items()}
		self.card_photos = {name: PhotoImage(file = file) for name, file in self.card_files.items()}
	
	def resolve_collection(self, collection):
		cards = {}
		for card in collection["cards"]:
			if not(card["market_id"]) and (not(card["delegated_to"]) or card["delegated_to"] == collection["player"]):
				cards[card["uid"]] = {"name": self.card_names[card["card_detail_id"]], "level": card["level"]}
		return(cards)
		
	def resolve_team(self, team, player):
		collection = self.get_player_collection(player)
		# name:level
		csv = [ ''.join([collection[card]["name"], ':', str(collection[card]["level"])]) for card in team]
		return(csv)
		
	def convert_team_to_csv(self, team, ruleset, mana_cap):
		liga = self.is_rating(team["rating"])
		if liga:
			try:
				color = team["color"]
				summoner = self.card_names[team["summoner"]["card_detail_id"]] + ':' + str(team["summoner"]["level"])
				monsters = [self.card_names[monster["card_detail_id"]] + ':' + str(monster["level"]) for monster in team["monsters"]]
				csv = ';'.join(ruleset + [liga, str(mana_cap), color, summoner] + monsters)
				return(csv)
			except:
				pprint(team)
				input('Error convert')
		return False
		
		
	### BATTLE ###
	
	def get_battle_history(self, player):
		cmd = ''.join([self.url, 'battle/history?player=', player])
		return(self.get_response(cmd))

	def get_opponent_colors(self, player):
		colors = {}
		data = self.get_battle_history(player)
		if data:
			for line in data["battles"]:
				if line["match_type"] == 'Ranked':
					details = json.loads(line["details"])
					type_result = details.get("type", None)
					if not type_result:
						for team_player, team_opponent in [["team1", "team2"], ["team2", "team1"] ]:
							team = details.get(team_player, None)
							if team:
								if team["player"] == player:
									color = team["color"]
									colors.setdefault(color, 0)
									colors[color] += 1
		return(colors)
	
	
	def get_battle_history_team(self, player):			# Доработать форматирования словаря
		data = self.get_battle_history(player)
		
		battles = []
		if data:
			for line in data["battles"]:
				battle = {cmd: line[cmd] for cmd in ['mana_cap', 'ruleset', 'inactive']}
				details = json.loads(line["details"])
				
				winner = details["winner"]	###
				loser = details["loser"]	###
				pre_battle = details["pre_battle"]	###
				
				#seed rounds pre_battle
				
				type_result = details.get("type", None)
				if not type_result:
					for team_player, team_opponent in [["team1", "team2"], ["team2", "team1"] ]:
						team = details.get(team_player, None)
						if team:
							if team["player"] == player:
								login, liga = team["player"], self.is_rating(team["rating"])
								battle["liga"] = liga
								battle["color"] = liga
								print(team["color"])
								input()
						
						
							#oppenent_color = result["details"][team_opponent]["color"]
							#team_csv = self.convert_team_to_csv(team)
					'''
					for type_team in ['team1', 'team2']:
						team = details.get(type_team, None)
						if team:
							login, liga = team["player"], self.is_rating(team["rating"])
							battle[type_team] = {"player": login, "liga": liga}
							battle["liga"] = liga
							
							summoner = [self.card_names[team["summoner"]["card_detail_id"]] + ':' + str(team["summoner"]["level"])]
							monsters = [self.card_names[m["card_detail_id"]] + ':' + str(m["level"]) for m in team["monsters"]]
							team = summoner + monsters
							check_team = self.check_rarity(team, liga)
							battle[type_team]["combo"] = check_team
							if check_team != team:
								print(team)
								print(check_team)
					'''
					battles.append(battle)
					
		return(battles)
		
	def get_battle_result(self, id):
		cmd = ''.join([self.url, 'battle/result?id=', str(id)])
		return(self.get_response(cmd))
		
	def get_battle_status(self, id):
		cmd = ''.join([self.url, 'battle/status?id=', str(id)])
		return(self.get_response(cmd))
		
		
	def check_rarity(self, combo, liga):
	
		check = []
		
		name, lvl = combo[0].split(':')
		rarity = self.card_stats["Summoner"][name]["rarity"]
		high_lvl = self.draft_liga[liga][rarity - 1]
		lvl = high_lvl if int(lvl) > high_lvl else int(lvl)
		draft = self.card_stats["Summoner"][name]["monsters"][lvl - 1]
		
		check.append(name + ':' + str(lvl))
		
		monsters = combo[1:]
		for monster in monsters:
			name, lvl = monster.split(':')
			rarity = self.card_stats["Monster"][name]["rarity"]
			high_lvl = draft[rarity - 1]
			lvl = high_lvl if int(lvl) > high_lvl else int(lvl)
			check.append(name + ':' + str(lvl))
			
		return(check)
		
	### Aim True, Broken Arrows, Earthquake, Keep Your Distance, Little League, Lost Legendaries, Melee Mayhem, Reverse Speed, 
	### Rise of the Commons, Silenced Summoners, Standard, Taking Sides, Up Close & Personal, Weak Magic
		
	def check_stats(self, stats, abilities, ruleset):
		### Armored Up, Back to Basics, Fog of War, Healed Out, Super Sneak, Target Practice, Unprotected,
		#state = ["attack", "ranged", "magic", "armor", "health", "speed"]
		
		if 'Armored Up' in ruleset:
			stats[self.state.index('armor')] += 2
		if 'Back to Basics' in ruleset:
			abilities = []
		if 'Fog of War' in ruleset:
			if 'Sneak' in abilities:
				abilities.remove('Sneak')
			if 'Snipe' in abilities:
				abilities.remove('Snipe')
		if 'Healed Out' in ruleset:
			if 'Heal' in abilities:
				abilities.remove('Heal')
			if 'Tank Heal' in abilities:
				abilities.remove('Tank Heal')
		if 'Super Sneak' in ruleset:
			if stats[self.state.index('attack')] > 0:
				abilities.append('Sneak')
		if 'Target Practice' in ruleset:
			if (stats[self.state.index('ranged')] > 0) or (stats[self.state.index('magic')] > 0):
				abilities.append('Snipe')
		if 'Unprotected' in ruleset:
			if 'Protect' in abilities:
				abilities.remove('Protect')
			stats[self.state.index('armor')] = 0			
			
		return({"stats": stats, "abilities": abilities})

	def check_ruleset(self, ruleset):
		#Earthquake, Healed Out, Reverse Speed
		check = ruleset
		if 'Earthquake' in ruleset and 'Healed Out' in ruleset:
			check = 'Earthquake|Healed Out'
		if 'Earthquake' in ruleset and 'Reverse Speed' in ruleset:
			check = 'Earthquake|Reverse Speed'
		if 'Healed Out' in ruleset and 'Reverse Speed' in ruleset:
			check = 'Healed Out|Reverse Speed'
		return(check)
		
	def check_color(self, combo):
	
		cards = [i.split(':')[0] for i in combo]
		color = self.card_colors[cards[0]]
		if color == 'Gold':
			for card in cards[1:]:
				monster_color = self.card_colors[card]
				if monster_color in ['Red', 'Blue', 'Green', 'White', 'Black']:
					color = color + '|' + monster_color
					break
		return(color)
		
	
	### MARKET ###
		
	def get_price(self):
		data = self.settings()
		if data:
			price = {"SBD": data["sbd_price"], "STEEM": data["steem_price"]}
			return(price)
		return False
		
	def get_for_sale(self):
		cmd = ''.join([self.url, 'market/for_sale'])
		return(self.get_response(cmd))
		
	def get_market_for_sale_grouped(self):
		cmd = ''.join([self.url, 'market/for_sale_grouped'])
		return(self.get_response(cmd))
		
	### END ###
		
		
	def get_response(self, cmd):
	
		n = 0
		while n < n_step:
			response = self.http.get(cmd)
			
			try:
				if str(response) == '<Response [200]>':
					try:
						return(response.json())
					except:
						return(response)
			except:
				print('??? ERROR in SteemMonstersApi', n)
			
			sleep(time_step)
			n += 1
		return False
		
