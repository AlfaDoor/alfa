# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo import SUPERUSER_ID

class res_config_settings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	pickup_paystore = fields.Boolean("Pickup and pay at store")
	pickup_paynow = fields.Boolean("Pickup at store but pay now")
	paynow_delivery = fields.Boolean("Pay now and get delivery")
	payon_delivery = fields.Boolean("Pay on delivery")


	@api.model
	def default_get(self, fields_list):
		res = super(res_config_settings, self).default_get(fields_list)
		if self.search([], limit=1, order="id desc").pickup_paystore:
			res.update({'pickup_paystore': self.search([], limit=1, order="id desc").pickup_paystore})

		if self.search([], limit=1, order="id desc").pickup_paynow:
			res.update({'pickup_paynow': self.search([], limit=1, order="id desc").pickup_paynow})

		if self.search([], limit=1, order="id desc").paynow_delivery:
			res.update({'paynow_delivery': self.search([], limit=1, order="id desc").paynow_delivery})
			
		if self.search([], limit=1, order="id desc").payon_delivery:
			res.update({'payon_delivery': self.search([], limit=1, order="id desc").payon_delivery})
												
		return res
  

class SaleOrderIn(models.Model):
	_inherit = 'sale.order'

	checkout_option = fields.Selection([
		('pickup_paystore','Pickup and pay at store'),
		('pickup_paynow','Pickup at store but pay now'),
		('paynow_delivery','Pay now and get delivery'),
		('payon_delivery','Pay on delivery')
	], default='paynow_delivery', string="Check Out Option")
	pickup_id = fields.Many2one('res.partner',string="Pickup Person",domain=[('type','=','other')])


