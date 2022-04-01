from odoo import fields, models, api


class MultiApprovalTypeLine(models.Model):
    _name = 'multi.approval.type.line'
    _description = 'Multi Aproval Type Lines'
    _order = 'sequence'

    name = fields.Char(string='Title', required=True)
    user_id = fields.Many2one(string='User', comodel_name="res.users",
                              required=True)
    type_id = fields.Many2one(
        string="Type", comodel_name="multi.approval.type")
    sequence = fields.Integer(string='Sequence')
    require_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ], string="Type of Approval", default='Required')
    
    def get_user(self):
        self.ensure_one()
        return self.user_id.id