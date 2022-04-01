from odoo import models, fields, api, _
# from datetime import datetime


class SupplierGroup(models.Model):
    _name = 'supplier.group'
    _rec_name = 'complete_name_group'

    name_group = fields.Char('Name', index=True, required=True)
    code_group = fields.Char('Code', index=True, required=True)
    complete_name_group = fields.Char('Group Name', compute='_compute_complete_name', store=True)

    @api.depends('name_group', 'complete_name_group')
    def _compute_complete_name(self):
        checkgroup = ""
        for group in self:
            if group.name_group:
                checkgroup += group.name_group
                group.complete_name_group = checkgroup


class SupplierCate(models.Model):
    _name = 'supplier.category'
    _rec_name = 'complete_name_cate'

    name_cate = fields.Char('Name', index=True, required=True)
    code_cate = fields.Char('Code', index=True, required=True)
    parent_id_group = fields.Many2one('supplier.group', 'Parent Category')
    complete_name_cate = fields.Char('Category Name', compute='_compute_complete_name', store=True)

    @api.depends('name_cate', 'complete_name_cate')
    def _compute_complete_name(self):
        check_cate = ""
        for category in self:
            if category.name_cate:
                check_cate += category.name_cate
                category.complete_name_cate = check_cate


class SupplierTypeCate(models.Model):
    _name = 'supplier.type'
    _rec_name = 'complete_name_type'

    name_type = fields.Char('Name', index=True, required=True)
    code_type = fields.Char('Code', index=True, required=True)
    parent_id_cate = fields.Many2one('supplier.category', 'Parent Category')
    complete_name_type = fields.Char('Type Name', compute='_compute_complete_name', store=True)

    @api.depends('name_type', 'complete_name_type')
    def _compute_complete_name(self):
        check_type = ""
        for type_type in self:
            if type_type.name_type:
                check_type += type_type.name_type
                type_type.complete_name_type = check_type


class SupplierCompute(models.Model):
    _name = "supplier.compute"

    parent_id_group = fields.Many2one('supplier.group', 'Parent Group')
    parent_id_cate = fields.Many2one('supplier.category', 'Parent Category',
                                     domain="[('parent_id_group', '=', parent_id_group)]")
    parent_id_type = fields.Many2one('supplier.type', 'Parent Type',
                                     domain="[('parent_id_cate', '=', parent_id_cate)]")

    name = fields.Char('Name', required=True)
    name_code = fields.Char('Code')
    seq_id = fields.Many2one('ir.sequence', string="Entry Sequence", copy=False, readonly=True)
    digit = fields.Integer('Number of digit', default=3)

    @api.model
    def create(self, vals):
        if vals.get('parent_id_group'):
            vals['name'] = self.env['supplier.group'].browse(vals['parent_id_group']).name_group + "/" +\
                           self.env['supplier.category'].browse(vals['parent_id_cate']).name_cate + "/" +\
                           self.env['supplier.type'].browse(vals['parent_id_type']).name_type

            vals['name_code'] = self.env['supplier.group'].browse(vals['parent_id_group']).code_group + \
                           self.env['supplier.category'].browse(vals['parent_id_cate']).code_cate + \
                           self.env['supplier.type'].browse(vals['parent_id_type']).code_type
        seq = {
            "name": '',
            "implementation": "no_gap",
            "prefix": '',
            "padding": '3',
            "number_increment": 1,
            "use_date_range": False,
        }
        seq = self.env["ir.sequence"].create(seq)
        vals['seq_id'] = seq.id

        result = super(SupplierCompute, self).create(vals)

        return result

    def write(self, vals):
        res = super(SupplierCompute, self).write(vals)
        value = {}
        for key, val in vals.items():
            if key == 'name':
                value["name"] = val
            if key == 'digit':
                value["padding"] = val

        self.seq_id.update(value)
        return res

    def unlink(self):
        for record in self:
            record.seq_id.sudo().unlink()

        return super(SupplierCompute, self).unlink()


class SupplierComplete(models.Model):
    _inherit = "res.partner"

    ref = fields.Char(string='Reference', index=True)
    supplier_compute_complete = fields.Many2one('supplier.compute', 'Supplier Group')

    @api.onchange('supplier_compute_complete')
    def stamp_internal_ref(self):
        if self.supplier_compute_complete:
            code = self.supplier_compute_complete.name_code
            seq = self.supplier_compute_complete.seq_id.next_by_id()
            self.ref = code + "-" + seq
        else:
            self.ref = ''

    # dt = datetime.now()
    # date_time = dt.strftime("%Y%m%d")

    # def check_month(self):
    #     check_last = self.env['res.partner'].search([], limit=1, order='create_date desc')
    #     if check_last.month < self.dt.month:
    #         return True
    #     else:
    #         return False


