from __future__ import annotations

from typing import Any, Type

from django.http import HttpRequest, HttpResponse
from reactivated.renderer import render_jsx_to_string

from server.rpc.context import get_context_class, get_context_processors
from server.rpc.core import Pick

template_registry: dict[str, Type[Template]] = {}


class Template(Pick):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        template_registry[cls.__name__] = cls

    def render(self, request: HttpRequest, status: int = 200) -> HttpResponse:
        props = self.model_dump(mode="json")

        context_dict: dict[str, Any] = {"template_name": self.__class__.__name__}
        for processor in get_context_processors():
            context_dict.update(processor(request))

        Context = get_context_class()
        context = Context(**context_dict).model_dump(mode="json")

        content = render_jsx_to_string(request, context, props)

        return HttpResponse(content, status=status)
