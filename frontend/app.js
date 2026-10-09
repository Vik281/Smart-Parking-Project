let selectedLocationId = null;
let selectedSpotNumber = null;
let allLocations = [];

const currency = (amount) => `₹${amount}`;

function renderStars(rating) {
    const full = Math.round(rating);
    return '★'.repeat(full) + '☆'.repeat(5 - full);
}

async function loadStats() {
    const response = await fetch('/api/v1/stats');
    const stats = await response.json();

    document.getElementById('stats').innerHTML = `
        <div class="stat-tile"><span class="stat-value">${stats.locations}</span><span class="stat-label">Locations</span></div>
        <div class="stat-tile"><span class="stat-value">${stats.available_spots}</span><span class="stat-label">Spots free</span></div>
        <div class="stat-tile"><span class="stat-value">${stats.booked_spots}</span><span class="stat-label">Spots booked</span></div>
        <div class="stat-tile"><span class="stat-value">${currency(stats.avg_price)}</span><span class="stat-label">Avg price/hr</span></div>
    `;
}

async function loadActivity() {
    const response = await fetch('/api/v1/activity');
    const activity = await response.json();
    const feed = document.getElementById('activity-feed');

    if (activity.length === 0) {
        feed.innerHTML = '<li class="activity-empty">No activity yet. Book a spot to see it appear here.</li>';
        return;
    }

    feed.innerHTML = activity.map((item) => `
        <li class="activity-item activity-${item.type}">
            <span class="activity-dot"></span>
            <span class="activity-text">
                Spot <strong>${item.spot_number}</strong> at <strong>${item.location}</strong>
                was ${item.type === 'booked' ? 'booked' : 'cancelled'}
            </span>
            <span class="activity-time">${item.at.split('T')[1] || item.at}</span>
        </li>
    `).join('');
}

function renderLocations() {
    const query = document.getElementById('search').value.trim().toLowerCase();
    const sortBy = document.getElementById('sort').value;

    let locations = allLocations.filter((location) =>
        location.name.toLowerCase().includes(query) || location.address.toLowerCase().includes(query)
    );

    const sorters = {
        'price-asc': (a, b) => a.price - b.price,
        'price-desc': (a, b) => b.price - a.price,
        availability: (a, b) => b.spots - a.spots,
        rating: (a, b) => b.rating - a.rating,
    };
    if (sorters[sortBy]) {
        locations = [...locations].sort(sorters[sortBy]);
    }

    document.getElementById('no-results').classList.toggle('hidden', locations.length !== 0);

    document.getElementById('locations').innerHTML = locations.map((location) => {
        const occupancy = Math.round(((location.total_spots - location.spots) / location.total_spots) * 100);
        return `
        <article class="parking-card">
            <div class="card-top">
                <h3>${location.name}</h3>
                <span class="rating" title="${location.rating} out of 5">${renderStars(location.rating)}</span>
            </div>
            <p class="address">${location.address}</p>
            <div class="amenities">
                ${location.amenities.map((item) => `<span class="badge">${item}</span>`).join('')}
            </div>
            <p class="price">${currency(location.price)}/hour</p>
            <p class="spots">Available spots: ${location.spots} / ${location.total_spots}</p>
            <div class="availability-bar"><div class="availability-fill" style="width:${occupancy}%"></div></div>
            <p class="spot-label">Tap an open spot to book, or a booked spot to cancel</p>
            <div class="spot-grid">
                ${location.spot_numbers.map((spotNumber) => {
                    const isBooked = location.booked_spots.includes(spotNumber);
                    return `<button class="spot-button ${isBooked ? 'booked' : ''}"
                        onclick="${isBooked
                            ? `cancelSpot(${location.id}, '${spotNumber}')`
                            : `chooseLocation(${location.id}, '${location.name}', '${spotNumber}')`}">
                        ${isBooked ? `${spotNumber} ✕` : spotNumber}
                    </button>`;
                }).join('')}
            </div>
        </article>
    `;
    }).join('');
}

async function refreshAll() {
    const response = await fetch('/api/v1/locations');
    allLocations = await response.json();
    renderLocations();
    loadStats();
    loadActivity();
}

function chooseLocation(locationId, locationName, spotNumber) {
    selectedLocationId = locationId;
    selectedSpotNumber = spotNumber;
    document.getElementById('selected-location').textContent = `Booking ${spotNumber} at ${locationName}`;
    document.getElementById('booking-section').classList.remove('hidden');
    document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('message').textContent = '';
    document.getElementById('name').focus();
}

async function cancelSpot(locationId, spotNumber) {
    if (!confirm(`Cancel booking for spot ${spotNumber}?`)) return;

    const response = await fetch(`/api/v1/locations/${locationId}/book/${spotNumber}`, { method: 'DELETE' });
    const result = await response.json();

    const message = document.getElementById('message');
    message.textContent = response.ok ? `Spot ${result.spot_number} is free again.` : result.detail;
    message.classList.toggle('message-error', !response.ok);

    refreshAll();
}

document.getElementById('booking-form').addEventListener('submit', async (event) => {
    event.preventDefault();

    const response = await fetch(`/api/v1/locations/${selectedLocationId}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: document.getElementById('name').value,
            vehicle_number: document.getElementById('vehicle-number').value,
            spot_number: selectedSpotNumber,
        }),
    });
    const result = await response.json();

    const message = document.getElementById('message');
    message.textContent = response.ok
        ? `Spot ${result.spot_number} booked! ${result.name}, your ${result.vehicle_number} is booked at ${result.location}.`
        : result.detail;
    message.classList.toggle('message-error', !response.ok);

    if (response.ok) {
        document.getElementById('booking-form').reset();
        document.getElementById('booking-section').classList.add('hidden');
    }

    refreshAll();
});

document.getElementById('search').addEventListener('input', renderLocations);
document.getElementById('sort').addEventListener('change', renderLocations);

refreshAll();
setInterval(loadActivity, 8000);
