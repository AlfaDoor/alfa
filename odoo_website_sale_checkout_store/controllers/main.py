# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers.portal import PaymentProcessing

class WebsiteSaleExtended(WebsiteSale):


	@http.route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
	def cart(self, access_token=None, revive='', **post):
		res = super(WebsiteSaleExtended,self).cart(**post)
		order = request.website.sale_get_order()

		website_order_obj = request.env['res.config.settings']
		pickup_paystore = website_order_obj.sudo().search([], limit=1, order="id desc").pickup_paystore

		pickup_paynow = website_order_obj.sudo().search([], limit=1, order="id desc").pickup_paynow

		paynow_delivery = website_order_obj.sudo().search([], limit=1, order="id desc").paynow_delivery
		
		payon_delivery = website_order_obj.sudo().search([], limit=1, order="id desc").payon_delivery

		res.qcontext.update({
			'pickup_paystore': pickup_paystore,
			'pickup_paynow': pickup_paynow,
			'paynow_delivery': paynow_delivery,
			'payon_delivery': payon_delivery,
		})
		return res
		

	def _get_mandatory_billing_fields(self):
		return ["name", "email"]

	def _get_mandatory_shipping_fields(self):
		return ["name", "street", "city", "country_id"]



	@http.route(['/shop/address'], type='http', methods=['GET', 'POST'], auth="public", website=True)
	def address(self, **kw):
		res = super(WebsiteSaleExtended,self).address(**kw)
		Partner = request.env['res.partner'].with_context(show_address=1).sudo()
		order = request.website.sale_get_order()

		partner = request.env.user.partner_id

		res.qcontext.update({
			'post': kw.get('option'),
			'order' : order,
			'states': request.env['res.country.state'].sudo().search([]),
			'countries': request.env['res.country'].sudo().search([]),
		})

		if not request.website.is_public_user():
			res.qcontext['checkout'].update({
				'name' : partner.name,
				'email' : partner.email,
				'phone' : partner.phone,
				'city' : partner.city,
				'street' : partner.street,
				'zip' : partner.zip,
				'state_id' : partner.state_id.id or False,
				'country_id' : partner.country_id.id or False,
			})

		return res
				
						
	@http.route(['/shop/confirm_order'], type='http', auth="public", website=True, sitemap=False)
	def confirm_order(self, **post):
		order = request.website.sale_get_order()

		user_id = request.env.user

		redirection = self.checkout_redirection(order)
		if redirection:
			return redirection

		transaction_id = None

		if transaction_id:
			tx = request.env['payment.transaction'].sudo().browse(transaction_id)
			assert tx in order.transaction_ids()
		elif order:
			tx = order.get_portal_last_transaction()
		else:
			tx = None
		email = post.get('email')
		name = post.get('name')
		phone = post.get('phone')
		pickup_type = post.get('pickup_type')

		city = post.get('city')
		street = post.get('street')
		zip1= post.get('zip')
		state_id = post.get('state_id')
		country_id = post.get('country_id')


		if pickup_type in ['pickup_paystore','pickup_paynow']:
			if email and name and phone:
				partner = request.env['res.partner'].sudo().search([('email','like',str(email))],limit=1)
				
				if request.website.is_public_user():
					if not partner:
						partner = request.env['res.partner'].sudo().create({
							'name' : post.get('name'),
							'email' : post.get('email'),
							'phone' : post.get('phone'),
						})

					order.sudo().write({
						'partner_id' : partner.id,
						'partner_invoice_id' : partner.id,
						'partner_shipping_id' : partner.id,
					})

				if not partner:
					partner = request.env['res.partner'].sudo().create({
						'name' : post.get('name'),
						'email' : post.get('email'),
						'phone' : post.get('phone'),
						'type' : 'other',
						'parent_id' : user_id.partner_id.id
					})

				order.sudo().write({
					'checkout_option' : post.get('pickup_type'),
					'pickup_id' : partner.id,
				})


				order.onchange_partner_shipping_id()
				order.order_line._compute_tax_id()
				request.session['sale_last_order_id'] = order.id
				request.website.sale_get_order(update_pricelist=True)

				if pickup_type == 'pickup_paystore':
					order.with_context(send_email=True).action_confirm()
					request.website.sale_reset()
					PaymentProcessing.remove_payment_transaction(tx)
					return request.render("website_sale.confirmation", {'order': order})

				if pickup_type == 'pickup_paynow':
					extra_step = request.website.viewref('website_sale.extra_info_option')
					if extra_step.active:
						return request.redirect("/shop/extra_info")

					return request.redirect("/shop/payment")

		elif pickup_type in ['paynow_delivery','payon_delivery']:
			if email and name and phone and city and street and country_id:
				partner = request.env['res.partner'].sudo().search([('email','=',email)],limit=1)
				
				if request.website.is_public_user():
					if not partner:
						partner = request.env['res.partner'].sudo().create({
							'name' : name,
							'email' : email,
							'phone' : phone,
							'city' : city,
							'street' : street,
							'zip' : zip1,
							'state_id' : int(state_id) or False,
							'country_id' : int(country_id) or False,
						})

					order.sudo().write({
						'partner_id' : partner.id,
						'partner_invoice_id' : partner.id,
						'partner_shipping_id' : partner.id,
					})

				if not partner:
					partner = request.env['res.partner'].sudo().create({
						'name' : name,
						'email' : email,
						'phone' : phone,
						'type' : 'other',
						'parent_id' : user_id.partner_id.id,
						'city' : city,
						'street' : street,
						'zip' : zip1,
						'state_id' : int(state_id) or False,
						'country_id' : int(country_id) or False,
					})

				order.sudo().write({
					'checkout_option' : post.get('pickup_type'),
					'pickup_id' : partner.id,
				})


				order.onchange_partner_shipping_id()
				order.order_line._compute_tax_id()
				request.session['sale_last_order_id'] = order.id
				request.website.sale_get_order(update_pricelist=True)

				if pickup_type == 'paynow_delivery':
					extra_step = request.website.viewref('website_sale.extra_info_option')
					if extra_step.active:
						return request.redirect("/shop/extra_info")

					return request.redirect("/shop/payment")

				if pickup_type == 'payon_delivery':
					order.with_context(send_email=True).action_confirm()
					request.website.sale_reset()
					PaymentProcessing.remove_payment_transaction(tx)
					return request.render("website_sale.confirmation", {'order': order})

		else:
			order = request.website.sale_get_order()

			redirection = self.checkout_redirection(order)
			if redirection:
				return redirection

			order.onchange_partner_shipping_id()
			order.order_line._compute_tax_id()
			request.session['sale_last_order_id'] = order.id
			request.website.sale_get_order(update_pricelist=True)
			extra_step = request.website.viewref('website_sale.extra_info_option')
			if extra_step.active:
				return request.redirect("/shop/extra_info")

			return request.redirect("/shop/payment")
			
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
