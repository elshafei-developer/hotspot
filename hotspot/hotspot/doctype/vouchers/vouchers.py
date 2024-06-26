import frappe
from frappe import _
from frappe.model.document import Document
from frappe import json
import re
from .rest_api_hotspot import connect_hotspot

class Vouchers(Document):

    def db_insert(self, *args, **kwargs):
        data = voucher_structure(self.as_dict())
        connect_hotspot('PUT',data)

    def db_update(self, *args, **kwargs):
        self.modified = False
        data = voucher_structure(self.as_dict())
        connect_hotspot('PATCH',data,self.name)

    def update(self, *args, **kwargs):
        return super().update(*args)

    def delete(args):
        connect_hotspot('DELETE',args.name)

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
            return  [{'name': owner, 'count': count} for owner, count in owners.items()]
        return vouchers

    @staticmethod
    def get_count(args):
        return ''
    @staticmethod
    def get_stats(args):
        return {}

### FUNCTIONS ###
def get_vouchers(args):
    try:
        hotspot_controller = frappe.get_single('Hotspot Controller')
        ip = hotspot_controller.ip
        if ip == "":
            frappe.throw("IP not found in Hotspot Controller!")

        if frappe.cache.get_value(f'hotspot{ip}'):
            vouchers =  frappe.cache.get_value(f'hotspot{ip}')
        else:
            vouchers = connect_hotspot('GET')
            
        filters = args.get('filters',[])
        if vouchers == False:
            frappe.throw(_(f"Error: The hotspot controller is disconnected."))
        if vouchers == "401":
            frappe.throw(_(f"Error: Failed Authentication to Hotspot."))
        else:
            order_by = args.get('order_by','desc')
            pattern = r'`tabVouchers`\.`(\w+)`\s+(desc|asc)'
            match = re.search(pattern, order_by)
            if match:
                order_key = match.group(1)
            else:
                order_key = 'name'
            vouchers_map = sorted(list(map(data_map(hotspot_controller), vouchers)), key=lambda x: x[order_key], reverse=True if 'desc' in order_by else False)
            if filters == []:
                return vouchers_map
            else:
                return filters_vouchers(filters,vouchers_map)
    except:
        return False
    
def get_voucher(voucher):

    hotspot_controller = frappe.get_single('Hotspot Controller')
    info_voucher = connect_hotspot('GET',voucher)
    comment = comment_Mikrotik(info_voucher)

    info_voucher['url'] = hotspot_controller.get_server_url(info_voucher['server']) if 'server' in info_voucher else 'http://hotspot.amalsharq.net'
    info_voucher['server'] = hotspot_controller.get_name(info_voucher['server']) if 'server' in info_voucher else 'الكل'
    info_voucher['name1'] = info_voucher['name']
    info_voucher['status'] = 'Active' if info_voucher['disabled'] == 'false' else 'Inactive'
    info_voucher['limit_uptime'] = hotspot_controller.get_limit_uptime_name(info_voucher['limit-uptime']) if 'limit-uptime' in info_voucher else None
    info_voucher['bytes_in'] = (int(info_voucher['bytes-in']) / 1024) / 1024
    info_voucher['bytes_out'] = (int(info_voucher['bytes-out']) / 1024) / 1024
    info_voucher['owner'] = comment['owner']
    info_voucher['create_by'] = comment['owner'] 
    info_voucher['creation'] = comment['creation']
    info_voucher['modified'] = comment['modified']
    info_voucher['modified_by'] = comment['modified_by']
    return info_voucher
def filters_vouchers(filters,vouchers_map):
        vouchers_filter = vouchers_map
        for f in filters:
            if 'status' in f:
                status_filter = list(filter(lambda v: v["status"] in f, vouchers_filter))
                vouchers_filter = status_filter
                continue
            if 'limit_uptime' in f:
                limit_uptime_filter = list(filter(lambda v: v["limit_uptime"] in f, vouchers_filter))
                vouchers_filter = limit_uptime_filter
                continue
            if 'server' in f:
                server_filter = list(filter(lambda v: v["server"] in f, vouchers_filter))
                vouchers_filter = server_filter
                continue
            if 'owner' in f:
                owner_filter = list(filter(lambda v: v["owner"] in f, vouchers_filter))
                vouchers_filter = owner_filter
                continue
            if 'create_by' in f:
                owner_filter = list(filter(lambda v: v["create_by"] in f, vouchers_filter))
                vouchers_filter = owner_filter
                continue
        return vouchers_filter

def data_map(hotspot_controller):
    return lambda v: {
                    'name':v['name'],
                    'name1':v['name'],
                    'idx':v['.id'],
                    'status': 'Active' if v['disabled'] == 'false' else 'Inactive',
                    'uptime': v['uptime'],
                    'limit_uptime':hotspot_controller.get_limit_uptime_name(v['limit-uptime']) if 'limit-uptime' in v else '00:00:00',
                    'server': hotspot_controller.get_name(v['server']) if 'server' in v else 'الكل',
                    'url': hotspot_controller.get_server_url(v['server']) if 'server' in v else 'http://localhost',
                    "owner": comment_Mikrotik(v)['owner'],
                    "create_by": comment_Mikrotik(v)['owner'],
					"creation1" : comment_Mikrotik(v)['creation'],
					"creation" : comment_Mikrotik(v)['creation'],
					"modified" : str(comment_Mikrotik(v)['modified']),
                    "bytes_in": (int(v['bytes-in']) / 1024) / 1024,
                    "bytes_out": (int(v['bytes-out']) / 1024) / 1024,
                    "dynamic": v['dynamic'],
                    }
def voucher_structure(data):
    """
    structure of voucher that MikroTik Accept
    """
    hotspot_controller = frappe.get_single('Hotspot Controller')
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
        'limit-uptime':  time,
        "comment": comment
    }
def comment_Mikrotik(voucher):
    comment = voucher['comment'] if 'comment' in voucher else '{}'
    try:
        comment_json = json.loads(comment.replace("'", "\""))
        return  {
            'owner': comment_json['owner'] if 'owner' in comment_json else "Hotspot",
            'creation': comment_json['creation'] if 'creation' in comment_json else '2000-01-01',
            'modified': comment_json['modified'] if 'modified' in comment_json else "2000-01-01",
            'modified_by': comment_json['modified_by'] if 'modified_by' in comment_json else "Hotspot",
            }
    except:
        return {
            'owner': 'Hotspot',
            'creation': '2000-01-01',
            'modified': '2000-01-01',
            'modified_by': 'Hotspot',
        }
