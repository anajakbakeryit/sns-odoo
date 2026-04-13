from datetime import timedelta

from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    duplicate_override_reason = fields.Text(
        string='Duplicate Override Reason',
        tracking=True,
        copy=False,
    )

    def _get_duplicate_check_config(self):
        params = self.env['ir.config_parameter'].sudo()
        enabled = params.get_param('sns_sale_duplicate_check.enabled', 'True') == 'True'
        try:
            days = int(params.get_param('sns_sale_duplicate_check.days', 7))
        except (TypeError, ValueError):
            days = 7
        return enabled, max(days, 1)

    def _find_duplicate_orders(self):
        self.ensure_one()
        enabled, days = self._get_duplicate_check_config()
        if not enabled or not self.partner_id or not self.order_line:
            return self.env['sale.order']

        reference_date = self.date_order or fields.Datetime.now()
        window_start = reference_date - timedelta(days=days)
        window_end = reference_date + timedelta(days=days)

        candidates = self.search([
            ('id', '!=', self.id),
            ('company_id', '=', self.company_id.id),
            ('partner_id', '=', self.partner_id.id),
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', window_start),
            ('date_order', '<=', window_end),
        ])

        tolerance = 0.10
        my_products = {line.product_id.id: line.product_uom_qty for line in self.order_line if line.product_id}
        if not my_products:
            return self.env['sale.order']

        matched = self.env['sale.order']
        for order in candidates:
            for line in order.order_line:
                if not line.product_id or line.product_id.id not in my_products:
                    continue
                mine = my_products[line.product_id.id]
                theirs = line.product_uom_qty
                if mine <= 0 or theirs <= 0:
                    continue
                if abs(mine - theirs) / max(mine, theirs) <= tolerance:
                    matched |= order
                    break
        return matched

    def action_confirm(self):
        skip = self.env.context.get('skip_sns_duplicate_check')
        orders_to_check = self.filtered(lambda o: o.state in ('draft', 'sent'))
        if skip or not orders_to_check:
            return super().action_confirm()

        flagged = {}
        for order in orders_to_check:
            matches = order._find_duplicate_orders()
            if matches:
                flagged[order.id] = matches
        if not flagged:
            return super().action_confirm()

        order_id, matched = next(iter(flagged.items()))
        wizard = self.env['sns.sale.duplicate.wizard'].create({
            'order_id': order_id,
            'matched_order_ids': [(6, 0, matched.ids)],
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Possible Duplicate Sales Order'),
            'res_model': 'sns.sale.duplicate.wizard',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new',
        }
