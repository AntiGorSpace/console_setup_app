import sqlite3
import os

from typing import Any

class SQLite():
	db_path = None

	def __new__(cls, path:str=''):
		if not hasattr(cls, 'instance'):
			cls.instance = super(SQLite, cls).__new__(cls)
		return cls.instance
		
	def __init__(self, path:str=''):
		if not os.path.exists(f'{path}/data'): os.mkdir(f'{path}/data')
		if not self.db_path: self.db_path = f'{path}/data/base.sqlite'
		self.db_con = sqlite3.connect(self.db_path)
		self.db_cur = self.db_con.cursor()
	
	def execute(self, querry:str, values:dict={}, commit:bool=True, ret:bool=False, ret_many:bool=False)-> list[Any] | Any:
		self.db_cur.execute(querry, values)
		if commit: 
			self.db_con.commit()
		if ret:
			if ret_many: return self.db_cur.fetchall()
			else: return self.db_cur.fetchone()
		else: 
			return None
