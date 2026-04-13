from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError


class SnsCreditOverrideWizard(models.TransientModel):
    _name = 'sns.credit.override.wizard'
    _description = 'Sales Order Credit Limit Override Wizard'

    order_id = fields.Many2one('sale.order', required=True, readonly=True)
    partner_id = fields.Many2one(related='order_id.partner_id', readonly=True)
    currency_id = fields.Many2one(related='order_id.currency_id', readonly=True)
    partner_credit_limit = fields.Float(
        related='order_id.partner_id.credit_limit',
        readonly=True,
    )
    partner_outstanding_ar = fields.Monetary(
        related='order_id.partner_id.sns_outstanding_ar',
        currency_field='currency_id',
        readonly=True,
    )
    partner_pending_so = fields.Monetary(
        related='order_id.partner_id.sns_pending_so_amount',
        currency_field='currency_id',
        readonly=True,
    )
    order_amount = fields.Monetary(
        related='order_id.amount_total',
        currency_field='currency_id',
        readonly=True,
    )
    exceeds_by = fields.Monetary(
        currency_field='currency_id',
        readonly=True,
    )
    reason = fields.Text(string='Override Reason', required=True)

    def action_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('sales_team.group_sale_manager'):
            raise AccessError(_('Only Sales Managers can approve credit overrides.'))
        if not (self.reason or '').strip():
            raise UserError(_('A reason is required to override credit limit.'))
        self.order_id.write({
            'sns_credit_override_reason': self.reason,
            'sns_credit_override_user_id': self.env.user.id,
        })
        self.order_id.message_post(body=_(
            'Credit override by %(user)s. Exceeds by %(excess).2f %(ccy)s. Reason: %(reason)s',
            user=self.env.user.name,
            excess=self.exceeds_by,
            ccy=self.currency_id.name,
            reason=self.reason,
        ))
        return self.order_id.with_context(skip_sns_credit_check=True).action_confirm()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
