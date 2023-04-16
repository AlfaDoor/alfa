# import xmlrpc.client
#
# url, db, username, password = "http://localhost:8069", "odoo12", "admin", "123"
# url, db, username, password = "https://musaid-test-staging-1362873.dev.odoo.com", "musaid-test-staging-1362873", "bk@mas.co", "sit@123"
# common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
# common.version()
# uid = common.authenticate(db, username, password, {})
# models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
# try:
#     res = models.execute_kw(db, uid, password, 'res.partner', 'check_access_rights', ['read'], {'raise_exception': False})
# except :
#     print("Test failed")
# # vals = {
# #     'employee_id': 1,
# #     'check_in': '2020-08-16 00:00:00',
# # }
# # res = models.execute_kw(db, uid, password, 'hr.attendance', 'create', [vals])
# print(res)


from zk import ZK, const
ip = "192.168.93.202"
zk = ZK(ip=ip, port="4370", timeout=5)
conn = zk.connect()
attendances = conn.get_attendance()
status = [att.status for att in attendances]
print(list(set(status)))
