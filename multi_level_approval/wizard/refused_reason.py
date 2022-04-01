from odoo import fields, models, api


class RefusedReason(models.TransientModel):
    _name = 'refused.reason'
    _description = 'Refused Reason'

    reason = fields.Text('Reason', required=True)

    def action_reason_apply(self):
        approval = self.env['multi.approval'].browse(
            self.env.context.get('active_ids'))
        return approval.action_refuse(reason=self.reason)