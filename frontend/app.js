let selectedLocationId = null;

async function showLocations() {
    const response = await fetch('/api/v1/locations');
    const locations = await response.json();

    document.getElementById('locations').innerHTML = locations.map((location) => `
        <article class="parking-card">
            <h3>${location.name}</h3>
            <p class="price">&#8377;${location.price}/hour</p>
            <p class="spots">Available spots: ${location.spots}</p>
            <button onclick="chooseLocation(${location.id}, '${location.name}')" ${location.spots === 0 ? 'disabled' : ''}>
                ${location.spots === 0 ? 'FULLY BOOKED' : 'BOOK'}
            </button>
        </article>
    `).join('');
}

function chooseLocation(locationId, locationName) {
    selectedLocationId = locationId;
    document.getElementById('selected-location').textContent = `Booking at ${locationName}`;
    document.getElementById('booking-section').classList.remove('hidden');
    document.getElementById('message').textContent = '';
    document.getElementById('name').focus();
}

document.getElementById('booking-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const response = await fetch(`/api/v1/locations/${selectedLocationId}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: document.getElementById('name').value,
            vehicle_number: document.getElementById('vehicle-number').value,
        }),
    });
    const result = await response.json();

    document.getElementById('message').textContent = response.ok
        ? `Spot booked! ${result.name}, your ${result.vehicle_number} is booked at ${result.location}.`
        : result.detail;

    if (response.ok) {
        document.getElementById('booking-form').reset();
        document.getElementById('booking-section').classList.add('hidden');
    }

    showLocations();
});

showLocations();
