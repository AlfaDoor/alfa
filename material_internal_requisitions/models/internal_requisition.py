from odoo import models, fields, api, _
from odoo.exceptions import Warning


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    desti_loca_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
    )
    fixed_asset_desti_loca_id = fields.Many2one(
        'stock.location',
        string='Fixed Asset Destination Location'
    )


class inheritStockPicking(models.Model):
    _inherit = 'stock.picking'

    inter_requi_id = fields.Many2one(
        'internal.requisition',
        string='Internal Requisition',
        readonly=True,
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        readonly=True,
    )

    requisition_done = fields.Boolean(default=False)
   

class InternalRequisition(models.Model):
    _name = 'internal.requisition'
    _description = 'Internal Requisition'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise Warning(
                    _('You can not delete Internal Requisition which is not in draft or cancelled or rejected state.'))
        return super(InternalRequisition, self).unlink()

    name = fields.Char(
        string='Number',
        index=True,
        readonly=1,
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Waiting Department Approval'),
        ('manager', 'Waiting IR Approved'),
        ('user', 'Approved'),
        ('stock', 'Requested Stock'),
        ('receive', 'Received'),
        #         ('done', 'Done'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        track_visibility='onchange',
    )
    mo_reference = fields.Char('MO Reference')
    request_date = fields.Date(
        string='Requisition Date',
        default=fields.Date.today(),
        required=True,
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        # required=True,
        copy=True,
    )
    request_emp = fields.Many2one(
        'hr.employee',
        string='Employee',
        default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1),
        required=True,
        copy=True,
    )
    approve_manager = fields.Many2one(
        'hr.employee',
        string='Department Manager',
        readonly=True,
        copy=False,
    )
    reject_manager = fields.Many2one(
        'hr.employee',
        string='Department Manager Reject',
        readonly=True,
    )
    approve_user = fields.Many2one(
        'hr.employee',
        string='Approved by',
        readonly=True,
        copy=False,
    )
    reject_user = fields.Many2one(
        'hr.employee',
        string='Rejected by',
        readonly=True,
        copy=False,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.user.company_id,
        required=True,
        copy=True,
    )
    location = fields.Many2one(
        'stock.location',
        string='Source Location',
        # required=True,
        copy=True,
    )
    requisition_line_ids = fields.One2many(
        'requisition.line',
        'requisition_id',
        string='Requisitions Line',
        copy=True,
    )
    date_end = fields.Datetime(
        string='Requisition Deadline',
        readonly=True,
        help='Last date for the product to be needed',
        copy=True,
#         default=fields.Datetime.now
    )
    date_done = fields.Date(
        string='Date Done',
        readonly=True,
        help='Date of Completion of Internal Requisition',
    )
    managerapp_date = fields.Date(
        string='Department Approval Date',
        readonly=True,
        copy=False,
    )
    manareject_date = fields.Date(
        string='Department Manager Reject Date',
        # default=fields.Date.today(),
        readonly=True,
    )
    userreject_date = fields.Date(
        string='Rejected Date',
        readonly=True,
        copy=False,
    )
    userrapp_date = fields.Date(
        string='Approved Date',
        readonly=True,
        copy=False,
    )
    receive_date = fields.Date(
        string='Received Date',
        readonly=True,
        copy=False,
    )
    reason = fields.Text(
        string='Reason for Requisitions',
        required=False,
        copy=True,
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        required=0,
        copy=True
    )
    desti_loca_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=False,
        copy=True,
    )
    fixed_asset_desti_loca_id = fields.Many2one(
        'stock.location',
        string='Fixed Asset Destination Location',
        required=False,
        copy=True,
    )
    delivery_picking_id = fields.Many2one(
        'stock.picking',
        string='Internal Picking',
        readonly=True,
        copy=False,
    )
    requisiton_responsible_id = fields.Many2one(
        'hr.employee',
        string='Requisition Responsible',
        copy=True,
    )
    confirm_id = fields.Many2one(
        'hr.employee',
        string='Confirmed by',
        readonly=True,
        copy=False,
    )
    confirm_date = fields.Date(
        string='Confirmed Date',
        readonly=True,
        copy=False,
    )
    custom_picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Picking Type',
        copy=False,
        domain=[('code','=','internal')]
    )

    @api.model
    def create(self, vals):
        name = self.env['ir.sequence'].next_by_code('internal.requisition.seq')
        vals.update({
            'name': name
        })
        res = super(InternalRequisition, self).create(vals)
        return res

    @api.onchange('request_emp')
    def onchange_employee(self):
        check=True
        for rec in self:
            # rec.department_id = rec.request_emp.department_id.id
            rec.desti_loca_id = rec.request_emp.desti_loca_id.id
            # rec.account_id = rec.request_emp.department_id.account_id.id
            # rec.fixed_asset_desti_loca_id = rec.request_emp.fixed_asset_desti_loca_id.id
            if self.user_has_groups('material_internal_requisitions.group_requisiton_users'):
                check=False
        if(check):    
            employees = self.env['hr.employee'].search(
                ['|', ('user_id', '=', self.env.uid), ('parent_id.user_id', '=', self.env.uid)])
            own_sub_cordinates = [employee.id for employee in employees]
            return {'domain': {'request_emp': [('id', 'in', own_sub_cordinates)],
                               # 'department_id': [('id','=',self.request_emp.department_id.id)],
                               # 'account_id': [('id','=',self.request_emp.department_id.account_id.id)]
                               }}

    @api.multi
    def requisition_confirm(self):
        for rec in self:
            manager_mail_template = self.env.ref('material_internal_requisitions.email_confirm_irrequisition')
            rec.confirm_id = rec.request_emp.id
            rec.confirm_date = fields.Date.today()
            rec.state = 'confirm'
            if manager_mail_template:
                manager_mail_template.send_mail(self.id)

    @api.multi
    def requisition_reject(self):
        for rec in self:
            rec.state = 'reject'
            rec.reject_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.userreject_date = fields.Date.today()

    @api.multi
    def manager_approve(self):
        
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.approve_manager = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            employee_mail_template = self.env.ref(
                'material_internal_requisitions.email_internal_requisition_iruser_custom')
            email_iruser_template = self.env.ref('material_internal_requisitions.email_ir_requisition')
            employee_mail_template.send_mail(self.id)
            email_iruser_template.send_mail(self.id)
            rec.state = 'manager'
            rec.user_approve()
            rec.request_stock()

    @api.multi
    def user_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_user = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
            rec.state = 'user'

    @api.multi
    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.multi
    def request_stock(self):

        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for rec in self:
            if not rec.location.id:
                raise Warning(_('Select Source location under the picking details.'))

            if not rec.custom_picking_type_id.id:
                raise Warning(_('Select Picking type under the picking details.'))

            if not rec.desti_loca_id:
                raise Warning(_('Select Destination location under the picking details.'))
            
            # if not rec.fixed_asset_desti_loca_id:
            #     raise Warning(_('Select Fixed Asset Destination location under the picking details.'))
            
            vals = {
                'scheduled_date': rec.date_end,
                'partner_id': rec.request_emp.address_home_id.id,
                'employee_id': rec.request_emp.id,
                'min_date': fields.Date.today(),
                'location_id': rec.location.id,
                'location_dest_id': rec.desti_loca_id.id or rec.request_emp.desti_loca_id.id,
                'picking_type_id': rec.custom_picking_type_id.id,  # internal_obj.id,
                'note': rec.reason,
                'inter_requi_id': rec.id,
                'origin': rec.name,
            }
            stock_id = stock_obj.create(vals)
            for line in rec.requisition_line_ids:
                if line.product_id.is_fixed_asset == True:
                    vals1 = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'product_uom': line.uom.id,
                        'location_id': rec.location.id,
                        'location_dest_id': rec.request_emp.fixed_asset_desti_loca_id.id,
                        'name': line.description,
                        'picking_id': stock_id.id,
                        'remarks':line.remarks
                    }
                else:
                    vals1 = {
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.qty,
                        'product_uom': line.uom.id,
                        'location_id': rec.location.id,
                        'location_dest_id': rec.request_emp.desti_loca_id.id or rec.desti_loca_id.id,
                        'name': line.description,
                        'picking_id': stock_id.id,
                        'remarks':line.remarks
                    }
                move_obj.create(vals1)
            vals3 = {
                'delivery_picking_id': stock_id.id,
            }
            rec.write(vals3)
            rec.state = 'stock'
            self.delivery_picking_id.action_confirm()

    @api.multi
    def action_received(self):
        val = 0
        received = []
        temp = {}
        internal_requisition = self.requisition_line_ids
        picking = self.env['stock.picking'].search(
            [('origin', '=', self.name), ('state', '=', 'done'), ('requisition_done', '=', False)],
            order='date_done desc', limit=1)
        picking_no_backorder = self.env['stock.picking'].search(
            [('origin', '=', self.name), ('state', '=', 'cancel'), ('requisition_done', '=', False)])

        if picking:
            for line in picking.move_ids_without_package:
                temp = {'product_id': line.product_id, 'quantity': line.quantity_done}
                received.append(temp)
            picking.requisition_done = True

        for r in received:
            for req in internal_requisition:
                if req.product_id == r['product_id']:
                    qty = req.rec_qty + r['quantity']
                    req.rec_qty = qty

        for rec in internal_requisition:
            if rec.qty != rec.rec_qty:
                val = 1

        if val == 0:
            self.state = 'receive'

        if picking_no_backorder:
            self.state = 'receive'

 #       if self.delivery_picking_id:
 #           mvl = self.env['account.move.line']
 #          res = self.env['account.move'].search([('ref', '=', self.delivery_picking_id.name), ])
 #           if len(res) > 0:
 #               move_id = res[0].id
 #               move_lines = mvl.search([('move_id', '=', move_id), ])
 #               for aml in move_lines:
 #                   mvl.browse(aml.id).write({'analytic_account_id': self.account_id.id})

    @api.multi
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    # @api.onchange('request_emp')
    # def set_department(self):
    #     for rec in self:
    #         rec.department_id = rec.request_emp.department_id.id
    #         rec.desti_loca_id = rec.request_emp.desti_loca_id.id or rec.request_emp.department_id.desti_loca_id.id

    @api.multi
    def show_picking(self):
        for rec in self:
            res = self.env.ref('stock.action_picking_tree_all')
            res = res.read()[0]
            res['domain'] = str([('inter_requi_id', '=', rec.id)])
        return res


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        copy=True,
    )

    desti_loca_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
    )
class inherit_moves(models.Model):
    _inherit = 'stock.move'

    remarks = fields.Char()

    price = fields.Float(compute="get_unit_price", store=False, string='Unit Price')
    total_cost = fields.Float(compute="get_total_cost", store=False, string='Total Cost')
    # total_total_cost = fields.Float(string='Total')


    @api.one
    @api.depends('price_unit')
    def get_unit_price(self):
        self.price = abs(self.price_unit)

    @api.one
    @api.depends('price')
    def get_total_cost(self):
        self.total_cost = format((float((format(self.price, ".4f"))) * self.quantity_done), ".2f")

class inherit_product(models.Model):
    _inherit = 'product.template'

    is_fixed_asset = fields.Boolean(default=False)

class inherit_backorder(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    @api.multi
    def process_cancel_backorder(self):
        received_prod = []
        dictionry = {}

        requisition = self.env['internal.requisition'].search([('name', '=', self.pick_ids.id)])

        if not requisition:
            res = super(inherit_backorder, self).process_cancel_backorder()
            return res

        for line in self.pick_ids.move_ids_without_package:
            dictionry = {'product_id': line.product_id, 'quantity': line.quantity_done}
            received_prod.append(dictionry)
        for items in received_prod:
            for rec in requisition.requisition_line_ids:
                if rec.product_id == items['product_id']:
                    rec.rec_qty = items['quantity']
        requisition.state = 'receive'
        res = super(inherit_backorder, self).process_cancel_backorder()
        return res


class InheritProduct(models.Model):
    _inherit = 'product.product'

    _sql_constraints = [
        ('name_uniq', 'unique(product_tmpl_id)', 'Product with this ID is already created'),
    ]

