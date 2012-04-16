from django.conf import settings

# Custom context processors for sikteeri

def is_production(request):
    '''
    Add the constant 'is_production' to current context
    '''
    return dict(is_production=settings.PRODUCTION)
