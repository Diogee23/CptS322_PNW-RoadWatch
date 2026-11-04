// Autocomplete based on https://developers.google.com/maps/documentation/javascript/examples/place-autocomplete-element
async function init() {
    const { PlaceAutocompleteElement } = await google.maps.importLibrary("places");

    const startAutocomplete = new PlaceAutocompleteElement();
    document.getElementById("startLocationContainer").appendChild(startAutocomplete);

    const endAutocomplete = new PlaceAutocompleteElement();
    document.getElementById("destinationContainer").appendChild(endAutocomplete);

    // Remember the Place the user picked in each box
    let startPlace = null;
    let endPlace = null;

    const onSelect = (setter) => async ({ placePrediction }) => {
        const place = placePrediction.toPlace();
        await place.fetchFields({ fields: ["displayName", "formattedAddress", "location"] });
        setter(place);
    };
    startAutocomplete.addEventListener("gmp-select", onSelect((p) => { startPlace = p; }));
    endAutocomplete.addEventListener("gmp-select", onSelect((p) => { endPlace = p; }));

    // Directions
    const panel = document.getElementById("directionsPanel");
    const directions = new DirectionsController(window.roadwatchMap, panel);

    document.getElementById("getDirectionsBtn").addEventListener("click", () => {
        directions.showRoute(startPlace, endPlace);
    });
    document.getElementById("clearDirectionsBtn")?.addEventListener("click", () => directions.clear());
}

void init();