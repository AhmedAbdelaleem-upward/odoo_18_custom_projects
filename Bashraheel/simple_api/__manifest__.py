{
    'name': 'Simple API',
    'version': '18.0.1.0.0',
    'summary': 'Simplified FastAPI endpoints for Odoo',
    'category': 'API/Integration',
    'depends': [
        'base',
        'fastapi',
    ],
    'data': [
        'data/simple_api_endpoint.xml',
    ],
    'external_dependencies': {
        'python': ['fastapi', 'pyjwt', 'pydantic'],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
