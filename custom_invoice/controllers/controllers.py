# -*- coding: utf-8 -*-
from odoo import http

# class Xxx(http.Controller):
#     @http.route('/xxx/xxx/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/xxx/xxx/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('xxx.listing', {
#             'root': '/xxx/xxx',
#             'objects': http.request.env['xxx.xxx'].search([]),
#         })

#     @http.route('/xxx/xxx/objects/<model("xxx.xxx"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('xxx.object', {
#             'object': obj
#         })