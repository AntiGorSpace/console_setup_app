import os

from classes.Page import Page

class Pager():
	def __new__(cls):
		if not hasattr(cls, 'instance'):
			cls.instance = super(Pager, cls).__new__(cls)
		return cls.instance
		
	def __init__(self):
		self.pages = []
		self.init_options()

	def init_options(self):
		pass
	
	def next_page(self, page:Page):
		page.add_class(self)
		self.pages.append(page)
		self.render()

	def prev_page(self):
		self.pages.pop()
		self.render()
	
	def render(self):
		while True:
			if len(self.pages) == 0: break
			active_page = self.pages[-1]
			active_page.after_return()
			os.system('clear')
			print(active_page.page_label, end='\n\n')
			print()
			for key in active_page.options:
				print(key, active_page.options[key]['name'])
			
			if len(self.pages)==1:
				print('\nb', 'close')
			else:
				print('\nb', 'back')
			active_page.select()