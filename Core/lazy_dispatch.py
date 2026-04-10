from functools import lru_cache

from django.views.decorators.csrf import csrf_exempt
from django.utils.module_loading import import_string


@lru_cache(maxsize=64)
def _get_view_callable(module_path: str, class_name: str, actions_key: tuple[tuple[str, str], ...]):
    viewset_cls = import_string(f"{module_path}.{class_name}")
    return viewset_cls.as_view(dict(actions_key))


def lazy_viewset(module_path: str, class_name: str, actions: dict[str, str]):
    actions_key = tuple(sorted(actions.items()))

    @csrf_exempt
    def _view(request, *args, **kwargs):
        view = _get_view_callable(module_path, class_name, actions_key)
        return view(request, *args, **kwargs)

    _view.csrf_exempt = True
    return _view
