from odoo import fields, models, api, _


class MultiApproval(models.Model):
    _name = 'multi.approval'
    _description = 'Multi Aproval'
    _inherit = 'mail.thread'

    code = fields.Char(default=_('New'))
    name = fields.Char(string='Title', required=True)
    state = fields.Selection(
        [('Draft', 'Draft'),
         ('Submitted', 'Submitted'),
         ('Approved', 'Approved'),
         ('Refused', 'Refused'),
         ('Cancel', 'Cancel')], default='Draft', tracking=True)
    type_id = fields.Many2one(
        string="Type", comodel_name="multi.approval.type", required=True)
    user_id = fields.Many2one(
        string='Request by', comodel_name="res.users",
        required=True, default=lambda self: self.env.uid)
    priority = fields.Selection(
        [('0', 'Normal'),
         ('1', 'Medium'),
         ('2', 'High'),
         ('3', 'Very High')], string='Priority', default='0')
    request_date = fields.Datetime(
        string='Request Date', default=fields.Datetime.now)
    description = fields.Html('Description')

    document_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ], string="Document opt", default='Optional',
        readonly=True, related='type_id.document_opt')
    attachment_ids = fields.Many2many('ir.attachment', string='Documents')

    contact_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Contact opt", default='None',
        readonly=True, related='type_id.contact_opt')
    contact_id = fields.Many2one('res.partner', string='Contact')

    date_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Date opt", default='None',
        readonly=True, related='type_id.date_opt')
    date = fields.Date('Date')

    period_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Period opt", default='None',
        readonly=True, related='type_id.period_opt')
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')

    item_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Item opt", default='None',
        readonly=True, related='type_id.item_opt')
    item_id = fields.Many2one('product.product', string='Item')

    multi_items_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Multi Items opt", default='None',
        readonly=True, related='type_id.multi_items_opt')
    item_ids = fields.Many2many('product.product', string='Items')

    quantity_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Quantity opt", default='None',
        readonly=True, related='type_id.quantity_opt')
    quantity = fields.Float('Quantity')

    amount_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Amount opt", default='None',
        readonly=True, related='type_id.amount_opt')
    amount = fields.Float('Amount')

    payment_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Payment opt", default='None',
        readonly=True, related='type_id.payment_opt')
    payment = fields.Float('Payment')

    reference_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Reference opt", default='None',
        readonly=True, related='type_id.reference_opt')
    reference = fields.Char('Reference')

    location_opt = fields.Selection(
        [('Required', 'Required'),
         ('Optional', 'Optional'),
         ('None', 'None'),
         ], string="Location opt", default='None',
        readonly=True, related='type_id.location_opt')
    location = fields.Char('Location')
    line_ids = fields.One2many('multi.approval.line', 'approval_id',
                               string="Lines")
    line_id = fields.Many2one('multi.approval.line', string="Line", copy=False)
    deadline = fields.Date(string='Deadline', related='line_id.deadline')
    pic_id = fields.Many2one(
        'res.users', string='Approver', related='line_id.user_id')
    is_pic = fields.Boolean(compute='_check_pic')
    follower = fields.Text('Following Users', default='[]', copy=False)

    attachment_number = fields.Integer(
        'Number of Attachments', compute='_compute_attachment_number')

    def _check_pic(self):
        for r in self:
            r.is_pic = r.pic_id.id == self.env.uid

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'multi.approval'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count'])
                          for data in attachment_data)
        for r in self:
            r.attachment_number = attachment.get(r.id, 0)

    def action_cancel(self):
        recs = self.filtered(lambda x: x.state == 'Draft')
        recs.write({'state': 'Cancel'})

    def action_submit(self):
        recs = self.filtered(lambda x: x.state == 'Draft')
        for r in recs:
            # Check if document is required
            if r.document_opt == 'Required' and r.attachment_number < 1:
                raise Warning(_('Document is required !'))
            if not r.type_id.line_ids:
                raise Warning(_(
                    'There is no approver of the type "{}" !'.format(
                        r.type_id.name)))
            r.state = 'Submitted'
        recs._create_approval_lines()

    def _create_approval_lines(self):
        ApprovalLine = self.env['multi.approval.line']
        for r in self:
            lines = r.type_id.line_ids.sorted('sequence')
            last_seq = 0
            for l in lines:
                line_seq = l.sequence
                if not line_seq or line_seq <= last_seq:
                    line_seq = last_seq + 1
                last_seq = line_seq
                vals = {
                    'name': l.name,
                    'user_id': l.get_user(),
                    'sequence': line_seq,
                    'require_opt': l.require_opt,
                    'approval_id': r.id
                }
                if l == lines[0]:
                    vals.update({'state': 'Waiting for Approval'})
                approval = ApprovalLine.create(vals)
                if l == lines[0]:
                    r.line_id = approval

    def get_follow_key(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        k = '[res.users:{}]'.format(user_id)
        return k

    def update_follower(self, user_id):
        self.ensure_one()
        k = self.get_follow_key(user_id)
        follower = self.follower
        if k not in follower:
            self.follower = follower + k

    def set_approved(self):
        self.ensure_one()
        self.state = 'Approved'

    def set_refused(self, reason=''):
        self.ensure_one()
        self.state = 'Refused'

    def action_approve(self):
        ret_act = None
        recs = self.filtered(lambda x: x.state == 'Submitted')
        for rec in recs:
            if not rec.is_pic:
                msg = _('{} do not have the authority to approve this request !'.format(rec.env.user.name))
                self.sudo().message_post(body=msg)
                return False
            line = rec.line_id
            if not line or line.state != 'Waiting for Approval':
                # Something goes wrong!
                self.message_post(body=_('Something goes wrong!'))
                return False

            # Update follower
            rec.update_follower(self.env.uid)

            # check if this line is required
            other_lines = rec.line_ids.filtered(
                lambda x: x.sequence >= line.sequence and x.state == 'Draft')
            if not other_lines:
                ret_act = rec.set_approved()
            else:
                next_line = other_lines.sorted('sequence')[0]
                next_line.write({
                    'state': 'Waiting for Approval',
                })
                rec.line_id = next_line
            line.set_approved()
            msg = _('I approved')
            rec.message_post(body=msg)
        if ret_act:
            return ret_act

    def action_refuse(self, reason=''):
        ret_act = None
        recs = self.filtered(lambda x: x.state == 'Submitted')
        for rec in recs:
            if not rec.is_pic:
                msg = _('{} do not have the authority to approve this request !'.format(rec.env.user.name))
                self.sudo().message_post(body=msg)
                return False
            line = rec.line_id
            if not line or line.state != 'Waiting for Approval':
                # Something goes wrong!
                self.message_post(body=_('Something goes wrong!'))
                return False

            # Update follower
            rec.update_follower(self.env.uid)

            # check if this line is required
            if line.require_opt == 'Required':
                ret_act = rec.set_refused(reason)
                draft_lines = rec.line_ids.filtered(lambda x: x.state == 'Draft')
                if draft_lines:
                    draft_lines.write({'state': 'Cancel'})
            else:  # optional
                other_lines = rec.line_ids.filtered(
                    lambda x: x.sequence >= line.sequence and x.state == 'Draft')
                if not other_lines:
                    ret_act = rec.set_refused(reason)
                else:
                    next_line = other_lines.sorted('sequence')[0]
                    next_line.state = 'Waiting for Approval'
                    rec.line_id = next_line
            line.set_refused(reason)
            msg = _('I refused due to this reason: {}'.format(reason))
            rec.message_post(body=msg)
        if ret_act:
            return ret_act

    @api.model
    def create(self, vals):
        vals['code'] = self.env['ir.sequence'].next_by_code(
            'multi.approval') or _('New')
        result = super(MultiApproval, self).create(vals)
        return result

