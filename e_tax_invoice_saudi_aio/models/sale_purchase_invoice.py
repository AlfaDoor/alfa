from odoo import api, fields, models, _
import qrcode
import base64
import io
from odoo.tools.misc import formatLang, format_date
from odoo import http
from num2words import num2words


class AccountMove(models.Model):
	_inherit = 'account.invoice'

	invoice_date_supply = fields.Date('Date Of Supply')

	def get_product_arabic_name(self,pid):
		translation = self.env['ir.translation'].search([
			('name','=','product.product,name'),('state','=','translated'),
			('res_id','=',pid)])
		if translation :
			return translation.value
		else: 
			product = self.env['product.product'].browse(int(pid))
			translation = self.env['ir.translation'].search([
				('name','=','product.product,name'),('state','=','translated'),
				('res_id','=',product.product_tmpl_id.id)])
			if translation :
				return translation.value
		return ''
	

	def amount_word(self, amount):
		language = self.partner_id.lang or 'en'
		language_id = self.env['res.lang'].search([('code', '=', 'ar_AA')])
		if language_id:
			language = language_id.iso_code
		amount_str =  str('{:2f}'.format(amount))
		amount_str_splt = amount_str.split('.')
		before_point_value = amount_str_splt[0]
		after_point_value = amount_str_splt[1][:2]           
		before_amount_words = num2words(int(before_point_value),lang=language)
		after_amount_words = num2words(int(after_point_value),lang=language)
		amount = before_amount_words + ' ' + after_amount_words
		return amount

	def amount_total_words(self, amount):
		words_amount = self.currency_id.amount_to_text(amount)
		return words_amount

	@api.model
	def get_qr_code(self):

		def get_qr_encoding(tag, field):
			company_name_byte_array = field.encode('UTF-8')
			company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
			company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
			return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

		qr_code_str = ''
		seller_name_enc = get_qr_encoding(1, self.company_id.display_name)
		company_vat_enc = get_qr_encoding(2, self.company_id.vat or '')
		time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), self.create_date)
		timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
		invoice_total_enc = get_qr_encoding(4, str(self.amount_total))
		total_vat_enc = get_qr_encoding(5, str(self.currency_id.round(self.amount_total - self.amount_untaxed)))

		str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
		qr_code_str = base64.b64encode(str_to_encode).decode('UTF-8')
		return qr_code_str


	@api.multi
	def action_invoice_sent(self):
		self.ensure_one()
		template = self.env.ref('e_tax_invoice_saudi_aio.email_template_edi_invoice_etir', False)
		compose_form = self.env.ref('account.account_invoice_send_wizard_form', False)
		# have model_description in template language
		lang = self.env.context.get('lang')
		if template and template.lang:
			lang = template._render_template(template.lang, 'account.invoice', self.id)
		self = self.with_context(lang=lang)
		TYPES = {
			'out_invoice': _('Invoice'),
			'in_invoice': _('Vendor Bill'),
			'out_refund': _('Credit Note'),
			'in_refund': _('Vendor Credit note'),
		}
		ctx = dict(
			default_model='account.invoice',
			default_res_id=self.id,
			default_use_template=bool(template),
			default_template_id=template and template.id or False,
			default_composition_mode='comment',
			mark_invoice_as_sent=True,
			model_description=TYPES[self.type],
			custom_layout="mail.mail_notification_paynow",
			force_email=True
		)
		return {
			'name': _('Send Invoice'),
			'type': 'ir.actions.act_window',
			'view_type': 'form',
			'view_mode': 'form',
			'res_model': 'account.invoice.send',
			'views': [(compose_form.id, 'form')],
			'view_id': compose_form.id,
			'target': 'new',
			'context': ctx,
		}


class ResPartner(models.Model):
	_inherit = 'res.partner'

	building_no = fields.Char('Building No')
	additional_no = fields.Char('Additional No')
	other_seller_id = fields.Char('Other Seller Id')


class ResCompany(models.Model):
	_inherit = 'res.company'

	building_no = fields.Char(related='partner_id.building_no', store=True, readonly=False, string='Building No')
	additional_no = fields.Char(related='partner_id.additional_no', store=True, readonly=False, string='Additional No')
	other_seller_id = fields.Char(related='partner_id.other_seller_id', store=True, readonly=False, string='Other Seller Id')
	arabic_name = fields.Char('Name')
	arabic_street = fields.Char('Street')
	arabic_street2 = fields.Char('Street2')
	arabic_city = fields.Char('City')
	arabic_state = fields.Char('State')
	arabic_country = fields.Char('Country')
	arabic_zip = fields.Char('Zip')


class SaleOrder(models.Model):
	_inherit = 'sale.order'

	def get_product_arabic_name(self,pid):
		translation = self.env['ir.translation'].search([
			('name','=','product.product,name'),('state','=','translated'),
			('res_id','=',pid)])
		if translation :
			return translation.value
		else: 
			product = self.env['product.product'].browse(int(pid))
			translation = self.env['ir.translation'].search([
				('name','=','product.product,name'),('state','=','translated'),
				('res_id','=',product.product_tmpl_id.id)])
			if translation :
				return translation.value
		return ''    

	@api.model
	def get_qr_code(self):

		def get_qr_encoding(tag, field):
			company_name_byte_array = field.encode('UTF-8')
			company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
			company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
			return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

		qr_code_str = ''
		seller_name_enc = get_qr_encoding(1, self.company_id.display_name)
		company_vat_enc = get_qr_encoding(2, self.company_id.vat or '')
		time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), self.date_order or self.create_date)
		timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
		invoice_total_enc = get_qr_encoding(4, str(self.amount_total))
		total_vat_enc = get_qr_encoding(5, str(self.currency_id.round(self.amount_total - self.amount_untaxed)))

		str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
		qr_code_str = base64.b64encode(str_to_encode).decode('UTF-8')
		return qr_code_str

	def amount_word(self, amount):
		language = self.partner_id.lang or 'en'
		language_id = self.env['res.lang'].search([('code', '=', 'ar_AA')])
		if language_id:
			language = language_id.iso_code
		amount_str =  str('{:2f}'.format(amount))
		amount_str_splt = amount_str.split('.')
		before_point_value = amount_str_splt[0]
		after_point_value = amount_str_splt[1][:2]           
		before_amount_words = num2words(int(before_point_value),lang=language)
		after_amount_words = num2words(int(after_point_value),lang=language)
		amount = before_amount_words + ' ' + after_amount_words
		return amount

	def amount_total_words(self, amount):
		words_amount = self.company_id.currency_id.amount_to_text(amount)
		return words_amount


class PurchaseOrder(models.Model):
	_inherit = 'purchase.order'

	def get_product_arabic_name(self,pid):
		translation = self.env['ir.translation'].search([
			('name','=','product.product,name'),('state','=','translated'),
			('res_id','=',pid)])
		if translation :
			return translation.value
		else: 
			product = self.env['product.product'].browse(int(pid))
			translation = self.env['ir.translation'].search([
				('name','=','product.product,name'),('state','=','translated'),
				('res_id','=',product.product_tmpl_id.id)])
			if translation :
				return translation.value
		return ''
		
	@api.model
	def get_qr_code(self):

		def get_qr_encoding(tag, field):
			company_name_byte_array = field.encode('UTF-8')
			company_name_tag_encoding = tag.to_bytes(length=1, byteorder='big')
			company_name_length_encoding = len(company_name_byte_array).to_bytes(length=1, byteorder='big')
			return company_name_tag_encoding + company_name_length_encoding + company_name_byte_array

		qr_code_str = ''
		seller_name_enc = get_qr_encoding(1, self.company_id.display_name)
		company_vat_enc = get_qr_encoding(2, self.company_id.vat or '')
		time_sa = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), self.date_order or self.create_date)
		timestamp_enc = get_qr_encoding(3, time_sa.isoformat())
		invoice_total_enc = get_qr_encoding(4, str(self.amount_total))
		total_vat_enc = get_qr_encoding(5, str(self.currency_id.round(self.amount_total - self.amount_untaxed)))

		str_to_encode = seller_name_enc + company_vat_enc + timestamp_enc + invoice_total_enc + total_vat_enc
		qr_code_str = base64.b64encode(str_to_encode).decode('UTF-8')
		return qr_code_str

	def amount_word(self, amount):
		language = self.partner_id.lang or 'en'
		language_id = self.env['res.lang'].search([('code', '=', 'ar_AA')])
		if language_id:
			language = language_id.iso_code
		amount_str =  str('{:2f}'.format(amount))
		amount_str_splt = amount_str.split('.')
		before_point_value = amount_str_splt[0]
		after_point_value = amount_str_splt[1][:2]           
		before_amount_words = num2words(int(before_point_value),lang=language)
		after_amount_words = num2words(int(after_point_value),lang=language)
		amount = before_amount_words + ' ' + after_amount_words
		return amount

	def amount_total_words(self, amount):
		words_amount = self.company_id.currency_id.amount_to_text(amount)
		return words_amount