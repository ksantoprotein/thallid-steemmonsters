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
				color = team["color"]
				summoner = self.sm.card_names[team["summoner"]["card_detail_id"]] + ':' + str(team["summoner"]["level"])
				monsters = [self.sm.card_names[monster["card_detail_id"]] + ':' + str(monster["level"]) for monster in team["monsters"]]
				combo = self.sm.check_rarity([summoner] + monsters, liga)
				csv = ';'.join([color] + combo)
				return(csv)
			except:
				pprint(team)
				input('Error convert')
		return False
		

	def resolve_players(self, players):
	
		for player, oppenent in [ [0, 1], [1, 0]]:
			player_name = players[player]["name"]
			oppenent_name = players[oppenent]["name"]
			
			d = players[player]["initial_rating"] - players[player]["final_rating"]
			win, lose = [1, 0] if d > 0 else [0, 1]
			
			self.state["players"].setdefault(player_name, {})
			self.state["players"][player_name].setdefault(oppenent_name, [0, 0])
			self.state["players"][player_name][oppenent_name][0] += win
			self.state["players"][player_name][oppenent_name][1] += lose
			
			d_rating = players[player]["initial_rating"] - players[oppenent]["initial_rating"]
			if d_rating >=0:
				rating = str(int(d_rating / 5) * 5)		# округление до шага 5
				self.state["ratings"].setdefault(rating, [0, 0])
				self.state["ratings"][rating][0] += win
				self.state["ratings"][rating][1] += lose
			
		return
		
		
		