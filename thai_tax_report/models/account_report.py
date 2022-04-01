from odoo import models, fields, api, _


class TaxReport(models.TransientModel):
    _inherit = "report.tax.report"

    def print_report_thai(self, report_type="qweb"):
        self.ensure_one()
        action = (
                report_type == "xlsx"
                and self.env.ref("thai_tax_report.tax.report.action_tax_report_xlsx")
                or self.env.ref("thai_tax_report.action_tax_report_pdf_thai")
        )
        return action.report_action(self, config=False)

    def _get_html_thai(self):
        result = {}
        rcontext = {}
        context = dict(self.env.context)
        report = self.browse(context.get("active_id"))
        if report:
            rcontext["o"] = report
            result["html"] = self.env.ref("thai_tax_report.report_tax_report_htmt_thai"
)._render(rcontext)
        return result

    @api.model
    def get_html_thai(self, given_context=None):
        return self.with_context(given_context)._get_html_thai()
