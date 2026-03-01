from .settings import APP_VERSION

def app_version(request):
    return {'app_version': APP_VERSION}
