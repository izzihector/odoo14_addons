from odoo import models, fields

class Project (models.Model):
    _name = 'pr.project'
    _rec_name = 'name'
    _order = 'name'
    image = fields.Image('Image', attatchment=True)
    name = fields.Char('Name', required=True)
    budget = fields.Float('Budget')
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    type = fields.Selection([
        ('N', 'Normal'),
        ('U', 'Urgent')], string='Type' , default='N')
    department = fields.Char()
