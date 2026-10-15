let selectedLocationId = null;
let selectedSpotNumber = null;
let allLocations = [];

const currency = (amount) => `₹${amount}`;
const formatTime = (iso) => new Date(iso).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });

function renderStars(rating) {
    const full = Math.round(rating);
    return '★'.repeat(full) + '☆'.repeat(5 - full);
}

// datetime-local works in the user's local time with no timezone, so build the
// value by hand. Starts at the next quarter hour.
function setDefaultWindowStart() {
    const start = new Date();
    start.setMinutes(Math.ceil((start.getMinutes() + 1) / 15) * 15, 0, 0);
    const pad = (n) => String(n).padStart(2, '0');
    document.getElementById('window-start').value =
        `${start.getFullYear()}-${pad(start.getMonth() + 1)}-${pad(start.getDate())}T${pad(start.getHours())}:${pad(start.getMinutes())}`;
}

// The chosen window as UTC ISO strings (toISOString always ends in "Z"),
// which the API needs because it rejects times without a timezone.
function selectedWindow() {
    const start = new Date(document.getElementById('window-start').value);
    const hours = Number(document.getElementById('window-hours').value);
    const end = new Date(start.getTime() + hours * 60 * 60 * 1000);
    return { start: start.toISOString(), end: end.toISOString(), hours };
}

async function loadStats() {
    const response = await fetch('/api/v1/stats');
    const stats = await response.json();

    document.getElementById('stats').innerHTML = `
        <div class="stat-tile"><span class="stat-value">${stats.locations}</span><span class="stat-label">Locations</span></div>
        <div class="stat-tile"><span class="stat-value">${stats.available_spots}</span><span class="stat-label">Free right now</span></div>
        <div class="stat-tile"><span class="stat-value">${stats.booked_spots}</span><span class="stat-label">Occupied now</span></div>
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
            <span class="activity-time">${new Date(item.at).toLocaleTimeString([], { timeStyle: 'short' })}</span>
        </li>
    `).join('');
}

function renderLocations() {
    const query = document.getElementById('search').value.trim().toLowerCase();
    const sortBy = document.getElementById('sort').value;
    const { hours } = selectedWindow();

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
            <p class="price">${currency(location.price)}/hour · ${currency(Math.ceil(location.price * hours))} for your time</p>
            <p class="spots">Free for your time: ${location.spots} / ${location.total_spots}</p>
            <div class="availability-bar"><div class="availability-fill" style="width:${occupancy}%"></div></div>
            <p class="spot-label">Tap a spot to see its bookings or book it</p>
            <div class="spot-grid">
                ${location.spot_numbers.map((spotNumber) => {
                    const isBooked = location.booked_spots.includes(spotNumber);
                    return `<button class="spot-button ${isBooked ? 'booked' : ''}"
                        onclick="chooseSpot(${location.id}, '${location.name}', '${spotNumber}')">
                        ${spotNumber}
                    </button>`;
                }).join('')}
            </div>
        </article>
    `;
    }).join('');
}

async function loadLocations() {
    const { start, end } = selectedWindow();
    const params = new URLSearchParams({ start, end });
    const response = await fetch(`/api/v1/locations?${params}`);
    allLocations = await response.json();
    renderLocations();
}

async function refreshAll() {
    await loadLocations();
    loadStats();
    loadActivity();
    if (selectedSpotNumber) loadSchedule();
}

async function loadSchedule() {
    const response = await fetch(`/api/v1/locations/${selectedLocationId}/spots/${selectedSpotNumber}/bookings`);
    const bookings = await response.json();
    const list = document.getElementById('spot-schedule');

    list.innerHTML = bookings.length === 0
        ? '<li class="activity-empty">No upcoming bookings. This spot is wide open.</li>'
        : bookings.map((booking) => `
            <li class="schedule-item">
                <span>${formatTime(booking.start_time)} → ${formatTime(booking.end_time)}</span>
                <button type="button" class="link-button" onclick="cancelBooking(${booking.booking_id})">Cancel</button>
            </li>
        `).join('');
}

function chooseSpot(locationId, locationName, spotNumber) {
    selectedLocationId = locationId;
    selectedSpotNumber = spotNumber;
    const { start, end } = selectedWindow();
    document.getElementById('selected-location').textContent =
        `${spotNumber} at ${locationName}, ${formatTime(start)} → ${formatTime(end)}`;
    document.getElementById('booking-section').classList.remove('hidden');
    document.getElementById('booking-section').scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('message').textContent = '';
    loadSchedule();
    document.getElementById('name').focus();
}

async function cancelBooking(bookingId) {
    if (!confirm('Cancel this booking?')) return;

    const response = await fetch(`/api/v1/bookings/${bookingId}`, { method: 'DELETE' });
    const result = await response.json();
    showMessage(response.ok ? `Booking for spot ${result.spot_number} cancelled.` : result.detail, response.ok);
    refreshAll();
}

function showMessage(text, ok) {
    const message = document.getElementById('message');
    message.textContent = text;
    message.classList.toggle('message-error', !ok);
}

// FastAPI validation errors (422) return a list of problems instead of a string.
const errorText = (detail) => Array.isArray(detail) ? detail.map((e) => e.msg.replace('Value error, ', '')).join('; ') : detail;

document.getElementById('booking-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const { start, end } = selectedWindow();

    const response = await fetch(`/api/v1/locations/${selectedLocationId}/book`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: document.getElementById('name').value,
            vehicle_number: document.getElementById('vehicle-number').value,
            spot_number: selectedSpotNumber,
            start_time: start,
            end_time: end,
        }),
    });
    const result = await response.json();

    showMessage(response.ok
        ? `Spot ${result.spot_number} booked at ${result.location} for ${result.vehicle_number}, ` +
          `${formatTime(result.start_time)} → ${formatTime(result.end_time)}. Total ${currency(result.total_price)}.`
        : errorText(result.detail), response.ok);

    if (response.ok) {
        document.getElementById('booking-form').reset();
        document.getElementById('booking-section').classList.add('hidden');
        selectedSpotNumber = null;
    }

    refreshAll();
});

document.getElementById('search').addEventListener('input', renderLocations);
document.getElementById('sort').addEventListener('change', renderLocations);
document.getElementById('window-start').addEventListener('change', loadLocations);
document.getElementById('window-hours').addEventListener('change', loadLocations);

setDefaultWindowStart();
refreshAll();
setInterval(loadActivity, 8000);
