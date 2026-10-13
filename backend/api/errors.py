class ProviderError(Exception):
    """A third-party service (routing, geocoding, weather) failed."""


class NoRouteError(Exception):
    """The routing service could not find a drivable route."""
