from odoo import fields, models, api


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.html.report"

    @property
    def filter_brand(self):
        if self.show_brand_filter:
            return True
        return super().filter_brand

    show_brand_filter = fields.Boolean('Allow filtering by Brand')


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.html.report.line"

    def _get_domain(self, options, financial_report):
        self.ensure_one()
        res = super(AccountFinancialReportLine, self)._get_domain(options, financial_report)

        if options.get('brand'):
            brand = [a.get('id') for a in options.get('brand') if a.get('selected', False)]
            if brand:
                res.append(('brand_id', 'in', brand))

        return res
