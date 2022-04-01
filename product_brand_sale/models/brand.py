from odoo import models,fields,api


class ProductBrand(models.Model):
    _inherit = 'product.template'

    brand_id = fields.Many2one('product.brand',string='Brand')
    launch_date = fields.Date('Launch Date')


class BrandProduct(models.Model):
    _name = 'product.brand'


    name= fields.Char(String="Name")
    brand_image = fields.Binary()
    member_ids = fields.One2many('product.template','brand_id')
    product_count = fields.Char(String='Product Count',compute='get_count_products',store=True)
    prefix = fields.Char('Prefix')

    @api.depends('member_ids')
    def get_count_products(self):
        self.product_count = len(self.member_ids)

class BrandPivot(models.Model):
    _inherit = 'sale.report'

    brand_id=fields.Many2one ('product.brand' ,string='Brand')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['brand_id'] = ", t.brand_id as brand_id"
        groupby += ', t.brand_id'
        res = super(BrandPivot, self)._query(with_clause, fields, groupby, from_clause)
        # res= super(BrandPivot, self)._query()
        # query = res.split('t.categ_id as categ_id,',1)
        # query= query[0]+'t.categ_id as categ_id,t.brand_id as brand_id,' +query[1]
        # split= query.split('t.categ_id,',1)
        # res = split[0] + 't.categ_id,t.brand_id,' + split[1]
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    brand_id = fields.Many2one('product.brand', string='Brand')
    pf_brand = fields.Char('Prefix Brand', compute='_compute_pf_brand')

    @api.depends('brand_id')
    def _compute_pf_brand(self):
        for rec in self:
            rec.pf_brand = rec.product_id.brand_id.prefix

class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
        res = super(AccountMove, self).create(vals)
        if res.line_ids:
            for a in res.line_ids:
                a.brand_id = a.product_id.brand_id
        return res