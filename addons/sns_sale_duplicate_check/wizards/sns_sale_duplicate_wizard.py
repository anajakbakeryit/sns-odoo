from odoo import _, fields, models
from odoo.exceptions import UserError


class SnsSaleDuplicateWizard(models.TransientModel):
    _name = 'sns.sale.duplicate.wizard'
    _description = 'Sales Order Duplicate Confirmation Wizard'

    order_id = fields.Many2one('sale.order', required=True, readonly=True)
    matched_order_ids = fields.Many2many('sale.order', readonly=True)
    override_reason = fields.Text(string='Reason to Proceed')

    def action_proceed(self):
        self.ensure_one()
        if not (self.override_reason or '').strip():
            raise UserError(_('Please explain why this order is not a duplicate before proceeding.'))
        matched_names = ', '.join(self.matched_order_ids.mapped('name'))
        self.order_id.message_post(body=_(
            'Duplicate override by %(user)s. Matched: %(matched)s. Reason: %(reason)s',
            user=self.env.user.name,
            matched=matched_names,
            reason=self.override_reason,
        ))
        self.order_id.duplicate_override_reason = self.override_reason
        return self.order_id.with_context(skip_sns_duplicate_check=True).action_confirm()

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
