from baize.asgi.responses import FileResponse as BaizeFileResponse
from fastapi.responses import Response as FastApiResponse


class FastApiBaizeFileResponse(FastApiResponse):
    _baize_response: BaizeFileResponse

    def __init__(self, path, **kwargs) -> None:
        filepath = str(kwargs.get("filepath", kwargs.get("path", path)))
        kwargs.pop("filepath", None)
        kwargs.pop("path", None)
        self._baize_response = BaizeFileResponse(filepath, **kwargs)
        super().__init__(None)

    def __call__(self, *args, **kwargs):
        return self._baize_response(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._baize_response, name)
