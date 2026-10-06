"""Optional location field: search, device location or map tap, shared only after Confirm."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx
from nicegui import ui
from nicegui.events import GenericEventArguments
from schemas.api import approximate, join_place_name
from services.geocoding import (
    autocomplete_places,
    is_valid_point,
    reverse_geocode,
    search_places,
)

from components.ui_kit import crisis_button, crisis_heading, crisis_input

logger = logging.getLogger(__name__)

# The world overview, shown first and after the location is removed.
_DEFAULT_CENTER = (20.0, 0.0)
_DEFAULT_ZOOM = 3
# The close-up used when search or device location picks a place.
_PIN_ZOOM = 12
_SUGGESTION_DEBOUNCE_SECONDS = 0.5
_SUGGESTION_HINT = "Type at least 3 characters for suggestions."
_LOOKUP_ERRORS = (httpx.HTTPError, RuntimeError, ValueError, KeyError, TypeError)


@dataclass(frozen=True)
class SelectedLocation:
    """A confirmed point and the place names found for it."""

    latitude: float
    longitude: float
    country: str | None = None
    region: str | None = None
    city: str | None = None

    def as_api_location(self) -> dict[str, str | float | None]:
        """Approximate coordinates and broad place names."""
        return {
            "location_name": join_place_name(self.city, self.region, self.country)
            or None,
            "country": self.country,
            "region": self.region,
            "city": self.city,
            "latitude": approximate(self.latitude),
            "longitude": approximate(self.longitude),
        }


class LocationPicker:
    def __init__(self, on_change: Callable[[], None] | None = None) -> None:
        self._on_change = on_change
        self._selected_point: tuple[float, float] | None = None
        self._confirmed_location: SelectedLocation | None = None
        self._marker: Any | None = None
        self._search_generation = 0
        self._pin_revision = 0
        self._suggestion_task: asyncio.Task[None] | None = None
        self._selected_search_label = ""
        self._build()

    def _build(self) -> None:
        """Search controls beside the map on desktop, stacked on mobile."""
        with ui.column().classes("crisis-location-panel w-full"):
            with ui.row().classes("w-full items-center justify-between"):
                crisis_heading("Add a location", 3)
                ui.label("Optional").classes("text-caption")

            ui.label(
                "Location is optional. Search for a city or area, use your current "
                "location, or select a point on the map."
            ).classes("text-body-sm")

            with ui.element("div").classes("crisis-location-workspace"):
                with ui.column().classes("crisis-location-controls"):
                    with ui.column().classes("w-full"):
                        with ui.element("div").classes("crisis-location-search-wrap"):
                            self.search_input = crisis_input(
                                "Search for a city or area",
                                placeholder="e.g. Kathmandu, Nepal",
                            ).classes("w-full")

                            self.search_input.on_value_change(
                                self._schedule_suggestions
                            )

                            self.search_results = ui.column().classes(
                                "crisis-location-results"
                            )

                        self.search_feedback = ui.label(_SUGGESTION_HINT).classes(
                            "text-caption crisis-location-inline-feedback"
                        )
                        ui.label(
                            "Suggestions send your search text to Photon."
                        ).classes("text-caption")

                        self.manual_search_button = crisis_button(
                            "Search location",
                            variant="secondary",
                            icon="search",
                            on_click=self._search_manually,
                        )

                    self.current_location_button = crisis_button(
                        "Use my current location",
                        variant="secondary",
                        icon="my_location",
                        on_click=self._use_current_location,
                    )

                    self.location_status = ui.label("No location selected.").classes(
                        "text-body-sm"
                    )
                    ui.label(
                        "Only an approximate area (about 1 km) is shared with "
                        "your report, not the exact pin."
                    ).classes("text-caption")

                    with ui.row().classes("crisis-location-actions w-full"):
                        self.confirm_button = crisis_button(
                            "Confirm location",
                            variant="secondary",
                            icon="place",
                            on_click=self._confirm_location,
                        )
                        self.confirm_button.disable()
                        self.remove_button = crisis_button(
                            "Remove location",
                            variant="ghost",
                            icon="close",
                            on_click=self._clear_location,
                        )
                        self.remove_button.disable()

                with ui.column().classes("crisis-location-map-column"):
                    self.map_view = ui.leaflet(
                        center=_DEFAULT_CENTER,
                        zoom=_DEFAULT_ZOOM,
                        options={"scrollWheelZoom": False, "worldCopyJump": True},
                    ).classes("crisis-report-map")
                    self.map_view.on("map-click", self._on_map_click)

            with ui.expansion(
                "How is my location used?",
                icon="privacy_tip",
            ).classes("w-full"):
                ui.label(
                    "Search suggestions use Photon. Confirming a pin sends its "
                    "coordinates to Nominatim to suggest an area name. Map tiles "
                    "are provided by OpenStreetMap, which may receive your IP "
                    "address. Avoid entering personal or home addresses."
                ).classes("text-caption")

    def _notify_change(self, _: Any = None) -> None:
        """Tell the form its review step is out of date."""
        if self._on_change is not None:
            self._on_change()

    def _set_pin(self, lat: float, lon: float, move_map: bool = True) -> None:
        """Move the pin and drop any earlier confirmation; move_map=False keeps the current view."""
        if not is_valid_point(lat, lon):
            ui.notify("This location has invalid coordinates.", type="warning")
            return

        self._selected_point = (lat, lon)
        self._pin_revision += 1
        self._search_generation += 1
        self._confirmed_location = None
        if self._marker is None:
            self._marker = self.map_view.marker(latlng=self._selected_point)
        else:
            self._marker.move(lat, lon)
        if move_map:
            self.map_view.set_center(self._selected_point)
            self.map_view.set_zoom(_PIN_ZOOM)
        self.location_status.set_text(
            f"Selected pin near {lat:.2f}, {lon:.2f}. Confirm to add this location."
        )
        self.confirm_button.enable()
        self.remove_button.enable()
        self.search_results.clear()
        self._notify_change()
        self.location_status.classes(remove="crisis-location-status--error")

    def _on_map_click(self, event: GenericEventArguments) -> None:
        try:
            latlng = event.args["latlng"]
            self._clear_search_text()
            self._set_pin(float(latlng["lat"]), float(latlng["lng"]), move_map=False)
        except (KeyError, TypeError, ValueError, OverflowError):
            ui.notify("Unable to read that map position.", type="warning")

    def _clear_search_text(self) -> None:
        self._selected_search_label = ""
        self.search_input.value = ""

    def _cancel_pending_search(self) -> int:
        """Cancel the running lookup and clear old suggestions; returns the new search id."""
        self._search_generation += 1
        if self._suggestion_task is not None and not self._suggestion_task.done():
            self._suggestion_task.cancel()
        self.search_results.clear()
        return self._search_generation

    def _schedule_suggestions(self, _: Any = None) -> None:
        """Suggest places after the user stops typing, not on every key."""
        query = (self.search_input.value or "").strip()
        if query == self._selected_search_label:
            return
        self._selected_search_label = ""
        generation = self._cancel_pending_search()

        if len(query) < 3:
            self.search_feedback.set_text(_SUGGESTION_HINT)
            return

        self.search_feedback.set_text("Searching locations...")

        self._suggestion_task = asyncio.create_task(
            self._load_suggestions(query, generation)
        )

    async def _load_suggestions(self, query: str, generation: int) -> None:
        """Fetch suggestions and show them unless the text has changed meanwhile."""
        try:
            await asyncio.sleep(_SUGGESTION_DEBOUNCE_SECONDS)
            places = await autocomplete_places(query)
        except asyncio.CancelledError:
            return
        except _LOOKUP_ERRORS:
            logger.warning("Location suggestions failed", exc_info=True)
            if generation == self._search_generation:
                self.search_results.clear()
                self.search_feedback.set_text(
                    "Live suggestions are unavailable. Select Search location "
                    "or tap the map."
                )
            return

        if (
            generation != self._search_generation
            or query != (self.search_input.value or "").strip()
        ):
            return
        self._display_places(places)

    def _display_places(self, places: list[dict[str, str | float]]) -> None:
        """Show the suggestions, or say there are none."""
        self.search_results.clear()
        if not places:
            self.search_feedback.set_text(
                "No matching places. Try a broader name or tap the map."
            )
            return

        self.search_feedback.set_text("")
        with self.search_results:
            for place in places:
                ui.button(
                    str(place["name"]),
                    on_click=lambda _, p=place: self._choose_place(p),
                ).props("flat no-caps align=left").classes(
                    "crisis-location-result w-full"
                )

    async def _search_manually(self) -> None:
        """Search on button click, for when live suggestions are unavailable."""
        query = (self.search_input.value or "").strip()
        if len(query) < 2:
            self.search_feedback.set_text("Enter at least 2 characters to search.")
            return

        generation = self._cancel_pending_search()
        self.search_feedback.set_text("Searching for this location...")
        self.manual_search_button.disable()
        try:
            places = await search_places(query)
        except _LOOKUP_ERRORS:
            logger.warning("Explicit location search failed", exc_info=True)
            if generation == self._search_generation:
                self.search_feedback.set_text(
                    "Search is unavailable. Tap the map or skip location."
                )
            return
        finally:
            self.manual_search_button.enable()

        if (
            generation == self._search_generation
            and query == (self.search_input.value or "").strip()
        ):
            self._display_places(places)

    def _choose_place(self, place: dict[str, str | float]) -> None:
        """Move the pin to the chosen result; the user still has to confirm it."""
        try:
            name = str(place["name"])
            self._selected_search_label = name
            self.search_input.value = name
            self.search_feedback.set_text("Suggestion selected. Confirm the pin below.")
            self._set_pin(float(place["lat"]), float(place["lon"]))
        except (KeyError, TypeError, ValueError):
            ui.notify("This search result could not be selected.", type="warning")

    async def _use_current_location(self) -> None:
        """Ask the browser for the device location."""
        self.current_location_button.disable()
        self.location_status.set_text("Requesting your browser location...")
        try:
            result = await ui.run_javascript(
                """
                new Promise((resolve) => {
                    if (!window.isSecureContext) {
                        resolve({error: 'insecure'});
                        return;
                    }
                    if (!navigator.geolocation) {
                        resolve({error: 'unsupported'});
                        return;
                    }
                    navigator.geolocation.getCurrentPosition(
                        (position) => resolve({
                            lat: position.coords.latitude,
                            lon: position.coords.longitude,
                        }),
                        (error) => resolve({
                            error: error.code === 1 ? 'denied' :
                                   error.code === 3 ? 'timeout' : 'unavailable',
                        }),
                        {
                            enableHighAccuracy: false,
                            timeout: 10000,
                            maximumAge: 60000,
                        },
                    );
                })
                """,
                timeout=15.0,
            )
        except TimeoutError:
            self._show_location_error(
                "Location request timed out. Try again or use the map."
            )
            return
        except (RuntimeError, ValueError):
            logger.warning("Browser location request failed", exc_info=True)
            self._show_location_error("Unable to request your current location.")
            return
        finally:
            self.current_location_button.enable()

        if not isinstance(result, dict):
            self._show_location_error("Unable to access your current location.")
            return
        if result.get("error"):
            messages = {
                "insecure": "Location access needs HTTPS or localhost.",
                "unsupported": "This browser does not support device location.",
                "denied": (
                    "Location permission denied. Search for a city or area "
                    "or tap the map instead."
                ),
                "timeout": "Location request timed out. Try again or use the map.",
                "unavailable": "Device location is unavailable. Try the map instead.",
            }

            message = messages.get(
                str(result["error"]), "Unable to access your current location."
            )
            self._show_location_error(message)
            return

        try:
            self._clear_search_text()
            self.search_feedback.set_text(
                "Browser location selected. Confirm the pin below."
            )
            self._set_pin(float(result["lat"]), float(result["lon"]))
        except (KeyError, TypeError, ValueError):
            ui.notify("The browser returned an invalid location.", type="warning")
            self.location_status.set_text("No location selected.")

    async def _confirm_location(self) -> None:
        """Look up the pin's place name and confirm it, even when the lookup fails."""
        if self._selected_point is None:
            return

        point = self._selected_point
        revision = self._pin_revision
        self.confirm_button.disable()
        self.location_status.set_text(
            f"Confirming pin near {point[0]:.2f}, {point[1]:.2f}..."
        )
        try:
            result = await reverse_geocode(*point)
        except _LOOKUP_ERRORS:
            logger.warning("Reverse geocoding failed", exc_info=True)
            if self._selected_point != point or self._pin_revision != revision:
                return
            self._confirmed_location = SelectedLocation(
                latitude=point[0], longitude=point[1]
            )
            self.location_status.set_text(
                "Pin confirmed. The place name could not be looked up, so the "
                "report will only include the approximate point."
            )
            ui.notify(
                "Coordinates confirmed. Place-name lookup is unavailable.",
                type="warning",
            )
        else:
            if self._selected_point != point or self._pin_revision != revision:
                return  # The pin moved while the lookup ran.
            self._confirmed_location = SelectedLocation(
                latitude=point[0],
                longitude=point[1],
                country=result["country"] or None,
                region=result["region"] or None,
                city=result["city"] or None,
            )
            self.location_status.set_text(
                f"Location confirmed: {result['location_name'] or 'approximate area'}."
            )
            ui.notify("Location confirmed.", type="positive")
        finally:
            if self._selected_point is not None:
                self.confirm_button.enable()
        self._notify_change()

    def _clear_location(self) -> None:
        """Remove the pin, the confirmation and any pending search."""
        self._selected_point = None
        self._pin_revision += 1
        self._confirmed_location = None
        self._clear_search_text()
        self.search_feedback.set_text(_SUGGESTION_HINT)
        self._cancel_pending_search()
        if self._marker is not None:
            self.map_view.remove_layer(self._marker)
            self._marker = None
        self.map_view.set_center(_DEFAULT_CENTER)
        self.map_view.set_zoom(_DEFAULT_ZOOM)
        self.location_status.set_text("No location selected.")
        self.location_status.classes(remove="crisis-location-status--error")
        self.confirm_button.disable()
        self.remove_button.disable()
        self._notify_change()

    def get_location(self) -> SelectedLocation | None:
        """The confirmed location, or None."""
        return self._confirmed_location

    def has_unconfirmed_pin(self) -> bool:
        """True when a pin is placed but not confirmed."""
        return self._selected_point is not None and self._confirmed_location is None

    def _show_location_error(self, message: str) -> None:
        """Show the error in the status line until the next action."""
        self.location_status.set_text(message)
        self.location_status.classes(add="crisis-location-status--error")
        ui.notify(message, type="warning")
