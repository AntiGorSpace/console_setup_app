import os
import subprocess

from classes.Page import Page
from classes.SQLite import SQLite


# os.system('apt install wireguard')

# os.system('chmod 600 /etc/wireguard/privatekey')
# os.system('echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf')
# os.system('sysctl -p')
# os.system('systemctl enable wg-quick@wg0.service')
# os.system('systemctl start wg-quick@wg0.service')

class WGUser():
	id:int
	login:str
	public:str
	private:str
	def __init__(self, id:int, login:str, public:str, private:str):
		self.id = id
		self.login = login
		self.public = public
		self.private = private

class WGMain():
	base_path = '/etc/wireguard'
	wg_changes = False
	server_ip = subprocess.check_output(["curl", "ifconfig.me"]).decode('UTF-8')

	def __new__(cls):
		if not hasattr(cls, 'instance'):
			cls.instance = super(WGMain, cls).__new__(cls)
		return cls.instance

	def __init__(self):
		if not os.path.exists(f'{self.base_path}/temp'): os.mkdir(f'{self.base_path}/temp')
		self.database = SQLite()

	def init_table(self):
		self.database.execute(
			"CREATE TABLE if not exists wire_guard_keys(id unique primary key, login unique, public, private)"
		)
		login = 'server'
		public, private = self.create_keys(login)
		self.database.execute(
			"INSERT OR IGNORE INTO wire_guard_keys(id, login, public, private) VALUES (0, :login, :public, :private);",
			{
				'login' : login,
				'public' : public,
				'private' : private
			}
		)

	def create_keys(self, login):
		pr_path = f'{self.base_path}/temp/{login}_privatekey'
		pb_path = f'{self.base_path}/temp/{login}_publickey'
		os.system(f'wg genkey | tee {pr_path} | wg pubkey | tee {pb_path}')
		def get_key(path):
			f = open(path)
			key = f.readline().replace('\n','')
			f.close()
			os.remove(path)
			return key
		self.wg_changes = True
		return get_key(pb_path), get_key(pr_path)

	def row_in_obj(self, row)->WGUser:
		return WGUser(row[0], row[1], row[2], row[3])

	def create_user(self, login:str, id:int|None = None):
		user = self.database.execute('select 1 from wire_guard_keys where login=:login', {'login':login}, ret=True)
		if user:
			self.select_label = 'login exist, write another: '
			return
		row_id = self.database.execute('''
			WITH RECURSIVE generate_series AS (
				SELECT
					1 as value
				UNION ALL
				SELECT 
					value+1
				FROM 
					generate_series
				WHERE 
					value+1<=255
			) 
			select
				min(value)
			from
				generate_series
			where
				value not in (select id from wire_guard_keys where id is not null)
		''', ret=True)
		public, private = self.create_keys(login)
		self.database.execute(
			'insert into wire_guard_keys (id, login, public, private) values(:id, :login, :public, :private)', 
			{
				'id': id if id else row_id[0],
				'login': login,
				'public': public,
				'private': private
			}
		)
		self.wg_changes = True

	def get_user(self, id:int)-> WGUser:
		user_row = self.database.execute('select id, login, public, private from wire_guard_keys where id=:id', {'id':id},  ret=True)
		return self.row_in_obj(user_row)

	def get_users(self)->list[WGUser]:
		users = []
		user_rows = self.database.execute('select id, login, public, private from wire_guard_keys where id>0 order by login',  ret=True, ret_many=True)
		for row in user_rows:

			users.append(self.row_in_obj(row))
		return users

	def update_user(self, user_id:int):
		user = self.get_user(user_id)
		public, private = self.create_keys(user.login)
		self.database.execute(
			'update wire_guard_keys set public=:public, private=:private where id=:id', 
			{
				'id':user.id,
				'public': public,
				'private': private
			}
		)
		self.wg_changes = True

	def delete_user(self, user_id:int):
		self.database.execute('delete from wire_guard_keys where id = :id', {'id':user_id})
		self.wg_changes = True

	def gen_conf_files(self):
		conf = open(f'{self.base_path}/wg0.conf', "w")
		server = self.get_user(0)
		conf.write(f'[Interface]\n')
		conf.write(f'PrivateKey = {server.private}\n')
		conf.write(f'Address = {self.server_ip}/24\n')
		conf.write(f'ListenPort = 51830\n')
		conf.write(f'PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE\n')
		conf.write(f'PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE\n\n')

		users = self.get_users()
		for user in users:
			conf.write('[Peer]\n')
			conf.write(f'PublicKey = {user.public}\n')
			conf.write(f'AllowedIPs = 10.0.0.{user.id}/32\n\n')

		conf.close()

	def gen_user_conf_files(self):
		conf_folder = f'{self.base_path}/user_confs'
		if not os.path.exists(conf_folder): os.mkdir(conf_folder)

		for root, dirs, files in os.walk(conf_folder):  
			for file_path in files:
				os.remove(f'{root}/{file_path}')

		users = self.get_users()
		server = self.get_user(0)
		for user in users:
			conf = open(f'{conf_folder}/{user.login}.conf', "w")
		
			conf.write(f'[Interface]\n')
			conf.write(f'PrivateKey = {user.private}\n')
			conf.write(f'Address = 10.0.0.{user.id}/32\n')
			conf.write(f'DNS = 8.8.8.8\n\n')

			conf.write(f'[Peer]\n')
			conf.write(f'PublicKey = {server.public}\n')
			conf.write(f'Endpoint = {self.server_ip}:51830\n')
			conf.write(f'AllowedIPs = 0.0.0.0/0')
		
			conf.close()
		

	def restart(self, force:bool=False):
		if not self.wg_changes and not force: return
		self.gen_conf_files()
		self.gen_user_conf_files()
		os.system('systemctl restart wg-quick@wg0')
		self.wg_changes = False

class WGPage(Page):
	page_label = 'WireGuard'
	wg = WGMain()
	def before_add(self):
		self.wg.init_table()
		self.options = {
			'l': {'name': 'User list', 'page':WGUserList()},
			'a': {'name': 'Add User', 'page':WGAddUser()},
			'r': {'name': 'Restart'},
		}
	def not_page_selector(self, input_text:str):
		if input_text == 'r':
			self.wg.restart()

	def back(self):
		self.wg.restart()
		self.pager.prev_page()

class WGUserList(Page):
	page_label = 'WireGuard Users List'
	wg = WGMain()

	def before_add(self):
		self.get_user_list()

	def after_return(self):
		pass
		self.get_user_list()

	def get_user_list(self):
		self.options = {}
		users = self.wg.get_users()
		for user in users:
			self.options[str(user.id)] = {'name': user.login, 'page':WGUserData(user.id)}

class WGUserData(Page):
	wg = WGMain()
	def __init__(self, user_id:int):
		super().__init__()
		if user_id == '0':self.back()
		self.user = self.wg.get_user(int(user_id))
		if not self.user:
			self.back()
			return

		self.page_label = f'User "{self.user.login}"'
		self.options = {
			'd': {'name': 'Delete'},
			'u': {'name': 'Update keys'}
		}
		
	def not_page_selector(self, input_text:str):
		if input_text == 'd':
			self.wg.delete_user(self.user.id)
			self.back()
		elif input_text == 'r':
			self.wg.restart()
	
	def update_keys(self):
		self.wg.update_user(self.user.id)

class WGAddUser(Page):
	page_label = 'WireGuard Add Users'
	select_label = 'new user login: '
	wg = WGMain()

	def not_page_selector(self, input_text:str):
		self.wg.create_user(input_text)
		self.back()

