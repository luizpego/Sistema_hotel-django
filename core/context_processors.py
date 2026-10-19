from core.permissions import ADMIN, RECEPTION, CLEANING, allowed


def navigation(request):
    return {
        "is_manager": allowed(request.user, ADMIN),
        "is_reception": allowed(request.user, ADMIN, RECEPTION),
        "is_cleaning": allowed(request.user, CLEANING) and not allowed(request.user, ADMIN, RECEPTION),
    }
