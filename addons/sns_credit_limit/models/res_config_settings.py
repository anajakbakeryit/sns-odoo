from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sns_credit_followup_days = fields.Integer(
        string='Overdue Follow-up Threshold (days)',
        config_parameter='sns_credit_limit.followup_days',
        default=7,
    )
    sns_credit_followup_enabled = fields.Boolean(
        string='Enable Overdue Follow-up Emails',
        config_parameter='sns_credit_limit.followup_enabled',
        default=True,
    )
