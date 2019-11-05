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
	
	from pathlib import Path
	path_sm = str(Path(__file__).parent)
	path_img = path_sm + '/png/small/'
	
	ratings = {"chemp": [2800, 10000], "gold": [1900, 2799], "silver": [1000, 1899], "bronze": [100, 999]}
	colors = ['Red', 'Blue', 'Green', 'White', 'Black', 'Gold']
	
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
		
		self.cards = self.get_card_details()
		self.card_names = {card["id"]: card["name"] for card in self.cards}
		
		self.quests = {}		# Цветовая гамма квестов
		for quest in data["quests"]:
			self.quests[quest["name"]] = quest["data"]["color"]
		
		print('version', self.version, self.url,  self.url_api, len(self.cards))
		#pprint(self.rulesets)
		
		
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

		return True
		
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

	def get_battle_history_team(self, player):			# Доработать форматирования словаря
		data = self.get_battle_history(player)
		battles = []
		if data:
			for line in data["battles"]:
				battle = {cmd: line[cmd] for cmd in ['mana_cap', 'ruleset', 'inactive']}
				details = json.loads(line["details"])
				type_result = details.get("type", None)
				if not type_result:
					for type_team in ['team1', 'team2']:
						team = details.get(type_team, None)
						if team:
							team["player"] == player
							battle["color"] = team["color"]
							summoner = [{ "name": self.card_names[team["summoner"]["card_detail_id"]], "level": team["summoner"]["level"]}]
							monsters = [{ "name": self.card_names[m["card_detail_id"]], "level": m["level"]} for m in team["monsters"]]
							battle["team"] = summoner + monsters
							battles.append(battle)
							break
		return(battles)
		
	def get_battle_result(self, id):
		cmd = ''.join([self.url, 'battle/result?id=', str(id)])
		return(self.get_response(cmd))
		
	def get_battle_status(self, id):
		cmd = ''.join([self.url, 'battle/status?id=', str(id)])
		return(self.get_response(cmd))

	
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
					return(response.json())
			except:
				print('??? ERROR in SteemMonstersApi', n)
			
			sleep(time_step)
			n += 1
		return False
		
