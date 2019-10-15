# -*- coding: utf-8 -*-

from pprint import pprint
from time import sleep, time
import json

from tsmbase.sm import Api as SteemMonstersApi
from tsteembase.api import Api

class Deep():
	
	decks = {}	### save load	
				### {team_csv, {"win": 0, "total": 0}}
				### team_csv = ','.join([liga, ruleset, str(mana_cap), color, summoner] + monsters)
				### summoner = level:name
				
	files = {
				"state_main": 'combo.json',
				"state_bak": 'combo.bak',
				"state_csv": 'combo.csv',
				"state_csv_mini": 'combo_mini.csv',
			}

	types = ['sm_battle', 'sm_start_quest', 'find_match', 'sm_submit_team', 'sm_team_reveal', 'token_transfer', 'sm_claim_reward', 'sm_combine_all',
				'gift_packs', 'market_purchase', 'sm_combine_cards', 'open_pack', 'sm_sell_cards', 'sm_cancel_match', 'sm_surrender',
				'sm_market_purchase', 'sm_gift_cards', 'guild_contribution', 'enter_tournament', 'sm_refresh_quest', 'sm_market_sale',
				'purchase_orbs', 'delegate_cards', 'update_price', 'sm_cancel_sell', 'burn_cards', 'sm_card_award', 'sm_pack_purchase',
				'undelegate_cards', 'join_guild', 'guild_accept', 'guild_promote', 'purchase_item']

			
	def __init__(self):
		
		self.last_b = 30000000
		
		self.sm = SteemMonstersApi()
		self.api = Api()
		
		self.load_state()
		
		print('last block', self.state["last_block"])

		
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
				self.state = {"last_block": self.last_b, "decks": {}}
				self.save_state()
				print('genesis new state')
				
	
	def save_state(self):
		self.decks = {}
		print('save state')
		with open(self.files["state_main"], 'w', encoding = 'utf8') as f:
			json.dump(self.state, f, ensure_ascii = False)
		with open(self.files["state_bak"], 'w', encoding = 'utf8') as f:
			json.dump(self.state, f, ensure_ascii = False)
		print('end save state')
		print('save decks')
		with open(self.files["state_csv"], 'w') as f:
			f.write(','.join(['Win', 'Total', 'Ruleset1', 'Ruleset2', 'Liga', 'Mana_cap', 'Color', 'Summoner']) + '\n')
			for key, value in self.state["decks"].items():
				f.write(','.join([str(value["win"]), str(value["total"]), key]) + '\n')
				
				new_key = ';'.join([i.split(':')[0] for i in key.split(',')])
				self.decks.setdefault(new_key, {"win": 0, "total": 0})
				self.decks[new_key]["win"] += value["win"]
				self.decks[new_key]["total"] += value["total"]
			
		with open(self.files["state_csv_mini"], 'w') as f:
			f.write(';'.join(['Win', 'Total', 'Ruleset1', 'Ruleset2', 'Liga', 'Mana_cap', 'Color', 'Summoner']) + '\n')
			for key, value in self.decks.items():
				f.write(';'.join([str(value["win"]), str(value["total"]), key]) + '\n')
			
		print('end save decks')
		
		
	##### ##### ##### ##### #####
		

		
	def upload(self):
	
		block_end = self.api.get_irreversible_block()
		print('update block_end', block_end)

		n = 0
		s = 0
		
		while True:
		
			ids = []
			
			print('start from', self.state["last_block"], n, s)
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
							mana_cap = result["mana_cap"]
							# Новые правила двойных боев
							ruleset = result["ruleset"].split('|')	if '|' in result["ruleset"] else [result["ruleset"], '-']
							winner = result["winner"]
							players = result["players"]

							if result["id"] not in ids:
								if players[0]["initial_rating"] >= 100:		# Отсеиваем новичков
									#self.resolve_players(players)
									
									if not result["details"].get("type", None):
										
										for t in ["team1", "team2"]:
											team = result["details"][t]
											if team:
												team_csv = self.sm.convert_team_to_csv(team, ruleset, mana_cap)
												if team_csv:
													self.state["decks"].setdefault(team_csv, {"win": 0, "total": 0})
													if winner == team['player']:
														self.state["decks"][team_csv]["win"] += 1
													self.state["decks"][team_csv]["total"] += 1
										
										ids.append(result["id"])
										n+=1
			
						
			self.state["last_block"] = line["block_num"]	###
			
			s += 1
			if s >= 100:
				self.save_state()
				s = 0
			
			if self.state["last_block"] > block_end:
				self.save_state()
				break
		return
		

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
		
		
		