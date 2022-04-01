import datetime
from . import thainlp
from odoo import models, fields, api, _
import json
import lxml
from odoo.tools import config, date_utils, get_lang
from odoo.tools.misc import formatLang, format_date
from babel.dates import get_quarter_names


class AccountReport(models.AbstractModel):

    _inherit = "account.report"

    @api.model
    def _get_templates_thai(self):
        return {
            'main_template_thai': 'Balance_Sheet_thai.main_template_thai',
            'main_table_header_template_thai': 'Balance_Sheet_thai.main_table_header_thai',
            'line_template': 'account_reports.line_template',
            'footnotes_template': 'account_reports.footnotes_template',
            'search_template': 'account_reports.search_template',
        }

    @api.model
    def _replace_class(self):
        """When printing pdf, we sometime want to remove/add/replace class for the report to look a bit different on paper
        this method is used for this, it will replace occurence of value key by the dict value in the generated pdf
        """
        return {b'o_account_reports_no_print': b'', b'table-responsive': b'', b'<a': b'<span', b'</a>': b'</span>'}

    def get_html(self, options, line_id=None, additional_context=None):
        '''
        return the html value of report, or html value of unfolded line
        * if line_id is set, the template used will be the line_template
        otherwise it uses the main_template. Reason is for efficiency, when unfolding a line in the report
        we don't want to reload all lines, just get the one we unfolded.
        '''
        # Prevent inconsistency between options and context.
        self = self.with_context(self._set_context(options))

        templates = self._get_templates_thai()
        report_manager = self._get_report_manager(options)

        render_values = {
            'report': {
                'name': self._get_report_name(),
                'summary': report_manager.summary,
                'company_name': self.env.company.name,
            },
            'options': options,
            'context': self.env.context,
            'model': self,
        }
        if additional_context:
            render_values.update(additional_context)

        if line_id:
            headers = options['headers']
            lines = self._get_lines(options, line_id=line_id)
            template = templates['line_template']
        else:

            headers, lines = self._get_table(options)

            options['headers'] = headers
            template = templates['main_template_thai']

            # divtotal = 1

            # for a in options['div']:
            #     if a['selected']:
            #         divtotal = a['id']

            # for x in lines:
            #     for y in x['columns']:
            #         if 'no_format' in y:
            #             if y.get('no_format'):
            #                 date_thai = float(y['no_format']) / divtotal
            #                 div_total_format = "{0:,.2f}".format(date_thai)
            #                 y['name'] = str(div_total_format) + ' ฿'

            if self.display_name == 'งบดุล':
                y = 0
                for x in options['headers'][0]:
                    key = list(options['headers'][0][y].keys())
                    if key[0] == "name":
                        if y != 0 and options['headers'][0][y]['name'] != "%":
                            date_thai = options['headers'][0][y]['name'].split("/")
                            date_thai[2] = int(date_thai[2]) + 543
                            day = date_thai[0].split(' ')
                            options['headers'][0][y]['name'] = day[2] + '  ' + date_thai[1] + '  ' + str(date_thai[2])
                        y += 1

            if self.display_name == 'รายงานงบดุล':
                y = 0
                for x in options['headers'][0]:
                    key = list(options['headers'][0][y].keys())

                    if key[0] == "name":
                        if y != 0 and options['headers'][0][y]['name'] != "%":
                            date_thai = options['headers'][0][y]['name'].split("/")
                            date_thai[2] = int(date_thai[2]) + 543
                            day = date_thai[0].split(' ')
                            options['headers'][0][y]['name'] = str(date_thai[2])
                        y += 1



            else:
                print(self.display_name)
        if options.get('hierarchy'):
            lines = self._create_hierarchy(lines, options)
        if options.get('selected_column'):
            lines = self._sort_lines(lines, options)
        #

        render_values['lines'] = {'columns_header': headers, 'lines': lines}

        # Manage footnotes.
        footnotes_to_render = []
        if self.env.context.get('print_mode', False):
            # we are in print mode, so compute footnote number and include them in lines values, otherwise, let the js compute the number correctly as
            # we don't know all the visible lines.
            footnotes = dict([(str(f.line), f) for f in report_manager.footnotes_ids])
            number = 0
            for line in lines:
                f = footnotes.get(str(line.get('id')))
                if f:
                    number += 1
                    line['footnote'] = str(number)
                    footnotes_to_render.append({'id': f.id, 'number': number, 'text': f.text})

        # Render.
        html = self.env.ref(template)._render(render_values)
        if self.env.context.get('print_mode', False):
            for k, v in self._replace_class().items():
                html = html.replace(k, v)
            # append footnote as well
            html = html.replace(b'<div class="js_account_report_footnotes"></div>',
                                self.get_html_footnotes(footnotes_to_render))

        return html

    def _get_reports_buttons(self):
        if self.display_name == 'รายงานงบดุล':
            return [
                {'name': _('Print Preview'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
                {'name': _('Export (XLSX)'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
                {'name': _('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
                {'name': _('Print Thai'), 'sequence': 11, 'action': 'print_pdf_thai', 'file_export_type': _('PDF')},
            ]
        else:
            return [
                {'name': _('Print Preview'), 'sequence': 1, 'action': 'print_pdf', 'file_export_type': _('PDF')},
                {'name': _('Export (XLSX)'), 'sequence': 2, 'action': 'print_xlsx', 'file_export_type': _('XLSX')},
                {'name': _('Save'), 'sequence': 10, 'action': 'open_report_export_wizard'},
            ]

    def print_pdf_thai(self, options):
        options['type'] = 'th'

        options['date']['string'] = self.get_date_thai(options['date']['date_to'])
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'pdf',
                     'financial_id': self.env.context.get('id'),
                     }
        }

    def get_date_thai(self, date_to):

        dateformat = date_to.split('-')

        day = int(dateformat[2])
        mon = int(dateformat[1])
        year = int(dateformat[0])

        datetime_obj = datetime.datetime(year=year, month=mon, day=day)
        return thainlp.thai_strftime(datetime_obj, "%-d %B %Y")

    def print_pdf(self, options):
        options['type'] = 'en'
        return {
            'type': 'ir_actions_account_report_download',
            'data': {'model': self.env.context.get('model'),
                     'options': json.dumps(options),
                     'output_format': 'pdf',
                     'financial_id': self.env.context.get('id'),
                     }
        }

    def get_pdf(self, options, minimal_layout=True):

        if not config['test_enable']:
            self = self.with_context(commit_assetsbundle=True)

        base_url = self.env['ir.config_parameter'].sudo().get_param('report.url') or self.env[
            'ir.config_parameter'].sudo().get_param('web.base.url')
        rcontext = {
            'mode': 'print',
            'base_url': base_url,
            'company': self.env.company,
        }
        if options['type'] == 'th':

            body = self.env['ir.ui.view']._render_template(
                "Balance_Sheet_thai.print_template_thai",
                values=dict(rcontext),
            )
            body_html = self.with_context(print_mode=True).get_html(options)

            body = body.replace(b'<body class="o_account_reports_body_print_thai">',
                                b'<body class="o_account_reports_body_print_thai">' + body_html)
        else:
            body = self.env['ir.ui.view']._render_template(
                "account_reports.print_template",
                values=dict(rcontext),
            )
            body_html = self.with_context(print_mode=True).get_html(options)

            body = body.replace(b'<body class="o_account_reports_body_print">',
                                b'<body class="o_account_reports_body_print">' + body_html)

        if minimal_layout:
            header = ''
            footer = self.env['ir.actions.report']._render_template("web.internal_layout", values=rcontext)
            spec_paperformat_args = {'data-report-margin-top': 10, 'data-report-header-spacing': 10}
            footer = self.env['ir.actions.report']._render_template("web.minimal_layout",
                                                                    values=dict(rcontext, subst=True, body=footer))
        else:
            rcontext.update({
                'css': '',
                'o': self.env.user,
                'res_company': self.env.company,
            })

            header = self.env['ir.actions.report']._render_template("web.external_layout", values=rcontext)
            header = header.decode('utf-8')  # Ensure that headers and footer are correctly encoded
            spec_paperformat_args = {}
            # Default header and footer in case the user customized web.external_layout and removed the header/footer
            headers = header.encode()
            footer = b''
            # parse header as new header contains header, body and footer
            try:
                root = lxml.html.fromstring(header)

            except lxml.etree.XMLSyntaxError:
                headers = header.encode()
                footer = b''
            header = headers

        landscape = False
        if len(self.with_context(print_mode=True).get_header(options)[-1]) > 5:
            landscape = True
            footer = ''
        if minimal_layout and options['type'] == 'th':
            return self.env['ir.actions.report']._run_wkhtmltopdf(
                [body],
                header=header,
                landscape=landscape,
                specific_paperformat_args=spec_paperformat_args,
            )

        return self.env['ir.actions.report']._run_wkhtmltopdf(
            [body],
            header=header, footer=footer,
            landscape=landscape,
            specific_paperformat_args=spec_paperformat_args,

        )

    @api.model
    def _get_dates_period(self, options, date_from, date_to, mode, period_type=None, strict_range=False):
        '''Compute some information about the period:
        * The name to display on the report.
        * The period type (e.g. quarter) if not specified explicitly.
        :param date_from:   The starting date of the period.
        :param date_to:     The ending date of the period.
        :param period_type: The type of the interval date_from -> date_to.
        :return:            A dictionary containing:
            * date_from * date_to * string * period_type * mode *
        '''

        def match(dt_from, dt_to):
            return (dt_from, dt_to) == (date_from, date_to)

        string = None
        # If no date_from or not date_to, we are unable to determine a period
        if not period_type or period_type == 'custom':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            if match(company_fiscalyear_dates['date_from'], company_fiscalyear_dates['date_to']):
                period_type = 'fiscalyear'
                if company_fiscalyear_dates.get('record'):
                    string = company_fiscalyear_dates['record'].name
            elif match(*date_utils.get_month(date)):
                period_type = 'month'
            elif match(*date_utils.get_quarter(date)):
                period_type = 'quarter'
            elif match(*date_utils.get_fiscal_year(date)):
                period_type = 'year'
            elif match(date_utils.get_month(date)[0], fields.Date.today()):
                period_type = 'today'
            else:
                period_type = 'custom'
        elif period_type == 'fiscalyear':
            date = date_to or date_from
            company_fiscalyear_dates = self.env.company.compute_fiscalyear_dates(date)
            record = company_fiscalyear_dates.get('record')
            string = record and record.name

        if not string:
            fy_day = self.env.company.fiscalyear_last_day
            fy_month = int(self.env.company.fiscalyear_last_month)
            if mode == 'single':
                string = _('%s') % (format_date(self.env, fields.Date.to_string(date_to)))
            elif period_type == 'year' or (
                    period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to)):
                string = date_to.strftime('%Y')
            elif period_type == 'fiscalyear' and (date_from, date_to) == date_utils.get_fiscal_year(date_to, day=fy_day,
                                                                                                    month=fy_month):
                string = '%s - %s' % (date_to.year - 1, date_to.year)
            elif period_type == 'month':
                string = format_date(self.env, fields.Date.to_string(date_to), date_format='MMM yyyy')
            elif period_type == 'quarter':
                quarter_names = get_quarter_names('abbreviated', locale=get_lang(self.env).code)
                string = u'%s\N{NO-BREAK SPACE}%s' % (
                    quarter_names[date_utils.get_quarter_number(date_to)], date_to.year)
            else:
                dt_from_str = format_date(self.env, fields.Date.to_string(date_from))
                dt_to_str = format_date(self.env, fields.Date.to_string(date_to))
                string = _('From %s\nto  %s') % (dt_from_str, dt_to_str)
        return {
            'string': string,
            'period_type': period_type,
            'mode': mode,
            'strict_range': strict_range,
            'date_from': date_from and fields.Date.to_string(date_from) or False,
            'date_to': fields.Date.to_string(date_to),
        }

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name
                                                          for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in
                                                      options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in
                                               options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for
                                                      category in (options.get('partner_categories') or [])]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(
                        journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view']._render_template(
                    self._get_templates().get('search_template', 'account_report.search_template'),
                    values=searchview_dict),
                }
        return info

    @api.model
    def _get_options(self, previous_options=None):
        # Create default options.
        options = {
            'unfolded_lines': previous_options and previous_options.get('unfolded_lines') or [],
        }

        # Multi-company is there for security purpose and can't be disabled by a filter.
        if self.filter_multi_company:
            if self._context.get('allowed_company_ids'):
                # Retrieve the companies through the multi-companies widget.
                companies = self.env['res.company'].browse(self._context['allowed_company_ids'])
            else:
                # When called from testing files, 'allowed_company_ids' is missing.
                # Then, give access to all user's companies.
                companies = self.env.companies
            if len(companies) > 1:
                options['multi_company'] = [
                    {'id': c.id, 'name': c.name} for c in companies
                ]

        # Call _init_filter_date/_init_filter_comparison because the second one must be called after the first one.
        if self.filter_date:
            self._init_filter_date(options, previous_options=previous_options)
        if self.filter_comparison:
            self._init_filter_comparison(options, previous_options=previous_options)
        if self.filter_analytic:
            options['analytic'] = self.filter_analytic
        # options['branch'] = self.get_branch()
        # options['operating_unit'] = self.get_operating_unit()
        self._init_filter_branch(options, previous_options=previous_options)
        self._init_filter_operating_unit(options, previous_options=previous_options)

        filter_list = [attr
                       for attr in dir(self)
                       if (attr.startswith('filter_') or attr.startswith('order_'))
                       and attr not in ('filter_date', 'filter_comparison', 'filter_multi_company')
                       and len(attr) > 7
                       and not callable(getattr(self, attr))]
        for filter_key in filter_list:
            options_key = filter_key[7:]
            init_func = getattr(self, '_init_%s' % filter_key, None)
            if init_func:
                init_func(options, previous_options=previous_options)
            else:
                filter_opt = getattr(self, filter_key, None)
                if filter_opt is not None:
                    if previous_options and options_key in previous_options:
                        options[options_key] = previous_options[options_key]
                    else:
                        options[options_key] = filter_opt

        return options

    def _init_filter_branch(self, options, previous_options=None):
        if self.filter_branch is None:
            return
        if previous_options and previous_options.get('branch'):
            branch_previous = dict((opt['id'], opt['selected']) for opt in previous_options['branch'] if 'selected' in
                                   opt)
        else:
            branch_previous = {}
        options['branch'] = []
        branch_read = self.env['res.branch'].search([], order="name")
        for c in branch_read:
            options['branch'].append({'id': c.id, 'name': c.name, 'selected': branch_previous.get(c.id)})

    def _init_filter_operating_unit(self, options, previous_options=None):
        if self.filter_operating_unit is None:
            return
        if previous_options and previous_options.get('operating_unit'):
            operating_unit_previous = dict((opt['id'], opt['selected']) for opt in previous_options['operating_unit'] if
                                           'selected' in opt)
        else:
            operating_unit_previous = {}
        operating_unit_read = self.env['operating.unit'].search([], order="name")
        options['operating_unit'] = []
        for c in operating_unit_read:
            options['operating_unit'].append(
                {'id': c.id, 'name': c.name, 'selected': operating_unit_previous.get(c.id)})


