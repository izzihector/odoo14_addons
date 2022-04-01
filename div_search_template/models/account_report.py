from odoo import fields, models, api

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    @api.model
    def _get_options(self, previous_options=None):

        if previous_options and previous_options.get('div'):
            div_previous = dict(
                (opt['id'], opt['selected']) for opt in previous_options['div'] if 'selected' in opt)
        else:
            div_previous = {}

        res = super(AccountReport, self)._get_options(previous_options)
        divtotal = 1
        res['div'] = []
        div_read = self.env['div.search.template'].search([])
        for c in div_read:

            res['div'].append({'id': c.id, 'name': c.div_name, 'selected': div_previous.get(c.id),'show_div_filter': c.show_div_filter,})

            #
            # for a in res['div']:
            #     if a['selected']:
            #         divtotal = a['id']
            #
            # for x in res:
            #     for y in x['columns']:
            #         if 'no_format' in y:
            #             if y.get('no_format'):
            #                 date_thai = float(y['no_format']) / divtotal
            #                 div_total_format = "{0:,.2f}".format(date_thai)
            #                 y['name'] = str(div_total_format) + ' ฿'

            # div_1k = res['div'][x]['selected']



        # self._init_filter_brand(options, previous_options=previous_options)
        return res

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

            divtotal = 1


            # div1 = options['div'][0]['selected']

            for a in options['div']:
                if a['selected']:
                    divtotal = a['show_div_filter']

            for x in lines:
                for y in x['columns']:
                    if 'no_format' in y:
                        if y.get('no_format'):
                            date_thai = float(y['no_format']) / divtotal
                            div_total_format = "{0:,.2f}".format(date_thai)
                            y['name'] = str(div_total_format) + ' ฿'



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
