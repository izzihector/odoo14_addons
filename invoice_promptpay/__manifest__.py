{
    "name": "PromptPay Invoice Report",
    "version": "14.0.0.1",
    "author": "",
    "website": "https://www.scgl.co.th/",
    "category": "Accounting / Payment",
    "summary": "Use PromptPay QR code with invoice report",
    "depends": ["account"],
    "data": [
        'views/res_config_setting_views.xml',
    ],
    "external_dependencies": {"python": ["promptpay"]},
    "installable": True,
    "application": False,
}