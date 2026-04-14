document.addEventListener('DOMContentLoaded', () => {
    
    // --- Elements ---
    const toggleTatkalBtn = document.getElementById('toggle-tatkal-btn');
    const seatsAvailableEl = document.getElementById('seats-available');
    const coachLayoutEl = document.getElementById('coach-layout');
    const activeListEl = document.getElementById('active-list');
    const waitingListEl = document.getElementById('waiting-list');
    const logListEl = document.getElementById('log-list');
    
    const bookingForm = document.getElementById('booking-form');
    const cancelForm = document.getElementById('cancel-form');
    const addPassengerBtn = document.getElementById('add-passenger-btn');
    const passengersContainer = document.getElementById('passengers-container');

    let passengerCount = 1;

    // --- State Management ---
    async function fetchState() {
        try {
            const res = await fetch('/api/state');
            const data = await res.json();
            renderState(data);
        } catch (e) {
            console.error("Failed to fetch state", e);
        }
    }

    function renderState(state) {
        // Stats header
        seatsAvailableEl.textContent = state.available_seat_count;
        if (state.tatkal_open) {
            toggleTatkalBtn.textContent = 'Tatkal: OPEN';
            toggleTatkalBtn.classList.add('open');
        } else {
            toggleTatkalBtn.textContent = 'Tatkal: CLOSED';
            toggleTatkalBtn.classList.remove('open');
        }

        // Coach Layout
        coachLayoutEl.innerHTML = '';
        if (state.seats.length === 0) {
            coachLayoutEl.innerHTML = '<p style="color:var(--text-muted); grid-column: 1/-1;">No seats dynamically allocated yet. Available unassigned: ' + state.available_seats.join(', ') + '</p>';
        }

        state.seats.forEach(node => {
            if (node.status === 'Available' && node.occupants.length === 0) return; // Hide strictly Empty nodes if preferred, but usually we show them
            
            let statusClass = 'status-avail';
            let statusText = 'Available';
            if (node.status.includes('Confirmed')) { statusClass = 'status-conf'; statusText = 'Confirmed'; }
            else if (node.status.includes('RAC')) { statusClass = 'status-rac'; statusText = 'RAC Shared'; }

            const card = document.createElement('div');
            card.className = 'seat-card';
            
            let occHtml = node.occupants.map(p => `<span>${p.name}</span>`).join('');

            card.innerHTML = `
                <div class="seat-number">${node.seat_number}</div>
                <div class="seat-status ${statusClass}">${statusText}</div>
                <div class="occupants">${occHtml || '-'}</div>
            `;
            coachLayoutEl.appendChild(card);
        });

        // Active List
        activeListEl.innerHTML = state.active_passengers.map(p => `
            <li>
                <div><strong>${p.name}</strong> (${p.gender === 'Male' ? 'M' : 'F'})</div>
                <div style="text-align: right;">
                    <span class="pnr">PNR: ${p.pnr}</span><br>
                    <span>Seat: ${p.seat_number}</span>
                </div>
            </li>
        `).join('');

        // Wait List
        waitingListEl.innerHTML = state.waiting_list.map(p => `
            <li>
                <div><strong>${p.name}</strong> (${p.type})</div>
                <div style="text-align: right;">
                    <span class="pnr">PNR: ${p.pnr}</span><br>
                    <span style="font-size:0.8rem">${p.prefers_rac ? 'RAC OK' : 'Only Full'}</span>
                </div>
            </li>
        `).join('');
    }

    function addLog(logMsgs) {
        if (!logMsgs || logMsgs.length === 0) return;
        logMsgs.forEach(msg => {
            const li = document.createElement('li');
            li.textContent = `> ${msg}`;
            logListEl.prepend(li); // add to top
        });
    }

    // --- Actions ---

    toggleTatkalBtn.addEventListener('click', async () => {
        const res = await fetch('/api/tatkal/toggle', { method: 'POST' });
        if (res.ok) fetchState();
    });

    addPassengerBtn.addEventListener('click', () => {
        passengerCount++;
        const div = document.createElement('div');
        div.className = 'passenger-entry';
        div.style.marginTop = '1rem';
        div.style.borderTop = '1px solid rgba(255,255,255,0.1)';
        div.style.paddingTop = '1rem';
        div.innerHTML = `
            <h3>Passenger ${passengerCount}</h3>
            <div class="input-row">
                <input type="text" class="p-name" placeholder="Name" required>
                <select class="p-gender">
                    <option value="M">Male</option>
                    <option value="F">Female</option>
                </select>
            </div>
            <div class="checkbox-group">
                <input type="checkbox" class="p-rac">
                <label>Accept RAC Sharing</label>
            </div>
        `;
        passengersContainer.appendChild(div);
    });

    bookingForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const type = document.getElementById('ticket-type').value;
        const entries = document.querySelectorAll('.passenger-entry');
        
        const passengers = Array.from(entries).map(entry => {
            return {
                name: entry.querySelector('.p-name').value,
                gender: entry.querySelector('.p-gender').value,
                prefers_rac: entry.querySelector('.p-rac').checked
            };
        });

        try {
            const res = await fetch('/api/book', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ticket_type: type, passengers })
            });
            const data = await res.json();
            
            if (data.success) {
                addLog(data.logs);
                renderState(data.state);
                bookingForm.reset();
                // Reset passengers count
                passengersContainer.innerHTML = `
                    <div class="passenger-entry">
                        <h3>Passenger 1</h3>
                        <div class="input-row">
                            <input type="text" class="p-name" placeholder="Name" required>
                            <select class="p-gender">
                                <option value="M">Male</option>
                                <option value="F">Female</option>
                            </select>
                        </div>
                        <div class="checkbox-group">
                            <input type="checkbox" class="p-rac">
                            <label>Accept RAC Sharing</label>
                        </div>
                    </div>
                `;
                passengerCount = 1;
            } else {
                alert(data.error || 'Booking Failed');
            }
        } catch(e) {
            console.error(e);
        }
    });

    cancelForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('cancel-name').value;
        try {
            const res = await fetch('/api/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name })
            });
            const data = await res.json();
            if (data.success) {
                addLog(data.logs);
                renderState(data.state);
                cancelForm.reset();
            } else {
                alert(data.error);
            }
        } catch(e) {
            console.error(e);
        }
    });

    // Initial Load
    fetchState();
});
