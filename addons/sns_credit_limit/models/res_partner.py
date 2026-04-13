from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    sns_outstanding_ar = fields.Monetary(
        string='Outstanding AR',
        compute='_compute_sns_credit_metrics',
        currency_field='currency_id',
        help='Sum of unpaid customer invoices amount_residual',
    )
    sns_pending_so_amount = fields.Monetary(
        string='Pending SO (uninvoiced)',
        compute='_compute_sns_credit_metrics',
        currency_field='currency_id',
    )
    sns_credit_used = fields.Monetary(
        string='Credit Used',
        compute='_compute_sns_credit_metrics',
        currency_field='currency_id',
    )
    sns_credit_available = fields.Monetary(
        string='Credit Available',
        compute='_compute_sns_credit_metrics',
        currency_field='currency_id',
    )
    sns_credit_used_pct = fields.Float(
        string='Credit Used (%)',
        compute='_compute_sns_credit_metrics',
    )

    @api.depends('credit_limit')
    def _compute_sns_credit_metrics(self):
        Move = self.env['account.move']
        SO = self.env['sale.order']
        for partner in self:
            moves = Move.search([
                ('partner_id', '=', partner.id),
                ('move_type', 'in', ('out_invoice', 'out_refund')),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ('not_paid', 'partial')),
            ])
            ar = sum(moves.mapped('amount_residual'))

            orders = SO.search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ('sale', 'done')),
                ('invoice_status', 'in', ('to invoice', 'no')),
            ])
            pending_so = sum(o.amount_total - o.amount_invoiced for o in orders if hasattr(o, 'amount_invoiced'))
            if not pending_so:
                pending_so = sum(
                    o.amount_total for o in orders
                    if o.invoice_status == 'to invoice'
                )

            partner.sns_outstanding_ar = ar
            partner.sns_pending_so_amount = pending_so
            used = ar + pending_so
            partner.sns_credit_used = used
            limit = partner.credit_limit or 0.0
            partner.sns_credit_available = max(limit - used, 0.0)
            partner.sns_credit_used_pct = (used / limit * 100.0) if limit > 0 else 0.0
