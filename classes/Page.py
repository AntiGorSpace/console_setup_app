
class Page():
	page_label = 'label'
	select_label = 'select mode: '
	def __init__(self):
		self.options = {}
		self.before_add()

	def before_add(self):
		pass
	
	def after_return(self):
		pass

	def add_class(self, pager):
		self.pager = pager


	def select(self):
		input_text = input(self.select_label)
		input_text = input_text.strip()
		if input_text == 'b': 
			self.back()
			return
		self.selector(input_text)
	
	def selector(self, input_text:str):
		if input_text in self.options and 'page' in self.options[input_text]:
			self.pager.next_page(self.options[input_text]['page'])
		self.not_page_selector(input_text)

	def not_page_selector(self, input_text:str):
		pass

	def back(self):
		self.pager.prev_page()