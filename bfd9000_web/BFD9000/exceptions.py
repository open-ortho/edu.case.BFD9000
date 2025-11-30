from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If the exception handler returned a response, add the standard error format.
    if response is not None:
        custom_data = {
            "error": {
                "code": "API_ERROR",
                "message": "An error occurred",
                "details": response.data
            }
        }

        # Try to determine a more specific error code based on status code
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            custom_data["error"]["code"] = "VALIDATION_ERROR"
            custom_data["error"]["message"] = "Validation failed"
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            custom_data["error"]["code"] = "AUTHENTICATION_REQUIRED"
            custom_data["error"]["message"] = "Authentication credentials were not provided."
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            custom_data["error"]["code"] = "PERMISSION_DENIED"
            custom_data["error"]["message"] = "You do not have permission to perform this action."
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            custom_data["error"]["code"] = "NOT_FOUND"
            custom_data["error"]["message"] = "Resource not found."
        elif response.status_code == status.HTTP_409_CONFLICT:
            custom_data["error"]["code"] = "CONFLICT"
            custom_data["error"]["message"] = "Resource conflict."
        
        # If response.data has a 'detail' key, use it as the message
        if isinstance(response.data, dict) and 'detail' in response.data:
            custom_data["error"]["message"] = response.data['detail']
            # Remove detail from details to avoid redundancy if it's the only thing
            if len(response.data) == 1:
                custom_data["error"]["details"] = None
        
        response.data = custom_data

    return response
