
from odoo import fields, models, api, _


class ResCompany(models.Model):
    _inherit = "res.company"

    format_type = fields.Selection([('A', 'A'), ('B', 'B'), ('C', 'C')], string='Format Type',
                                   help='Format to be used in Print View Report', default='A')

    @api.multi
    def all_company_data(self):
        company = self.env.user.company_id
        complete_street = company.street and company.street + ', ' or ''
        if company.street2:
            complete_street += company.street2
        remaining_address = company.zip or ''
        if company.city:
            remaining_address += ' ' + company.city
        if company.country_id:
            remaining_address += ' - ' + company.country_id.name
        dic = {
            'name': company.name or '',
            'street': company.street or '',
            'street2': company.street2 or '',
            'city': company.city or '',
            'state_id': company.state_id.name or '',
            'zip': company.zip or '',
            'country_id': company.country_id.name or '',
            'email': company.email or '',
            'phone': company.phone or '',
            'website': company.website or '',
            'logo': company.logo,
            'vat': company.vat,
            'format_type': company.format_type,
            'complete_street': complete_street or '',
            'remaining_address': remaining_address or '',
        }
        return dic
