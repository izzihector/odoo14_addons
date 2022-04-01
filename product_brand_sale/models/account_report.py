from odoo import fields, models, api


class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    filter_brand = None
    @api.model
    def _get_options(self, previous_options=None):
        # options = {
        #     'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        # }

        # if self.filter_multi_company:
        #     if self._context.get('allowed_company_ids'):
        #         # Retrieve the companies through the multi-companies widget.
        #         companies = self.env['res.company'].browse(self._context['allowed_company_ids'])
        #     else:
        #         # When called from testing files, 'allowed_company_ids' is missing.
        #         # Then, give access to all user's companies.
        #         companies = self.env.companies
        #     if len(companies) > 1:
        #         options['multi_company'] = [
        #             {'id': c.id, 'name': c.name} for c in companies
        #             ]

        # if self.filter_analytic:
        #     options['analytic'] = self.filter_analytic
        if previous_options and previous_options.get('brand'):
            brand_previous = dict(
                (opt['id'], opt['selected']) for opt in previous_options['brand'] if 'selected' in opt)
        else:
            brand_previous = {}
        res = super(AccountReport, self)._get_options(previous_options)

        if self.filter_brand is None:
            return res

        res['brand'] = []
        brand_read = self.env['product.brand'].search([], order="name")
        for c in brand_read:
            res['brand'].append({'id': c.id, 'name': c.name, 'selected': brand_previous.get(c.id)})

        # self._init_filter_brand(options, previous_options=previous_options)
        return res

    # def _init_filter_brand(self, options, previous_options=None):
    #     if self.filter_brand is None:
    #         return
    #     if previous_options and previous_options.get('brand'):
    #         brand_previous = dict(
    #             (opt['id'], opt['selected']) for opt in previous_options['brand'] if 'selected' in opt)
    #     else:
    #         brand_previous = {}
    #     options['brand'] = []
    #     brand_read = self.env['product.brand'].search([], order="name")
    #     for c in brand_read:
    #         options['brand'].append({'id': c.id, 'name': c.name, 'selected': brand_previous.get(c.id)})
