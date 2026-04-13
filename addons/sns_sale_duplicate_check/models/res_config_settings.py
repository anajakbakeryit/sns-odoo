from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sns_duplicate_check_enabled = fields.Boolean(
        string='Enable SO Duplicate Check',
        config_parameter='sns_sale_duplicate_check.enabled',
        default=True,
    )
    sns_duplicate_check_days = fields.Integer(
        string='Duplicate Check Window (days)',
        config_parameter='sns_sale_duplicate_check.days',
        default=7,
    )
