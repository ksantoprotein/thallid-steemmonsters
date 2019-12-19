# -*- coding: utf-8 -*-

from pprint import pprint
from time import sleep, time
import json

from tsmbase.sm import Api as SteemMonstersApi
from tsteembase.api import Api

class Deep():
	
	decks = {}	### save load	
				### {team_csv, {"win": 0, "total": 0 and colors}}
				### team_csv = ','.join([ruleset, liga, str(mana_cap), color, summoner] + monsters)
				### summoner = level:name
				
	files = {
				"state_main": 'moon.json',
				"state_bak": 'moon.bak',
				"state_csv": 'moon.csv',
				"state_csv_mini": 'moon_mini.csv',
			}

	types = ['sm_battle', 'sm_start_quest', 'find_match', 'sm_submit_team', 'sm_team_reveal', 'token_transfer', 'sm_claim_reward', 'sm_combine_all',
				'gift_packs', 'market_purchase', 'sm_combine_cards', 'open_pack', 'sm_sell_cards', 'sm_cancel_match', 'sm_surrender',
				'sm_market_purchase', 'sm_gift_cards', 'guild_contribution', 'enter_tournament', 'sm_refresh_quest', 'sm_market_sale',
				'purchase_orbs', 'delegate_cards', 'update_price', 'sm_cancel_sell', 'burn_cards', 'sm_card_award', 'sm_pack_purchase',
				'undelegate_cards', 'join_guild', 'guild_accept', 'guild_promote', 'purchase_item']

			
	def __init__(self, double = False, csv = False):
		
		self.last_b = 30000000
		self.double = double
		self.csv = csv
		
		self.sm = SteemMonstersApi()
		self.api = Api()
		
		self.load_state()

		
	##### ##### ##### ##### #####
	
	def load_state(self):
		try:
			with open(self.files["state_main"], 'r', encoding = 'utf8') as f:
				self.state = json.load(f)
				print('load state ok')
		except:
			# not exist or bad file, load copy in *.bak
			try:
				with open(self.files["state_bak"], 'r', encoding = 'utf8') as f:
					self.state = json.load(f)
					print('load state bak ok')
			except:
				self.state = {"last_block": self.last_b, "decks": {liga: {} for liga in self.sm.ratings}}
				self.save_state()
				print('genesis new state')
				
	
	def save_state(self):
		self.decks = {}
		print('save state')
		with open(self.files["state_main"], 'w', encoding = 'utf8') as f:
			json.dump(self.state, f, ensure_ascii = False)
		if self.double:
			with open(self.files["state_bak"], 'w', encoding = 'utf8') as f:
				json.dump(self.state, f, ensure_ascii = False)
		if self.csv:
			with open(self.files["state_csv"], 'w', encoding = 'utf8') as f:
				for liga, v1 in self.state["decks"].items():
					for ruleset, v2 in v1.items():
						for mana_cap, v3 in v2.items():
							for team, v4 in v3.items():
								players = []
								for player, v5 in v4["player"].items():
									p5 = ':'.join([player, str(v5["win"]), str(v5["lose"])])
									players.append(p5)
								p4 = ','.join(players)
								p3 = ':'.join([str(v4[cmd]) for cmd in ["win", "total", "Red", "Blue", "Green", "White", "Black", "Gold"]])
								line = ';'.join([p3, p4, liga, ruleset, mana_cap, team])
								f.write(line + '\n')
			
		print('end save state')
		
	##### ##### ##### ##### #####
	
	def load_moon(self, login):
	
		collection = self.sm.get_player_collection(login)
		
		self.moon_cards = {}
		for uid, card in collection.items():
			name, level = card["name"], card["level"]
			self.moon_cards.setdefault(name, {"level": level, "uid": uid})
			if level > self.moon_cards[name]["level"]:
				self.moon_cards[name] = {"level": level, "uid": uid}

		self.moon_decks = {liga: {} for liga in self.sm.ratings}
		for liga, v1 in self.state["decks"].items():
			for ruleset, v2 in v1.items():
				for mana_cap, v3 in v2.items():
					for team, v4 in v3.items():
						color, *combo = team.split(';')
						
						win, total = v4["win"], v4["total"]
					
						for i in range(len(self.sm.colors) - 1):
							opponent_color = self.sm.colors[i]
							win_color = v4[opponent_color]
							k_moon = round((win_color / total) * (win / total) * (win + total), 3)
						
							self.moon_decks[liga].setdefault(ruleset, {})
							self.moon_decks[liga][ruleset].setdefault(mana_cap, {})
							self.moon_decks[liga][ruleset][mana_cap].setdefault(opponent_color, {})
							self.moon_decks[liga][ruleset][mana_cap][opponent_color].setdefault(color, {"team": ['xxx'], "k_moon": -100, "best": combo, "k_best": k_moon})
							if k_moon > self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["k_best"]:
								self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["k_best"] = k_moon
								self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["best"] = combo
							
							flag = True
							
							for card in combo:
								name, level = card.split(':')
								level = int(level)
								if name in self.moon_cards:
									for k in range(level - self.moon_cards[name]["level"]):
										k_moon = round(k_moon * 0.75, 3)
								else:
									flag = False
									break

							if flag:
								
								if k_moon > self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["k_moon"]:
									self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["k_moon"] = k_moon
									self.moon_decks[liga][ruleset][mana_cap][opponent_color][color]["team"] = combo
		
	##### ##### ##### ##### #####
	
	def upload(self):
	
		block_end = self.api.get_irreversible_block()
		print('update block_end:', block_end, 'last block:', self.state["last_block"])

		n = 0
		s = 0
		
		while True:
		
			ids = []
			
			print('start from', self.state["last_block"], n, s, 'update block_end:', block_end)
			data = self.sm.get_from_block(self.state["last_block"])

			for line in data:
			
				if line["type"] == 'sm_battle':
					block_num = line["block_num"]
				
					if line["error"] != None or line["success"] != True:
						line.pop("data")
						line.pop("result")
						
						pprint(line)
						input('next?')
					else:
						data = json.loads(line.pop("data"))
						result = json.loads(line.pop("result"))
						
						if result["match_type"] == 'Ranked':
							mana_cap = str(result["mana_cap"])
							ruleset = self.sm.check_ruleset(result["ruleset"])
							winner = result["winner"]
							players = result["players"]

							if result["id"] not in ids:
								liga = self.sm.is_rating(players[0]["initial_rating"])
								if liga:		# Отсеиваем новичков >= 100
									
									if not result["details"].get("type", None):
										
										for team_player, team_opponent in [["team1", "team2"], ["team2", "team1"] ]:
											team = result["details"][team_player]
											if team:
												oppenent_color = result["details"][team_opponent]["color"]
												team_csv = self.convert_team_to_csv(team)
												if team_csv:
													self.state["decks"][liga].setdefault(ruleset, {})
													self.state["decks"][liga][ruleset].setdefault(mana_cap, {})
													self.state["decks"][liga][ruleset][mana_cap].setdefault(team_csv, {
															"win": 0, "total": 0, 
															"Red": 0, "Blue": 0, "Green": 0, "White": 0, "Black": 0, "Gold": 0,
															"player": {}})
													self.state["decks"][liga][ruleset][mana_cap][team_csv]["player"].setdefault(team["player"], {
															"win": 0, "lose": 0})
													if winner == team["player"]:
														self.state["decks"][liga][ruleset][mana_cap][team_csv]["win"] += 1
														self.state["decks"][liga][ruleset][mana_cap][team_csv][oppenent_color] += 1
														self.state["decks"][liga][ruleset][mana_cap][team_csv]["player"][team['player']]["win"] += 1
													else:
														self.state["decks"][liga][ruleset][mana_cap][team_csv][oppenent_color] -= 1
														self.state["decks"][liga][ruleset][mana_cap][team_csv]["player"][team['player']]["lose"] += 1
													self.state["decks"][liga][ruleset][mana_cap][team_csv]["total"] += 1
										ids.append(result["id"])
										n += 1
			
						
			self.state["last_block"] = line["block_num"]	###
			
			s += 1
			if s >= 1000:
				self.save_state()
				s = 0
			
			if self.state["last_block"] > block_end:
				self.save_state()
				break
		return
		
		
	def convert_team_to_csv(self, team):
		liga = self.sm.is_rating(team["rating"])
		if liga:
			try:
				summoner = self.sm.card_names[team["summoner"]["card_detail_id"]] + ':' + str(team["summoner"]["level"])
				monsters = [self.sm.card_names[monster["card_detail_id"]] + ':' + str(monster["level"]) for monster in team["monsters"]]
				combo = self.sm.check_rarity([summoner] + monsters, liga)
				color = self.sm.check_color(combo)
				csv = ';'.join([color] + combo)
				return(csv)
			except:
				pprint(team)
				input('Error convert')
		return False
		
