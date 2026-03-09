from .settings import APP_VERSION, FORCE_SCRIPT_NAME

def app_version(request):
    return {'app_version': APP_VERSION}

def script_name_prefix(request):
    # Always defined ('' for none, never None)
    prefix = FORCE_SCRIPT_NAME or ''
    return {'script_name': prefix}
