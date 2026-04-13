{
    'name': 'SNS Sale Order Duplicate Check',
    'version': '18.0.1.0.0',
    'summary': 'Warn user when confirming a sales order that looks like a duplicate',
    'author': 'foilss',
    'website': 'https://www.foilss.com',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['sale', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sns_sale_duplicate_wizard_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
