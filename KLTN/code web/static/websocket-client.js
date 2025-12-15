// websocket-client.js
// Khởi tạo WebSocket
let wsClient = null;
let wsReconnectAttempts = 0;
const wsMaxReconnectAttempts = 5;
const wsReconnectDelay = 5000;
let wsReconnectTimeout = null;
let lastData = null;

function isDataEqual(data1, data2) {
    if (!data1 || !data2) return false;
    try {
        return (
            Math.abs(data1.temperature - data2.temperature) < 0.1 &&
            Math.abs(data1.humidity - data2.humidity) < 0.1 &&
            data1.nitrogen === data2.nitrogen &&
            data1.phosphorus === data2.phosphorus &&
            data1.potassium === data2.potassium &&
            Math.abs(data1.ph - data2.ph) < 0.1 &&
            Math.abs(data1.rainfall - data2.rainfall) < 0.1 &&
            Math.abs(data1.monthly_rainfall - data2.monthly_rainfall) < 0.1
        );
    } catch (error) {
        console.error('Error comparing data:', error);
        return false;
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Hàm lấy URL WebSocket động
function getWebSocketUrl() {
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
    const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsHost = window.location.host;
    return isLocal ? `${wsProtocol}://localhost:8000/ws` : `${wsProtocol}://${wsHost}/ws`;
}

function connectWebSocket() {
    try {
        if (wsReconnectTimeout) {
            clearTimeout(wsReconnectTimeout);
            wsReconnectTimeout = null;
        }
        if (wsClient) {
            wsClient.close();
            wsClient = null;
        }
        wsClient = new WebSocket(getWebSocketUrl());

        wsClient.onopen = () => {
            console.log('Connected to WebSocket server');
            wsReconnectAttempts = 0;
        };

        wsClient.onclose = (event) => {
            console.log('WebSocket connection closed:', event.code, event.reason);
            if (wsReconnectAttempts < wsMaxReconnectAttempts) {
                wsReconnectAttempts++;
                console.log(`Attempting to reconnect (${wsReconnectAttempts}/${wsMaxReconnectAttempts})...`);
                wsReconnectTimeout = setTimeout(connectWebSocket, wsReconnectDelay);
            } else {
                console.error('Max reconnection attempts reached');
                showConnectionError();
            }
        };

        wsClient.onerror = (error) => {
            console.error('WebSocket Error:', error);
        };

        wsClient.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            } catch (error) {
                console.error('Error processing WebSocket message:', error);
                showErrorNotification('Lỗi khi xử lý dữ liệu từ server');
            }
        };
    } catch (error) {
        console.error('Error creating WebSocket:', error);
        if (wsReconnectAttempts < wsMaxReconnectAttempts) {
            wsReconnectTimeout = setTimeout(connectWebSocket, wsReconnectDelay);
        }
    }
}

// Xử lý tin nhắn từ WebSocket
function handleWebSocketMessage(data) {
    try {
        if (data.latest && !isDataEqual(data.latest, lastData)) {
            console.log('New sensor data:', data.latest);
            lastData = {...data.latest};
            if (typeof updateSensorDisplay === 'function') {
                debouncedUpdateSensorDisplay(data.latest);
            }
            if (typeof updateNotifications === 'function') {
                updateNotifications(data.latest);
            }
        }

        if (data.history && Array.isArray(data.history)) {
            if (typeof isHistoryTimeFiltered === 'undefined' || !isHistoryTimeFiltered) {
                updateHistoryTable(data.history);
            }
        }

        if (data.forecast_5days && Array.isArray(data.forecast_5days)) {
            console.log('Debug - Received forecast data:', data.forecast_5days);
            if (typeof updateForecastDisplay === 'function') {
                updateForecastDisplay(data.forecast_5days);
            }
        }
    } catch (error) {
        console.error('Error handling WebSocket message:', error);
        showErrorNotification('Lỗi khi xử lý dữ liệu từ server');
    }
}

// Hiển thị thông báo lỗi kết nối
function showConnectionError() {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded shadow-lg z-50';
    errorDiv.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-circle mr-2"></i>
            <span>Mất kết nối với máy chủ. Đang thử kết nối lại...</span>
            <button id="reconnect-btn" class="ml-4 bg-white text-red-500 px-2 py-1 rounded">Thử lại</button>
        </div>
    `;
    document.body.appendChild(errorDiv);

    document.getElementById('reconnect-btn').addEventListener('click', () => {
        wsReconnectAttempts = 0;
        connectWebSocket();
        errorDiv.remove();
    });

    setTimeout(() => errorDiv.remove(), 10000);
}

// Hiển thị thông báo lỗi chung
function showErrorNotification(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'fixed top-4 right-4 bg-red-500 text-white px-6 py-3 rounded shadow-lg z-50';
    errorDiv.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-exclamation-circle mr-2"></i>
            <span>${message}</span>
        </div>
    `;
    document.body.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

// Kết nối khi trang được tải
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
});

// Khôi phục kết nối
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        if (!wsClient || wsClient.readyState !== WebSocket.OPEN) {
            wsReconnectAttempts = 0;
            connectWebSocket();
        }
    }
});

// Cập nhật hiển thị cảm biến
function updateSensorDisplay(data) {
    if (!data || typeof data !== 'object') {
        console.error('Invalid sensor data:', data);
        return;
    }

    try {
        const savedData = localStorage.getItem('plantSelectionData');
        let idealParams = null;
        if (savedData) {
            const plantData = JSON.parse(savedData);
            idealParams = plantData?.parameters?.ideal;
            console.log('Ideal parameters:', idealParams);
        }

        function isOutOfRange(value, paramName) {
            if (!idealParams || !idealParams[paramName] || isNaN(value)) return false;
            const range = idealParams[paramName];
            if (range.min !== undefined && range.max !== undefined) {
                return value < range.min || value > range.max;
            }
            const idealValue = parseFloat(range);
            const tolerance = idealValue * 0.1;
            return Math.abs(value - idealValue) > tolerance;
        }

        function updateValueWithWarning(elementId, value, paramName, unit = '') {
            const element = document.getElementById(elementId);
            if (!element || isNaN(value)) return;
            let displayValue = value.toFixed(1);
            let warningIcon = idealParams && isOutOfRange(value, paramName)
                ? '<i class="fas fa-exclamation-triangle text-yellow-500 ml-2" title="Giá trị nằm ngoài khoảng phù hợp"></i>'
                : '';
            element.innerHTML = `${displayValue}${unit}${warningIcon}`;
            console.log(`Updated ${paramName}:`, element.innerHTML);
        }

        updateValueWithWarning('temperature', data.temperature, 'temperature', ' °C');
        updateValueWithWarning('humidity', data.humidity, 'humidity', ' %');
        updateValueWithWarning('ph', data.ph, 'ph', '');
        updateValueWithWarning('nitrogen', data.nitrogen, 'nitrogen', ' mg/kg');
        updateValueWithWarning('phosphorus', data.phosphorus, 'phosphorus', ' mg/kg');
        updateValueWithWarning('potassium', data.potassium, 'potassium', ' mg/kg');

        const rainfallElement = document.getElementById('rainfall');
        if (rainfallElement && data.rainfall !== undefined && !isNaN(data.rainfall)) {
            rainfallElement.textContent = `${data.rainfall.toFixed(2)} mm`;
            console.log('Updated rainfall:', data.rainfall);
        }

        const monthlyRainfallElement = document.getElementById('monthly_rainfall');
        if (monthlyRainfallElement && data.monthly_rainfall !== undefined && !isNaN(data.monthly_rainfall)) {
            monthlyRainfallElement.textContent = `${data.monthly_rainfall.toFixed(2)} mm`;
            console.log('Updated monthly rainfall:', data.monthly_rainfall);
        }
    } catch (error) {
        console.error('Error updating sensor display:', error);
        showErrorNotification('Lỗi khi cập nhật dữ liệu cảm biến');
    }
}

// Điền nhanh dữ liệu cho form khuyến nghị
async function quickFillPredictionForm() {
    try {
        const baseUrl = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://localhost:8000'
            : `${window.location.protocol}//${window.location.host}`;
        const response = await fetch(`${baseUrl}/quick-fill`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error getting quick fill data:', data.error);
            showErrorNotification('Không thể lấy dữ liệu điền nhanh: ' + data.error);
            return;
        }
        
        const temperatureInput = document.getElementById('temperature-input');
        const humidityInput = document.getElementById('humidity-input');
        const rainfallInput = document.getElementById('rainfall-input');
        const nitrogenInput = document.getElementById('nitrogen-input');
        const phosphorusInput = document.getElementById('phosphorus-input');
        const potassiumInput = document.getElementById('potassium-input');
        const phInput = document.getElementById('ph-input');
        
        if (temperatureInput) temperatureInput.value = data.temperature.toFixed(2);
        if (humidityInput) humidityInput.value = data.humidity.toFixed(2);
        if (rainfallInput) rainfallInput.value = data.monthly_rainfall.toFixed(2);
        if (nitrogenInput) nitrogenInput.value = data.nitrogen.toFixed(2);
        if (phosphorusInput) phosphorusInput.value = data.phosphorus.toFixed(2);
        if (potassiumInput) potassiumInput.value = data.potassium.toFixed(2);
        if (phInput) phInput.value = data.ph.toFixed(2);
        
        console.log('Quick fill data:', data);
    } catch (error) {
        console.error('Error in quick fill:', error);
        showErrorNotification('Lỗi khi lấy dữ liệu điền nhanh');
    }
}

const debouncedUpdateSensorDisplay = debounce(updateSensorDisplay, 1000);

function updateHistoryTable(data) {
    const tbody = document.getElementById('history-table');
    if (!tbody) {
        return;
    }
    if (!Array.isArray(data)) {
        console.error('Invalid history data:', data);
        return;
    }

    tbody.innerHTML = '';
    const sortedData = [...data].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    sortedData.forEach(item => {
        const timestamp = new Date(item.timestamp);
        if (isNaN(timestamp.getTime())) return;

        const hours = timestamp.getHours().toString().padStart(2, '0');
        const minutes = timestamp.getMinutes().toString().padStart(2, '0');
        const day = timestamp.getDate().toString().padStart(2, '0');
        const month = (timestamp.getMonth() + 1).toString().padStart(2, '0');
        const formattedDateTime = `${hours}:${minutes}(${day}/${month})`;

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${formattedDateTime}</td>
            <td>${isNaN(item.temperature) ? 'N/A' : Number(item.temperature).toFixed(2)}</td>
            <td>${isNaN(item.humidity) ? 'N/A' : Number(item.humidity).toFixed(2)}</td>
            <td>${isNaN(item.rainfall) ? 'N/A' : Number(item.rainfall).toFixed(2)}</td>
            <td>${isNaN(item.nitrogen) ? 'N/A' : Number(item.nitrogen).toFixed(2)}</td>
            <td>${isNaN(item.phosphorus) ? 'N/A' : Number(item.phosphorus).toFixed(2)}</td>
            <td>${isNaN(item.potassium) ? 'N/A' : Number(item.potassium).toFixed(2)}</td>
            <td>${isNaN(item.ph) ? 'N/A' : Number(item.ph).toFixed(2)}</td>
        `;
        tbody.appendChild(row);
    });

    console.log('History table updated with', data.length, 'rows');
}