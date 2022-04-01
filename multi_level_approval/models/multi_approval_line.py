from odoo import fields, models, api


class MultiApprovalLine(models.Model):
    _name = 'multi.approval.line'
    _description = 'Multi Aproval Line'
    _order = 'sequence'
    
    name = fields.Char(string='Title', required=True)
    user_id = fields.Many2one(string='User', comodel_name="res.users",
                              required=True)
    require_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ], string="Type of Approval", default='Required')
    sequence = fields.Integer(string='Sequence')
    approval_id = fields.Many2one(
        string="Approval", comodel_name="multi.approval")
    state = fields.Selection(
        [('Draft', 'Draft'),
         ('Waiting for Approval', 'Waiting for Approval'),
         ('Approved', 'Approved'),
         ('Refused', 'Refused'),
         ('Cancel', 'Cancel'),
         ], default="Draft")
    refused_reason = fields.Text('Refused Reason')
    deadline = fields.Date(string='Deadline')
    
    def set_approved(self):
        self.ensure_one()
        self.state = 'Approved'
    
    def set_refused(self, reason=''):
        self.ensure_one()
        self.write({
            'state': 'Refused',
            'refused_reason': reason
        })
        