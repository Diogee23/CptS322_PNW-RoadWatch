// Autocomplete based on https://developers.google.com/maps/documentation/javascript/examples/place-autocomplete-element
async function init() {
    const { PlaceAutocompleteElement } = await google.maps.importLibrary("places");

    // The Place the user picked in each box
    let startPlace = null;
    let endPlace = null;

    // Build a fresh autocomplete box inside a container. Calling this again
    // replaces the old box, which is how we empty it.
    function createAutocomplete(containerId, setPlace) {
        const container = document.getElementById(containerId);
        container.replaceChildren();

        const autocomplete = new PlaceAutocompleteElement();
        autocomplete.addEventListener("gmp-select", async ({ placePrediction }) => {
            const place = placePrediction.toPlace();
            await place.fetchFields({ fields: ["displayName", "formattedAddress", "location", "addressComponents"] });
            setPlace(place);
        });
        container.appendChild(autocomplete);
    }

    const setStart = (p) => { startPlace = p; };
    const setEnd = (p) => { endPlace = p; };

    createAutocomplete("startLocationContainer", setStart);
    createAutocomplete("destinationContainer", setEnd);

    // Directions
    const panel = document.getElementById("directionsPanel");
    const directions = new DirectionsController(window.roadwatchMap, panel);

    document.getElementById("getDirectionsBtn").addEventListener("click", () => {
        directions.showRoute(startPlace, endPlace);
    });

    document.getElementById("clearDirectionsBtn")?.addEventListener("click", () => {
        directions.clear();   // route, highlighted step and panel
        startPlace = null;    // forget the old places so Get Route can't reuse them
        endPlace = null;
        createAutocomplete("startLocationContainer", setStart);   // empty the boxes
        createAutocomplete("destinationContainer", setEnd);
    });
}

void init();