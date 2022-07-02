import xmlrpc.client

url, db, username, password = "http://localhost:8069", "Musaid-withoutfilestore", "barrak@musaidalsayyarco.com", "123"
# url, db, username, password = "https://musaid-test2.odoo.com", "musaid-staging-1642416", "admin", "admin"
common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
common.version()
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
values = [{
    'id': 80,
    'employee_fingerprint_no': "9",
    'fingerprint': "XXX",
    'datetime': "2020-11-01 08:50:00",
    'action': 'sign_in',
}]
# res = models.execute_kw(db, uid, password, 'res.partner', 'check_access_rights', ['read'], {'raise_exception': False})
res = models.execute_kw(db, uid, password, 'hr.attendance', 'create_new_from_remote', [values], )  # {'values':}
print(res)












# from zk import ZK, const
# ip = "192.168.93.202"
# zk = ZK(ip=ip, port="4370", timeout=5)
# conn = zk.connect()
# attendances = conn.get_attendance()
# status = [att.status for att in attendances]
# print(list(set(status)))
