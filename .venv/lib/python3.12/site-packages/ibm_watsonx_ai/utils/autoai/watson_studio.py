#  -----------------------------------------------------------------------------------------
#  (C) Copyright IBM Corp. 2023-2024.
#  https://opensource.org/licenses/BSD-3-Clause
#  -----------------------------------------------------------------------------------------

__all__ = [
    'get_project',
]


from typing import Any

from .errors import NotInWatsonStudio, CredentialsNotFound


def get_project() -> Any:
    """Try to import project_lib and get user corresponding project."""
    try:
        from project_lib import Project

    except ModuleNotFoundError:
        raise NotInWatsonStudio(reason="You are not in Watson Studio or Watson Studio Desktop environment. "
                                       "Cannot access to project metadata.")

    try:
        access = Project.access()

    except RuntimeError:
        raise CredentialsNotFound(reason="Your WSD environment does not have correctly configured "
                                         "connection to WML Server or you are not in WSD environment. "
                                         "In that case, please provide WMLS credentials and space_id.")

    return access