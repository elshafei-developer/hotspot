import frappe
from frappe import _
from frappe.model.document import Document
from frappe import json
import frappe.realtime
from frappe.utils import random_string
import frappe.utils
import requests
import re


class Vouchers(Document):

    def db_insert(self, *args, **kwargs):
        insert_voucher(self.as_dict())

    def db_update(self, *args, **kwargs):
        update_voucher(self.name, self.as_dict())
        self.modified = False

    def update(self, *args, **kwargs):
        return super().update(*args)

    def before_rename(self, old, new, merge=False):
        frappe.throw(_(f"Error: Can not Rename From Here."))

    def delete(args):
        delete_voucher(args.name)

    def load_from_db(self):
        self.modified = False
        voucher = get_voucher(self.name)
        super(Document, self).__init__(voucher)

    @staticmethod
    def get_list(args):
        vouchers = get_vouchers(args)
        if args.get('as_list'):
            return [tuple(voucher.values()) for voucher in vouchers]
        if args.get('user'):
            owners = {}
            for voucher in vouchers:
                owner = voucher['owner']
                owners[owner] = owners.get(owner, 0) + 1
            result = [{'name': owner, 'count': count} for owner, count in owners.items()]
            return result
        return vouchers

    @staticmethod
    def get_count(args):
        return ''
    @staticmethod
    def get_stats(args):
        return {}

### FUNCTIONS ###
def get_vouchers(args):
	filters = args.get('filters',[])
	vouchers = connect_hotspot('GET')
	if vouchers == False:
		frappe.throw(_(f"Error: The hotspot controller is disconnected."))
	else:
		vouchers.pop(0)
		order_by = args.get('order_by')
		# order_by = args.get('order_by')
		pattern = r'`tabVouchers`\.`(\w+)`\s+(desc|asc)'
		match = re.search(pattern, order_by)
		printData(order_by,'Order By')
		if match:
			order_key = match.group(1)
		else:
			order_key = None
		printData(order_by,'Match')    
		vouchers_map = sorted(list(map(data_map(), vouchers)), key=lambda x: x[order_key], reverse=True if 'desc' in order_by else False)
		if filters == []:
			return vouchers_map
		else:
			return filters_vouchers(filters,vouchers_map)
def get_voucher(voucher):
	info_voucher = connect_hotspot('GET',voucher)
	comment = comment_Mikrotik_structure(info_voucher)
	hotspot_controller = frappe.get_doc('Hotspot Controller')
	info_voucher['url'] = hotspot_controller.get_server_url(info_voucher['server']) if 'server' in info_voucher else 'http://localhost'
	info_voucher['server'] = hotspot_controller.get_name(info_voucher['server']) if 'server' in info_voucher else 'الكل'
	info_voucher['name1'] = info_voucher['name']
	info_voucher['status'] = 'Active' if info_voucher['disabled'] == 'false' else 'Inactive'
	info_voucher['limit_uptime'] = hotspot_controller.get_limit_uptime_name(info_voucher['limit-uptime']) if 'limit-uptime' in info_voucher else None
	info_voucher['owner'] = comment['owner'] 
	info_voucher['create_by'] = comment['owner'] 
	info_voucher['creation'] = comment['creation']
	info_voucher['modified'] = comment['modified']
	info_voucher['modified_by'] = comment['modified_by']
	return info_voucher
def insert_voucher(data):
	data = voucher_structure(data)
	connect_hotspot('PUT',data)
def update_voucher(voucher,data):
	data = voucher_structure(data)
	connect_hotspot('PATCH',data,voucher)
def delete_voucher(voucher):
	connect_hotspot('DELETE',voucher)
def voucher_exists(new_name,old_name=None):
	vouchers = connect_hotspot('GET')
	vouchers_exists = list(map(lambda x: x['name'], vouchers))
	if old_name:
		vouchers_exists.pop(vouchers_exists.index(old_name))
	if new_name in vouchers_exists:
		frappe.throw(_(f"Error: The voucher '{new_name}' already exists."))
def data_map():
    hotspot_controller = frappe.get_doc('Hotspot Controller')

    data_map = lambda v: {
                    'name':v['name'],
                    'name1':v['name'],
                    'idx':v['.id'],
                    'status': 'Active' if v['disabled'] == 'false' else 'Inactive',
                    'uptime': v['uptime'],
                    'limit_uptime':hotspot_controller.get_limit_uptime_name(v['limit-uptime']) if 'limit-uptime' in v else '00:00:00',
                    'server': hotspot_controller.get_name(v['server']) if 'server' in v else 'الكل',
                    'url': hotspot_controller.get_server_url(v['server']) if 'server' in v else 'http://localhost',
                    "owner": comment_Mikrotik_structure(v)['owner'],
                    "create_by": comment_Mikrotik_structure(v)['owner'],
					"creation1" : comment_Mikrotik_structure(v)['creation'],
					"creation" : comment_Mikrotik_structure(v)['creation'],
					"modified" : comment_Mikrotik_structure(v)['modified'],
                    }
    return data_map
def comment_Mikrotik_structure(voucher):
    comment = voucher['comment'] if 'comment' in voucher else '{}'
    try:
        comment_json = json.loads(comment.replace("'", "\""))
        return  {
            'owner': comment_json['owner'] if 'owner' in comment_json else None,
            'creation': comment_json['creation'] if 'creation' in comment_json else '2000-01-01',
            'modified': comment_json['modified'] if 'modified' in comment_json else "2000-01-01",
            'modified_by': comment_json['modified_by'] if 'modified_by' in comment_json else "Administrator",
            }
    except:
        return {
            'owner': 'Hotspot',
            'creation': 0,
            'modified': 0,
            'modified_by': 'Hotspot',
        }
def filters_vouchers(filters,vouchers_map):
        vouchers_filter = vouchers_map
        for f in filters:
            if 'status' in f:
                status_filter = list(filter(lambda v: v[f[1]] == f[-1], vouchers_filter))
                vouchers_filter = status_filter
                continue
            if 'limit_uptime' in f:
                limit_uptime_filter = list(filter(lambda v: v[f[1]] == f[-1], vouchers_filter))
                vouchers_filter = limit_uptime_filter
                continue
            if 'server' in f:
                server_filter = list(filter(lambda v: v[f[1]] == f[-1], vouchers_filter))
                vouchers_filter = server_filter
                continue
            if 'owner' in f:
                owner_filter = list(filter(lambda v: v[f[1]] == f[-1], vouchers_filter))
                vouchers_filter = owner_filter
                continue
            if 'create_by' in f:
                owner_filter = list(filter(lambda v: v[f[1]] == f[-1], vouchers_filter))
                vouchers_filter = owner_filter
                continue
        return vouchers_filter
def voucher_structure(data):
	"""
	structure of voucher that MikroTik Accept
	"""
	hotspot_controller = frappe.get_doc('Hotspot Controller')
	time = hotspot_controller.get_limit_uptime(data['limit_uptime']) if data['limit_uptime'] else '00:00:00'
	comment = {
		"owner": data['owner'] if 'owner' in data else frappe.session.user,
		"creation": data['creation'] if 'creation' in data else frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M:%S'),
		"modified": data['modified'] if 'modified' in data else frappe.utils.now_datetime().strftime('%Y-%m-%d %H:%M:%S'),
		"modified_by": data['modified_by'] if 'modified_by' in data else frappe.session.user,
    }
	comment = json.dumps(comment)
	return {
		"name": data['name1'].replace(' ','_'),
		'disabled': 'false' if data['status'] == 'Active' else 'true',
		'server': hotspot_controller.get_server(data['server']) if data['server'] != 'الكل' else 'all',
		'limit-uptime':  convert_time_format(time),
		"comment": f"{comment}",
	}
def convert_time_format(time_str):
    parts = str(time_str).split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = int(parts[2])
    
    formatted_time = f"{hours}h{minutes}m{seconds}s"
    return formatted_time

### REST API ###
def connect_hotspot(method,data=None,voucher=None):
	hotspot_controller = frappe.get_doc('Hotspot Controller')
	ip = hotspot_controller.ip
	admin = hotspot_controller.user
	password = hotspot_controller.password

	if method == 'GET':
		return GET(ip,admin,password,data)
	if method == 'PUT':
		return PUT(ip,admin,password,data)
	if method == 'DELETE':
		return DELETE(ip,admin,password,data)
	if method == 'PATCH':
		return PATCH(ip,admin,password,data,voucher)

def GET(ip,admin,password,name=None):
	if name:
		try:
			api = requests.request("GET",f"https://{ip}/rest/ip/hotspot/user/{name}",auth=(admin,password),verify=False)
			if api.status_code == 200:
				return api.json()
			else:
				frappe.throw(_(f"Error: {api.status_code} "))
				return False
		except requests.exceptions.RequestException as e:
			frappe.throw(_(f"Error: => {e}"))
			return False
	else:
		try:
			api = requests.request("GET",f"https://{ip}/rest/ip/hotspot/user",auth=(admin,password),verify=False)
			if api.status_code == 200:
				return api.json()
			else:
				frappe.throw(_(f"Error: {api.status_code}"))
				return False
		except requests.exceptions.RequestException as e:
			frappe.throw(_(f"Error: => Hotspot Controller is disconnected."))
			return False

def PUT(ip,admin,password,data):
	if data == None:
		frappe.throw(_(f"Error: The voucher could not be created Empty."))
	voucher_exists(data['name'])
	try:
		api = requests.request("PUT",f"https://{ip}/rest/ip/hotspot/user",auth=(admin,password),json=data,verify=False)
		if api.status_code == 201:
			return True
		else:
			if api.status_code == 400:
				frappe.throw(_(f"Error: {api.status_code}"))
				return False
			frappe.throw(_(f"Error: {api.status_code}"))
			return False
	except requests.exceptions.RequestException as e:
		frappe.throw(_(f"Error: => {e}"))
		return False

def DELETE(ip,admin,password,voucher):
	if voucher == None:
		frappe.throw(_(f"Error: A name Voucher must be given to delete the Voucher"))
	try:
		api = requests.request("DELETE",f"https://{ip}/rest/ip/hotspot/user/{voucher}",auth=(admin,password),verify=False)
		if api.status_code == 204:
			return True
		else:
			frappe.throw(_(f"Error: {api.status_code}"))
			return False
	except requests.exceptions.RequestException as e:
		frappe.throw(_(f"Error: => {e}"))
		return False

def PATCH(ip,admin,password,data,voucher):
	if voucher == None:
		frappe.throw(_(f"Error: A name must be given to Update the Voucher"))
	voucher_exists(data['name'],voucher)
	try:
		api = requests.request("PATCH",f"https://{ip}/rest/ip/hotspot/user/{voucher}",auth=(admin,password),verify=False,json=data)
		if api.status_code == 200:
			return True
		else:
			if api.status_code == 400:
				frappe.throw(_(f"Error: {api.status_code}"))
				return False
			frappe.throw(_(f"Error: {api.status_code}"))
			return False
	except requests.exceptions.RequestException as e:
		frappe.throw(_(f"Error: => {e}"))
		return False

### ACTION ###
@frappe.whitelist()
def create_printer_voucher(vouchers):
	doc = frappe.new_doc('Vouchers Printer')
	vouchers = json.loads(vouchers)
	if type(vouchers) != list:
		frappe.throw(_(f"ERROR => Type Data is Not Array"))
		return False
	else:
		for voucher in list(vouchers):
			doc.append('vouchers_table', {
				'voucher': voucher['name'],
				'server': voucher['server'],
				'url': voucher['url'],
                "limit_uptime": voucher['limit_uptime'],
			})
		doc.insert()
		return doc.name

@frappe.whitelist()
def delete_inactive_vouchers_background():
    frappe.enqueue(delete_inactive_vouchers)
def delete_inactive_vouchers():
	frappe.publish_realtime("realtime_vouchers", {
		"message": f"Will delete all inactive vouchers...",
		"indicator": "blue",
		"title": "Deleting Inactive Vouchers",
    })
	all_vouchers = connect_hotspot("GET")
	(all_vouchers,"All Vouchers")
	inactive_vouchers = list(filter(lambda x: x['disabled'] == 'true', all_vouchers))

	for voucher in inactive_vouchers:
		connect_hotspot("DELETE",voucher['name'])
	frappe.publish_realtime("realtime_vouchers", {
		"message": f"Successfully Deleted All Inactive Vouchers",
		"indicator": "green",
		"title": "Deleted Inactive Vouchers",
    })

@frappe.whitelist()
def crete_vouchers_background(number_vouchers,server,limit_uptime,create_print):
    if create_print == 'true':
        frappe.enqueue(create_vouchers_with_print,number_vouchers=number_vouchers,server=server,limit_uptime=limit_uptime)
    else:
        frappe.enqueue(create_vouchers,number_vouchers=number_vouchers,server=server,limit_uptime=limit_uptime)
def create_vouchers(number_vouchers,server,limit_uptime):
    frappe.publish_realtime("realtime_vouchers", {
		"message": f"Creating {number_vouchers} Vouchers for {server} server...",
		"indicator": "blue",
		"title": "Creating Vouchers",
    })
    vouchers = []
    for voucher in range(int(number_vouchers)):
        data = {
            "name1": server + random_string(3),
            'status': 'Active' ,
            'server':  server,
            'limit_uptime':  limit_uptime,
        }
        insert_voucher(data)
        vouchers.append(data)
    frappe.publish_realtime("realtime_vouchers", {
        "message": f"Successfully Created {number_vouchers} Vouchers.",
        "indicator": "green",
        "title": "Created Vouchers",
    })
    return vouchers
def create_vouchers_with_print(number_vouchers,server,limit_uptime):
    frappe.publish_realtime("realtime_vouchers", {
		"message": f"Creating {number_vouchers} Vouchers for {server} server...",
		"indicator": "blue",
		"title": "Creating Vouchers",
    })
    hotspot_controller = frappe.get_doc('Hotspot Controller')
    vouchers = []
    for voucher in range(int(number_vouchers)):
        data = {
            "name1": server + random_string(3),
            'status': 'Active' ,
            'server':  server,
            'limit_uptime':  limit_uptime,
        }
        insert_voucher(data)
        vouchers.append(data)
    doc = frappe.new_doc('Vouchers Printer')
    for v in list(vouchers):
            name = v['name1'].replace(' ','_')
            server = hotspot_controller.get_server(v['server'])
            url = hotspot_controller.get_server_url(server)
            doc.append('vouchers_table', {
                'voucher': name,
                'server': v['server'],
                'url':url,
                "limit_uptime": limit_uptime,
            })
    doc.insert()
    name_doc = doc.name
    frappe.publish_realtime("realtime_vouchers_printer", {
        "message": f"Successfully Created {number_vouchers} Vouchers for {v['server']} server With Vouchers Printer.",
        "indicator": "green",
        "title": "Created Vouchers",
		"name_doc":  doc.name,
    })
    return vouchers

# FOR TESTING
def printData(date,name=None):
	print('\n')
	print("*"*20)
	if name:
		print(name)
	print(date)
	print("*"*20)
	print('\n')
