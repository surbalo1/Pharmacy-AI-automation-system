// dashboard/app.js - charts and data fetching

const API_BASE = '/api';

// init when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadStats();
    initCharts();
    loadOrders();
    updateTime();
});

// update time display
function updateTime() {
    const now = new Date();
    document.getElementById('update-time').textContent = now.toLocaleString();
}

// load stats from api
async function loadStats() {
    try {
        // in prod these would be real api calls
        // for now use mock data
        document.getElementById('rx-count').textContent = '47';
        document.getElementById('reminder-count').textContent = '23';
        document.getElementById('chat-count').textContent = '156';
        document.getElementById('call-count').textContent = '34';
    } catch (err) {
        console.error('failed to load stats:', err);
    }
}

// init charts
function initCharts() {
    // rx volume chart - line
    const rxCtx = document.getElementById('rx-chart').getContext('2d');
    new Chart(rxCtx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Prescriptions',
                data: [42, 38, 45, 51, 47, 28, 12],
                borderColor: '#4ecca3',
                backgroundColor: 'rgba(78, 204, 163, 0.1)',
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { 
                    beginAtZero: true,
                    grid: { color: '#333' },
                    ticks: { color: '#888' }
                },
                x: { 
                    grid: { display: false },
                    ticks: { color: '#888' }
                }
            }
        }
    });

    // compound categories - doughnut
    const catCtx = document.getElementById('category-chart').getContext('2d');
    new Chart(catCtx, {
        type: 'doughnut',
        data: {
            labels: ['Hormone', 'Pain', 'Dermal', 'Other'],
            datasets: [{
                data: [35, 25, 22, 18],
                backgroundColor: [
                    '#4ecca3',
                    '#f9a826',
                    '#3b82f6',
                    '#8b5cf6'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#888' }
                }
            }
        }
    });
}

// load open orders
async function loadOrders() {
    // mock data - replace with api call
    const orders = [
        { rx: 'RX123456', patient: 'J. Smith', med: 'Testosterone Cream', status: 'processing', days: 2 },
        { rx: 'RX123457', patient: 'M. Johnson', med: 'Progesterone Caps', status: 'ready', days: 1 },
        { rx: 'RX123458', patient: 'R. Williams', med: 'Pain Compound', status: 'pending', days: 4 },
        { rx: 'RX123459', patient: 'L. Brown', med: 'Estrogen Cream', status: 'processing', days: 1 },
    ];

    const tbody = document.getElementById('orders-body');
    tbody.innerHTML = '';

    orders.forEach(order => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${order.rx}</td>
            <td>${order.patient}</td>
            <td>${order.med}</td>
            <td class="status-${order.status}">${order.status}</td>
            <td>${order.days}</td>
        `;
        tbody.appendChild(row);
    });
}

// refresh data
function refresh() {
    loadStats();
    loadOrders();
    updateTime();
}

// auto refresh every 5 min
setInterval(refresh, 300000);
