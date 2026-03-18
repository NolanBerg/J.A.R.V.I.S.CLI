"""Weather skill — current conditions via wttr.in (no API key needed)."""
from __future__ import annotations

import ssl
import urllib.error
import urllib.request

from jarvis.config import load_config, save_config
from jarvis.core import jarvis_say, jarvis_thinking, register

WTTR_URL = "https://wttr.in"


def _get_saved_city() -> str | None:
    return load_config().get("weather_city")


def _set_saved_city(city: str) -> None:
    cfg = load_config()
    cfg["weather_city"] = city
    save_config(cfg)


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context, falling back to unverified if certs aren't set up."""
    try:
        ctx = ssl.create_default_context()
        # Quick test — if this doesn't raise, certs are fine
        urllib.request.urlopen("https://wttr.in", timeout=2, context=ctx)
        return ctx
    except (ssl.SSLError, urllib.error.URLError, OSError):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


_ctx: ssl.SSLContext | None = None


def _get_ssl_ctx() -> ssl.SSLContext:
    global _ctx
    if _ctx is None:
        _ctx = _ssl_context()
    return _ctx


def _fetch_weather(city: str | None, timeout: int = 10) -> str | None:
    """Fetch weather from wttr.in. If city is None, auto-detect via IP."""
    location = city.replace(" ", "%20") if city else ""
    url = f"{WTTR_URL}/{location}?format=%l:+%c+%t+%w+%h+humidity"
    req = urllib.request.Request(url, headers={"User-Agent": "curl/7.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_get_ssl_ctx()) as resp:
            return resp.read().decode("utf-8").strip()
    except (urllib.error.URLError, OSError):
        return None


@register(
    "weather",
    aliases=["wttr"],
    description="Current weather. Usage: weather [city] | weather setup <city>",
)
def handle_weather(raw: str) -> None:
    # Strip command prefix
    query = raw.strip()
    for prefix in ("weather ", "wttr "):
        if query.lower().startswith(prefix):
            query = query[len(prefix):].strip()
            break
    else:
        query = ""

    lower = query.lower()

    # weather setup <city>
    if lower.startswith("setup"):
        city = query[5:].strip()
        if not city:
            jarvis_say("Usage: [bold]weather setup <city>[/bold]  (e.g. weather setup Austin)")
            return
        _set_saved_city(city)
        jarvis_say(f"Default city set to [bold]{city}[/bold].")
        # Show weather for the newly saved city
        with jarvis_thinking(f"Fetching weather for {city}..."):
            result = _fetch_weather(city)
        if result:
            jarvis_say(result)
        return

    # weather <city>  or  weather (use saved/auto)
    city = query if query else _get_saved_city()
    label = city or "your location (auto-detected)"

    with jarvis_thinking(f"Fetching weather for {label}..."):
        result = _fetch_weather(city)

    if result:
        jarvis_say(result)
        if not city:
            jarvis_say(
                "[dim]Location auto-detected from IP. "
                "Run [bold]weather setup <city>[/bold] to set your default.[/dim]"
            )
    else:
        jarvis_say(
            "[red]Could not fetch weather.[/red] Check your internet connection."
        )
