from typing import Annotated

from fastapi import Depends, HTTPException, status

from backend.core.config import Settings, get_settings

LOCAL_MODE = "local"
DEMO_MODE = "demo"
DEMO_READ_ONLY_MESSAGE = "Demo mode is read-only"
DEMO_NOTICE = "This demonstration contains fictional, precomputed data."


SettingsDependency = Annotated[Settings, Depends(get_settings)]


def is_demo_mode(settings: Settings) -> bool:
    return settings.app_mode == DEMO_MODE


def require_writable_mode(settings: SettingsDependency) -> None:
    if is_demo_mode(settings):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=DEMO_READ_ONLY_MESSAGE,
        )


def app_info_payload(settings: Settings) -> dict[str, object]:
    demo_mode = is_demo_mode(settings)
    payload: dict[str, object] = {
        "app_mode": settings.app_mode,
        "read_only": demo_mode,
        "demo_data": demo_mode,
    }
    if demo_mode:
        payload["notice"] = DEMO_NOTICE
    return payload
