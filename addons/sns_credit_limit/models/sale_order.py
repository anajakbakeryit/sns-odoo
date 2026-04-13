from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sns_credit_override_reason = fields.Text(
        string='Credit Override Reason',
        tracking=True,
        copy=False,
    )
    sns_credit_override_user_id = fields.Many2one(
        'res.users',
        string='Credit Override Approver',
        tracking=True,
        copy=False,
        readonly=True,
    )
    sns_credit_limit_display = fields.Float(
        string='Customer Credit Limit',
        related='partner_id.credit_limit',
    )
    sns_credit_available_display = fields.Monetary(
        string='Customer Credit Available',
        related='partner_id.sns_credit_available',
        currency_field='currency_id',
    )

    def _sns_check_credit(self):
        self.ensure_one()
        limit = self.partner_id.credit_limit or 0.0
        if limit <= 0:
            return True, 0.0
        used_after = self.partner_id.sns_credit_used + self.amount_total
        excess = used_after - limit
        return excess <= 0, excess

    def action_confirm(self):
        if self.env.context.get('skip_sns_credit_check'):
            return super().action_confirm()

        orders_to_check = self.filtered(lambda o: o.state in ('draft', 'sent'))
        for order in orders_to_check:
            if not order.partner_id:
                continue
            within, excess = order._sns_check_credit()
            if not within:
                wizard = self.env['sns.credit.override.wizard'].create({
                    'order_id': order.id,
                    'exceeds_by': excess,
                })
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Credit Limit Exceeded'),
                    'res_model': 'sns.credit.override.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new',
                }
        return super().action_confirm()
