from odoo import models, fields, _


class PoolingQt(models.Model):
    _name = 'pooling.qt'
    _description = 'api ic'

    No = fields.Integer('No')
    CertNo = fields.Char('CertNo')
    RequestNumber = fields.Char('RequestNumber')
    RequestDate = fields.Datetime('RequestDate')
    RequestName = fields.Char('RequestName')
    RequestType = fields.Char('RequestType')
    ApprovedNumber = fields.Char('ApprovedNumber')
    ApprovedDate = fields.Datetime('ApprovedDate')
    RegisterID = fields.Char('RegisterID')
    TaxID = fields.Char('TaxID')
    Username = fields.Char('Username')
    ComCode = fields.Char('ComCode')
    InvoiceNumber = fields.Char('InvoiceNumber')
    InvoiceDate = fields.Datetime('InvoiceDate')
    ItemNumber = fields.Char('ItemNumber')
    Month = fields.Integer('Month')
    Year = fields.Integer('Year')
    Send = fields.Boolean('Send')
    Receipt = fields.Boolean('Receipt')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_qt', 'To Quotations')], string='State',
        default='draft')
    User = fields.Char('User')
    user_ref = fields.Char('User Reference')

    def action_create_to_qt(self):
        customer = self.env['res.partner'].search([('ref', '=', self.user_ref)])
        qt_rec = self.env['sale.order'].create({
            'partner_id': customer.id,
        })
        action = {
            'name': _('open quotations'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': qt_rec.id,
        }
        return action
