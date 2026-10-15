//code for autocomplete from https://developers.google.com/maps/documentation/javascript/examples/place-autocomplete-element#maps_place_autocomplete_element-javascript
async function init() {
    // Request needed libraries.
    const { PlaceAutocompleteElement } =
        await google.maps.importLibrary('places');
    // Create the input HTML element for start location, and append it.
    const startAutocomplete = new PlaceAutocompleteElement();
    document.getElementById("startLocationContainer").appendChild(startAutocomplete);
    // Inject HTML UI.
    const startSelectedPlaceTitle = document.createElement('p');
    startSelectedPlaceTitle.textContent = '';
    document.getElementById("startLocationContainer").appendChild(startSelectedPlaceTitle);

    const startSelectedPlaceInfo = document.createElement('pre');
    startSelectedPlaceInfo.textContent = '';
    document.getElementById("startLocationContainer").appendChild(startSelectedPlaceInfo);

    //create input HTML element for end location
    const endAutocomplete = new PlaceAutocompleteElement();
    document.getElementById("destinationContainer").appendChild(endAutocomplete);
    // Inject HTML UI.
    const endSelectedPlaceTitle = document.createElement('p');
    endSelectedPlaceTitle.textContent = '';
    document.getElementById("destinationContainer").appendChild(endSelectedPlaceTitle);

    const endSelectedPlaceInfo = document.createElement('pre');
    endSelectedPlaceInfo.textContent = '';
    document.getElementById("destinationContainer").appendChild(endSelectedPlaceInfo);
    
    // Add the gmp-select listener, and display the results.
    // placeAutocomplete.addEventListener(
    //     'gmp-select',
    //     async ({ placePrediction }) => {
    //         const place = placePrediction.toPlace();
    //         await place.fetchFields({
    //             fields: ['displayName', 'formattedAddress', 'location'],
    //         });
    //         selectedPlaceTitle.textContent = 'Selected Place:';
    //         selectedPlaceInfo.textContent = JSON.stringify(
    //             place.toJSON(),
    //             /* replacer */ null,
    //             /* space */ 2
    //         );
    //     }
    // );
}

void init();