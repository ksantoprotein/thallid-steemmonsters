# -*- coding: utf-8 -*-

from pprint import pprint
from time import sleep, time, strptime, mktime
import json

from threading import Thread
from tkinter import *

from tsmbase.sm import Api as SteemMonstersApi
#from tsteembase.api import Api as SteemApi
import tsteembase.storage as storage

from tsmbase.findmatch import FindMatch

from datetime import datetime, timedelta
time_format = '%Y-%m-%dT%H:%M:%S'


class Explorer():

	color_stop = 'red'
	color_go = 'green'
	color_opponent_hide = 'red'
	color_opponent_not_hide = 'cyan'

	scan_sleep = 0.5
	sleep_team_opponent = 5
	
	
	def __init__(self):
		
		self.sm = SteemMonstersApi()
		#self.api = SteemApi()
		self.fm = FindMatch()
		self.root = Tk()
		
		self.flag = False
		self.team_opponent = {}
		
		with open('accounts.ini', 'r') as f:
			raw = f.read()
		self.fm.accounts_list = raw.replace('\n', ' ').split()
		print('load accounts:', self.fm.accounts_list)
		
		self.fm.nodes_list = storage.nodes
		print('load nodes:', self.fm.nodes_list)
		
		self.root.title('Explorer SteemMonsters')
		self.root.minsize(700, 450)
		self.root.maxsize(700, 450)
		
		self.load_liga()
		self.load_find_match()
		self.load_vs()
		self.load_unit()
		
		self.sm.load_cards()
		
		self.root.mainloop()
		
		
	def scan(self):
	
		while self.flag:
		
			### find_match_label ###
			#print(self.fm.sm_find_match_list)
			raw_text = [' '.join([i["timestamp"], str(i["rating"]), i["player"]]) for i in self.fm.sm_find_match_list]
			new_text = '\n'.join(raw_text)
			self.find_match_label["text"] = new_text if not self.fm.replay else 'replay'
			
			### vs_label ###
			raw_text = [' '.join(i) for i in self.fm.sm_vs_list]
			new_text = '\n'.join(raw_text)
			self.vs_label["text"] = new_text if not self.fm.replay else 'replay'
			
			### pool_label ###
			now = int(mktime(strptime(self.fm.timestamp, time_format)))
			raw_text = [' '.join(['{:>3}'.format(str(now - int(mktime(strptime(i[2], time_format))))), 'sec', str(i[0]), i[1], i[3]]) for i in self.fm.sm_players_list]
			new_text = '\n'.join(raw_text)
			self.pool_label["text"] = new_text if not self.fm.replay else 'replay'
			self.pool_label["bg"] = self.color_stop if len(self.fm.sm_players_list) > 0 or self.fm.replay else self.color_go

			### title ###
			utc_unit = int(self.utc.get().replace('UTC', ''))
			self.root.title(' '.join([str(int(time()) - now - utc_unit * 60 * 60), 'sec delta', 'Explorer SteemMonsters']))
			
			### unit_opponent_label ###
			player = self.unit.get()
			#self.fm.players["player"] = player
			
			opponent_player = self.fm.players[player].get("opponent_player", None)
			if opponent_player:
				self.unit_opponent_label["text"] = opponent_player
				try:
					bg = self.color_opponent_hide if self.fm.players[player]["submit_hashed_team"] else self.color_opponent_not_hide
				except:
					### point for error
					bg = 'black'
					##pprint(self.fm.players)
					
				self.unit_opponent_label["bg"] = bg
			else:
				self.unit_opponent_label["text"] = ''
				self.unit_opponent_label["bg"] = 'white'

			### team_opponent ###
			opponent_team = self.fm.players[player].get("team", None)
			r = 25
			x = 100
			y = int(x * 420 / 300)
			
			if opponent_team:
				if opponent_team == 'hash':
					hidden = 'HIDDEN'
					for n in range(len(list(hidden))):
						self.team_opponent[n] = {	"image": Label(self.unit_opponent_frame), 
													"level": Label(self.unit_opponent_frame, text = hidden[n], font = 'Arial 40'),}
						self.team_opponent[n]["image"].place(x = 0 + n * x, y = 0, width = x, height = y)										
						self.team_opponent[n]["level"].place(x = 0 + n * x, y = 0, width = x, height = y)												
						
				else:
					for n in range(len(opponent_team)):
						name, level = opponent_team[n].split(':')
						
						self.team_opponent[n] = {	"image": Label(self.unit_opponent_frame, image = self.sm.card_photos[name]),
													"level": Label(self.unit_opponent_frame, text = level, font = 'Arial 18'),}
						self.team_opponent[n]["image"].place(x = 0 + n * x, y = 0, width = x, height = y)										
						self.team_opponent[n]["level"].place(x = 50 - 0.5 * r + n * x, y = 140 - r - 5, width = 25, height = 25)												
						
				sleep(self.sleep_team_opponent)
				
				# kill widgets
				for n in range(len(self.team_opponent)):
					self.team_opponent[n]["image"].destroy()												
					self.team_opponent[n]["level"].destroy()												
					self.team_opponent.pop(n)
					#self.team_opponent = {}
					#print('kill')

			sleep(self.scan_sleep)
			
		self.fm.stop()
			
			
	##### ##### ##### ##### #####

	def cmd_button_start(self):
	
		self.fm.node = self.node.get()

		self.button_start["state"] = DISABLED
		self.button_stop["state"] = NORMAL
		self.node_entry["state"] = DISABLED
		for liga in self.liga_radiobuttons:
			self.liga_radiobuttons[liga]["state"] = DISABLED
			
		self.flag = True
		sm_thread = Thread(target = self.scan, daemon = True)
		sm_thread.start()
		print(self.liga_var.get())
		self.fm.run(self.liga_var.get())
		
		
	def cmd_button_stop(self):
		self.button_start["state"] = NORMAL
		self.button_stop["state"] = DISABLED
		self.node_entry["state"] = NORMAL
		for liga in self.liga_radiobuttons:
			self.liga_radiobuttons[liga]["state"] = NORMAL
		print('end work')
		self.flag = False
			
		
	def load_liga(self):
		
		self.liga_var = StringVar()
		self.liga_var.set('chemp')
		self.liga_radiobuttons = {}
		
		menu_liga = [ ['Diamond+Champion', 'chemp'], ['Gold', 'gold'], ['Silver', 'silver'], ['Bronze', 'bronze'] ]
		liga_frame = LabelFrame(self.root, width = 200, height = 250, text = 'Your League')	#, bg = "green"
		n = 0
		for text, liga in menu_liga:
			self.liga_radiobuttons[liga] = Radiobutton(liga_frame, text = text, variable = self.liga_var, value = liga)
			self.liga_radiobuttons[liga].place(x = 0, y = n * 25)
			n += 1
		
		self.button_start = Button(liga_frame, text = 'Start', width = 10, command = self.cmd_button_start)
		self.button_start.place(x = 5, y = 100)
		self.button_stop = Button(liga_frame, text = 'Stop', width = 10, state = DISABLED, command = self.cmd_button_stop)
		self.button_stop.place(x = 100, y = 100)
		
		self.pool_label = Label(liga_frame, justify = LEFT, anchor = 'nw', bg = "red")
		self.pool_label.place(x = 5, y = 130, width = 185, height = 95)
		
		liga_frame.place(x = 0, y = 0)
		

	def load_find_match(self):
		find_match_frame = LabelFrame(self.root, width = 250, height = 250, text = 'Find Match')	#
		self.find_match_label = Label(find_match_frame, justify = LEFT, anchor = 'nw')	#, bg = "green"
		self.find_match_label.place(x = 5, y = 0, width = 235, height = 225)
		find_match_frame.place(x = 200, y = 0)
		
		
	def load_vs(self):
		vs_frame = LabelFrame(self.root, width = 250, height = 250, text = 'Battles')	#, bg = "green"
		self.vs_label = Label(vs_frame, justify = LEFT, anchor = 'nw')					#, bg = "green"
		self.vs_label.place(x = 5, y = 0, width = 235, height = 225)
		vs_frame.place(x = 450, y = 0)
		
		
	def load_unit(self):
		unit_frame = LabelFrame(self.root, width = 700, height = 200, text = 'Your VS Opponent')	#, bg = "green"
		
		#self.unit_entry = Entry(unit_frame, width = 200)
		#self.unit_entry.place(x = 5, y = 0, width = 185, height = 25)
		self.unit = StringVar(value = self.fm.accounts_list[0])
		self.unit_entry = OptionMenu(unit_frame, self.unit, *self.fm.accounts_list)
		self.unit_entry.place(x = 5, y = 0, width = 150, height = 25)
		
		#self.unit_vs_label = Label(unit_frame, text = 'VS')
		#self.unit_vs_label.place(x = 150, y = 0, width = 150, height = 25)
		
		self.utc = StringVar(value = 'UTC+3')
		utc_list = ['UTC' + str(n) for n in range(-12, 13)]
		self.utc_optionmenu = OptionMenu(unit_frame, self.utc, *utc_list)
		self.utc_optionmenu.place(x = 155, y = 0, width = 100, height = 25)
		
		self.node = StringVar(value = self.fm.nodes_list[0])
		self.node_entry = OptionMenu(unit_frame, self.node, *self.fm.nodes_list)
		self.node_entry.place(x = 255, y = 0, width = 190, height = 25)
		
		self.unit_opponent_label = Label(unit_frame, justify = LEFT, anchor = 'nw', bg = "white")		#
		self.unit_opponent_label.place(x = 455, y = 0, width = 235, height = 25)
		
		self.unit_opponent_frame = Frame(unit_frame, width = 695, height = 145)
		self.unit_opponent_frame.place(x = 0, y = 35)
		
		unit_frame.place(x = 0, y = 250)
		
			
		
