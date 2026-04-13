from datetime import timedelta

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _sns_cron_credit_followup(self):
        params = self.env['ir.config_parameter'].sudo()
        enabled = params.get_param('sns_credit_limit.followup_enabled', 'True') == 'True'
        if not enabled:
            return
        try:
            days = int(params.get_param('sns_credit_limit.followup_days', 7))
        except (TypeError, ValueError):
            days = 7
        cutoff = fields.Date.context_today(self) - timedelta(days=days)

        overdue = self.search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('invoice_date_due', '<', cutoff),
        ])

        template = self.env.ref(
            'sns_credit_limit.mail_template_sns_credit_followup',
            raise_if_not_found=False,
        )
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)

        for move in overdue:
            existing = self.env['mail.activity'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
                ('summary', '=', 'Credit Follow-up'),
            ], limit=1)
            if existing:
                continue
            if activity_type:
                self.env['mail.activity'].create({
                    'activity_type_id': activity_type.id,
                    'summary': 'Credit Follow-up',
                    'note': f'Invoice {move.name} is overdue ({move.amount_residual} {move.currency_id.name} outstanding).',
                    'res_model_id': self.env['ir.model']._get_id('account.move'),
                    'res_id': move.id,
                    'user_id': (move.invoice_user_id or move.partner_id.user_id or self.env.user).id,
                })
            if template:
                template.send_mail(move.id, force_send=False)
