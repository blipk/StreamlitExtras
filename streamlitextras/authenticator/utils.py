import json
import requests


# Proxy for handling pyrebase/firebase errors
def handle_firebase_action(
    action_function, exception_type, error_dict, *fn_args, **fn_kwargs
):
    """
    Handler for pyrebase/firebase actions.
    """
    error = None
    result = None
    try:
        # print("Args", fn_args, fn_kwargs)
        result = action_function(*fn_args, **fn_kwargs)
    except requests.HTTPError as e:
        # Pyrebase/4 is intercepting and raising an incorrectly initialized requests.HTTPError,
        # so the response has to be extracted from builtin BaseException args rather than e.response
        response_dict = json.loads(e.args[0].response.text.replace('"', '"'))
        error_type = None
        try:
            error_type = response_dict["error"]["message"]
        except:
            try:
                error_type = response_dict["error"]["errors"][0]["message"]
            except:
                pass

        if e.args[0].response.status_code == 400:
            if not error_dict:
                error = exception_type(
                    f"Unknown {exception_type.__name__} while trying to {action_function.__name__} ({error_type})",
                    error_type,
                    e.args[0],
                )
            else:
                if error_type in error_dict:
                    error = exception_type(
                        error_dict[error_type], error_type, e.args[0]
                    )
                else:
                    for key in error_dict:
                        if key in error_type:
                            message = error_dict[key] + " " + error_type.split(" : ")[1]
                            error = exception_type(message, error_type, e.args[0])
                if not error:
                    error = exception_type(
                        f"Unknown {exception_type.__name__} while trying to {action_function.__name__} ({error_type})",
                        error_type,
                        e.args[0],
                    )
        else:
            error = exception_type(
                f"Storage network error, please try again later ({e.args[0].response.status_code}) ({error_type})",
                error_type,
                e.args[0],
            )
            print(e.args[0])
        if not error:
            raise
    except requests.ConnectionError as e:
        error = exception_type(
            "Storage connection error, please try again later", f"SERVER_{e.args[0]}", e
        )

    return (result, error)
