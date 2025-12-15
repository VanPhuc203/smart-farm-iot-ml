// common.js
let charts = {
    temperature: null,
    humidity: null,
    rainfall: null,
    nitrogen: null,
    phosphorus: null,
    potassium: null,
    ph: null
};

const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
        legend: {
            display: true,
            position: 'top'
        }
    },
    layout: {
        padding: {
            left: 10,
            right: 10,
            top: 0,
            bottom: 30
        }
    },
    scales: {
        x: {
            grid: {
                display: true,
                drawOnChartArea: true,
                color: 'rgba(0, 0, 0, 0.1)'
            },
            ticks: {
                maxRotation: window.innerWidth <= 768 ? 45 : 0, 
                minRotation: window.innerWidth <= 768 ? 45 : 0, 
                autoSkip: false,
                padding: 15,
                font: {
                    size: 10
                }
            }
        },
        y: {
            grid: {
                display: true,
                drawOnChartArea: true,
                color: 'rgba(0, 0, 0, 0.1)'
            },
            beginAtZero: true
        }
    }
};

const chartConfigs = {
    temperature: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 50,
                ticks: {
                    stepSize: 5
                }
            }
        }
    },
    humidity: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 100,
                ticks: {
                    stepSize: 10
                }
            }
        }
    },
    rainfall: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 1,
                ticks: {
                    stepSize: 0.1
                }
            }
        }
    },
    nitrogen: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 300,
                ticks: {
                    stepSize: 25
                }
            }
        }
    },
    phosphorus: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 300,
                ticks: {
                    stepSize: 25
                }
            }
        }
    },
    potassium: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 300,
                ticks: {
                    stepSize: 25
                }
            }
        }
    },
    ph: {
        ...commonOptions,
        scales: {
            ...commonOptions.scales,
            y: {
                ...commonOptions.scales.y,
                min: 0,
                max: 14,
                ticks: {
                    stepSize: 1
                }
            }
        }
    }
};

let lastUpdateTime = 0;
let lastHistoryTimestamp = null;
const UPDATE_INTERVAL = 300000;

function shouldUpdate(timestamp) {
    const currentTime = Date.now();
    if (currentTime - lastUpdateTime < UPDATE_INTERVAL) {
        console.log('Skipping update - too soon since last update');
        return false;
    }
    lastUpdateTime = currentTime;
    return true;
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
// Hàm khởi tạo biểu đồ
function initializeCharts() {
    if (!document.getElementById('temperatureChart')) {
        console.warn('No chart canvas found on this page.');
        return;
    }
    console.log('Initializing charts...');
    // Hủy các biểu đồ cũ
    if (charts.temperature) {
        charts.temperature.destroy();
        charts.temperature = null;
    }
    if (charts.humidity) {
        charts.humidity.destroy();
        charts.humidity = null;
    }
    if (charts.rainfall) {
        charts.rainfall.destroy();
        charts.rainfall = null;
    }
    if (charts.nitrogen) {
        charts.nitrogen.destroy();
        charts.nitrogen = null;
    }
    if (charts.phosphorus) {
        charts.phosphorus.destroy();
        charts.phosphorus = null;
    }
    if (charts.potassium) {
        charts.potassium.destroy();
        charts.potassium = null;
    }
    if (charts.ph) {
        charts.ph.destroy();
        charts.ph = null;
    }
    Chart.defaults.scale.grid.drawOnChartArea = true;
    Chart.defaults.scale.grid.color = 'rgba(0, 0, 0, 0.1)';
    // Biểu đồ nhiệt độ
    const temperatureCtx = document.getElementById('temperatureChart').getContext('2d');
    charts.temperature = new Chart(temperatureCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Nhiệt độ (°C)',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(255, 99, 132)'
            }]
        },
        options: {
            ...chartConfigs.temperature,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ độ ẩm
    const humidityCtx = document.getElementById('humidityChart').getContext('2d');
    charts.humidity = new Chart(humidityCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Độ ẩm (%)',
                data: [],
                borderColor: 'rgb(54, 162, 235)',
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(54, 162, 235)'
            }]
        },
        options: {
            ...chartConfigs.humidity,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ lượng mưa
    const rainfallCtx = document.getElementById('rainfallChart').getContext('2d');
    charts.rainfall = new Chart(rainfallCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Lượng mưa (mm)',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(75, 192, 192)'
            }]
        },
        options: {
            ...chartConfigs.rainfall,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ Nitrogen
    const nitrogenCtx = document.getElementById('nitrogenChart').getContext('2d');
    charts.nitrogen = new Chart(nitrogenCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Nitrogen (mg/kg)',
                data: [],
                borderColor: 'rgb(153, 102, 255)',
                backgroundColor: 'rgba(153, 102, 255, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(153, 102, 255)'
            }]
        },
        options: {
            ...chartConfigs.nitrogen,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ Phosphorus
    const phosphorusCtx = document.getElementById('phosphorusChart').getContext('2d');
    charts.phosphorus = new Chart(phosphorusCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Phosphorus (mg/kg)',
                data: [],
                borderColor: 'rgb(255, 159, 64)',
                backgroundColor: 'rgba(255, 159, 64, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(255, 159, 64)'
            }]
        },
        options: {
            ...chartConfigs.phosphorus,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ Potassium
    const potassiumCtx = document.getElementById('potassiumChart').getContext('2d');
    charts.potassium = new Chart(potassiumCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Potassium (mg/kg)',
                data: [],
                borderColor: 'rgb(255, 205, 86)',
                backgroundColor: 'rgba(255, 205, 86, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(255, 205, 86)'
            }]
        },
        options: {
            ...chartConfigs.potassium,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });
    // Biểu đồ pH
    const phCtx = document.getElementById('phChart').getContext('2d');
    charts.ph = new Chart(phCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'pH',
                data: [],
                borderColor: 'rgb(201, 203, 207)',
                backgroundColor: 'rgba(201, 203, 207, 0.2)',
                fill: true,
                tension: 0,
                pointRadius: 4,
                pointHoverRadius: 6,
                pointBackgroundColor: 'rgb(201, 203, 207)'
            }]
        },
        options: {
            ...chartConfigs.ph,
            maintainAspectRatio: false,
            responsive: true,
            animation: false
        }
    });

    console.log('Charts initialized successfully');
}
// Bảng ánh xạ mô tả thời tiết
const weatherTranslations = {
    'clear sky': 'Trời quang',
    'few clouds': 'Ít mây',
    'scattered clouds': 'Mây rải rác',
    'broken clouds': 'Nhiều mây',
    'overcast clouds': 'Trời âm u',
    'light rain': 'Mưa nhẹ',
    'moderate rain': 'Mưa vừa',
    'heavy rain': 'Mưa to',
    'mist': 'Sương mù',
    'fog': 'Sương mù dày',
    'haze': 'Khói mù',
    'thunderstorm': 'Giông bão',
    'thunderstorm with light rain': 'Giông và mưa nhẹ',
    'thunderstorm with rain': 'Giông và mưa',
    'thunderstorm with heavy rain': 'Giông và mưa to'
};
// Hàm cập nhật hiển thị dự báo thời tiết
const updateForecastDisplay = (forecastData) => {
    try {
        const forecastDisplay = document.getElementById('forecast-display');
        if (!forecastDisplay) return;

        if (!forecastData || !Array.isArray(forecastData)) {
            console.error('Invalid forecast data:', forecastData);
            forecastDisplay.innerHTML = '<p class="text-red-500">Không thể tải dữ liệu dự báo thời tiết</p>';
            return;
        }

        let forecastHtml = '<div class="grid grid-cols-1 gap-4">';

        forecastData.forEach((day, index) => {
            if (!day || !day.date) return; 

            const date = new Date(day.date);
            const formattedDate = `${date.getDate()}/${date.getMonth() + 1}`;
            const dayOfWeek = getDayOfWeek(date);
            const descriptionVi = weatherTranslations[day.description] || day.description || 'N/A';
            const dayAndDate = (dayOfWeek === 'CN' ? 'CN' : `T${dayOfWeek}`) + `, ${formattedDate}`;
            forecastHtml += `
                <div class="bg-gray-50 p-3 rounded-lg shadow-sm mb-2">
                    <div class="grid grid-cols-2 gap-x-4 items-center">
                        <!-- Left column -->
                        <div class="flex flex-col items-center">
                            <div class="font-semibold text-black-700 text-lg mb-1" >${dayAndDate}</div>
                            <img src="${day.icon || ''}" alt="weather" class="w-10 h-10 mb-1">
                            <div class="text-sm text-gray-700 text-center">${descriptionVi}</div>
                        </div>
                        <!-- Right column -->
                        <div class="flex flex-col items-end">
                            <div class="font-bold text-lg text-red-500 mb-1 ">
                                <i class="fas fa-thermometer-half"></i>${day.temperature || 'N/A'}°C
                            </div>
                            <div class="text-base text-green-600 mb-1 ">
                                <i class="fas fa-tint mr-1"></i>${day.humidity || 'N/A'}%
                            </div>
                            <div class="text-base text-sky-600 ">
                                <i class="fas fa-cloud-rain mr-1"></i> ${day.rainfall || '0'}mm
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        forecastHtml += '</div>';
        forecastDisplay.innerHTML = forecastHtml;

    } catch (error) {
        console.error('Error updating forecast display:', error);
        const forecastDisplay = document.getElementById('forecast-display');
        if (forecastDisplay) {
            forecastDisplay.innerHTML = '<p class="text-red-500">Lỗi hiển thị dự báo thời tiết</p>';
        }
    }
};

// Hàm lấy thứ trong tuần
function getDayOfWeek(date) {
    const days = ['CN', '2', '3', '4', '5', '6', '7'];
    return days[date.getDay()];
}

// Hàm định dạng thời gian "giờ:phút(ngày/tháng)"
const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    return `${hours}:${minutes}(${day}/${month})`;
};

// Biến toàn cục để lưu trữ dữ liệu lịch sử
let globalHistoryData = [];

// Biến để theo dõi trạng thái lọc thời gian
let isTimeFiltered = false;

// Biến để lưu trữ dữ liệu đã lọc
let filteredHistoryData = null;
let isHistoryTimeFiltered = false;
let isSelectingTime = false;
// Hàm cập nhật biểu đồ
function updateCharts(historyData) {
    if (!historyData || historyData.length === 0) {
        console.log('Không có dữ liệu để hiển thị biểu đồ');
        return;
    }

    let dataToShow;
    if (isTimeFiltered && filteredHistoryData) {
        dataToShow = filteredHistoryData;
        console.log('Hiển thị dữ liệu đã lọc:', dataToShow);
    } else {
        dataToShow = historyData.slice(0, 10).reverse();
        console.log('Hiển thị 10 dữ liệu mới nhất:', dataToShow);
    }

    Object.entries(charts).forEach(([key, chart]) => {
        if (chart) {
            const labels = dataToShow.map(item => formatTime(item.timestamp));
            const data = dataToShow.map(item => {
                if (key === 'rainfall') {
                    return parseFloat(item[key]) || 0;
                }
                return item[key];
            });

            chart.data.labels = labels;
            chart.data.datasets[0].data = data;

            if (key === 'rainfall') {
                const maxRainfall = Math.max(...data);
                if (maxRainfall > chart.options.scales.y.max) {
                    chart.options.scales.y.max = Math.ceil(maxRainfall * 1.2); 
                }
            }

            chart.update();
            console.log(`Đã cập nhật biểu đồ ${key} với ${dataToShow.length} điểm dữ liệu`);
        }
    });
}

function filterData() {
    const startDate = new Date(document.getElementById('startDate').value);
    const endDate = new Date(document.getElementById('endDate').value);

    if (!startDate || !endDate) {
        alert('Vui lòng chọn khoảng thời gian');
        return;
    }

    if (startDate > endDate) {
        alert('Ngày bắt đầu phải nhỏ hơn ngày kết thúc');
        return;
    }

    isTimeFiltered = true;
    console.log('Bắt đầu lọc dữ liệu từ', startDate, 'đến', endDate);

    const filteredData = globalHistoryData.filter(item => {
        const itemDate = new Date(item.timestamp);
        return itemDate >= startDate && itemDate <= endDate;
    });

    if (filteredData.length === 0) {
        alert('Không có dữ liệu trong khoảng thời gian này');
        return;
    }
    // Sắp xếp dữ liệu theo thời gian
    filteredData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    // Tính toán khoảng thời gian giữa các điểm
    const totalDuration = endDate.getTime() - startDate.getTime();
    const interval = totalDuration / 9;
    // Tạo mảng 10 mốc thời gian đều nhau
    const targetTimes = [];
    for (let i = 0; i < 10; i++) {
        targetTimes.push(new Date(startDate.getTime() + (interval * i)));
    }
    // Tìm điểm dữ liệu gần nhất cho mỗi mốc thời gian
    const sampledData = targetTimes.map(targetTime => {
        return findClosestDataPoint(filteredData, targetTime.getTime());
    }).filter(point => point !== null);
    // Đảm bảo không có điểm trùng lặp
    const uniqueData = [];
    const seenTimestamps = new Set();

    sampledData.forEach(point => {
        if (!seenTimestamps.has(point.timestamp)) {
            seenTimestamps.add(point.timestamp);
            uniqueData.push(point);
        }
    });
    // Nếu thiếu điểm, thêm điểm từ dữ liệu gốc
    if (uniqueData.length < 10) {
        for (const point of filteredData) {
            if (uniqueData.length >= 10) break;
            if (!seenTimestamps.has(point.timestamp)) {
                seenTimestamps.add(point.timestamp);
                uniqueData.push(point);
            }
        }
    }
    // Sắp xếp lại theo thời gian
    uniqueData.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
    // Lưu dữ liệu đã lọc
    filteredHistoryData = uniqueData;
    console.log('Dữ liệu sau khi lọc và xử lý:', filteredHistoryData);
    // Cập nhật biểu đồ với dữ liệu đã lọc
    updateCharts(uniqueData);
}

// Hàm tìm điểm dữ liệu gần nhất với thời gian mục tiêu
function findClosestDataPoint(data, targetTime) {
    if (!data || data.length === 0) return null;

    let closestPoint = data[0];
    let minDiff = Math.abs(new Date(data[0].timestamp).getTime() - targetTime);

    for (const point of data) {
        const diff = Math.abs(new Date(point.timestamp).getTime() - targetTime);
        if (diff < minDiff) {
            minDiff = diff;
            closestPoint = point;
        }
    }
    // Nếu điểm gần nhất cách quá xa, trả về null
    if (minDiff > 21600000) { // 6 giờ
        return null;
    }
    return closestPoint;
}

// Nút Reset
function resetCharts() {
    isTimeFiltered = false;
    filteredHistoryData = null;
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    updateCharts(globalHistoryData);
}
// Kiểm tra trạng thái lọc
function handleWebSocketData(data) {
    console.log('WebSocket Data Received');

    try {
        const parsedData = typeof data === 'string' ? JSON.parse(data) : data;
        // Xử lý dữ liệu cảm biến mới nhất
        if (parsedData.latest) {
            lastSensorData = { ...parsedData.latest };
            updateSensorDisplay(parsedData.latest);
            updateNotifications(parsedData.latest);
        }
        // Xử lý dữ liệu lịch sử
        if (parsedData.history && Array.isArray(parsedData.history)) {
            globalHistoryData = parsedData.history;
            if (!window.chartsInitialized) {
                initializeCharts();
                window.chartsInitialized = true;
            }
            // Lấy timestamp mới nhất trong dữ liệu
            const newestTimestamp = globalHistoryData.length > 0 ? new Date(globalHistoryData[0].timestamp).getTime() : null;
            // Cập nhật bảng nếu có dữ liệu mới hơn
            if (
                !isHistoryTimeFiltered &&
                !isSelectingTime &&
                (lastHistoryTimestamp === null || (newestTimestamp && newestTimestamp > lastHistoryTimestamp))
            ) {
                lastHistoryTimestamp = newestTimestamp;
                resetHistoryTable();
                updateHistory(globalHistoryData);
            }
            // Nếu đang lọc hoặc đang chọn thời gian thì không cập nhật bảng!
            if (!isTimeFiltered) {
                updateCharts(globalHistoryData);
            }
        }
        // Xử lý dữ liệu dự báo
        if (parsedData.forecast_5days) {
            updateForecastDisplay(parsedData.forecast_5days);
        }
    } catch (error) {
        console.error('Error processing WebSocket data:', error);
    }
}

// Biến lưu trữ dữ liệu cảm biến cuối cùng
let lastSensorData = {
    temperature: '-',
    humidity: '-',
    rainfall: '-',
    nitrogen: '-',
    phosphorus: '-',
    potassium: '-',
    ph: '-'
};

// Hàm cập nhật hiển thị cảm biến
function updateSensorDisplay(data) {
    try {
        const elements = {
            temperature: { el: document.getElementById('temperature'), unit: '°C' },
            humidity: { el: document.getElementById('humidity'), unit: '%' },
            rainfall: { el: document.getElementById('rainfall'), unit: 'mm' },
            nitrogen: { el: document.getElementById('nitrogen'), unit: 'mg/kg' },
            phosphorus: { el: document.getElementById('phosphorus'), unit: 'mg/kg' },
            potassium: { el: document.getElementById('potassium'), unit: 'mg/kg' },
            ph: { el: document.getElementById('ph'), unit: '' }
        };

        Object.entries(elements).forEach(([key, {el, unit}]) => {
            if (el && data[key] !== undefined) {
                const rawValue = data[key];
                const formattedValue = `${Number(rawValue).toFixed(2)}${unit ? ' ' + unit : ''}`;
                el.innerText = formattedValue;
            }
        });
        // Cập nhật giá trị lượng mưa
        const rainfallElement = document.getElementById('rainfall');
        const monthlyRainfallElement = document.getElementById('monthly_rainfall');
        // Lấy dữ liệu lượng mưa
        fetchRainfallData().then(rainData => {
            if (rainfallElement) {
                rainfallElement.textContent = `${rainData.today.toFixed(2)} mm`;
                console.log(`[${new Date().toLocaleString()}] Lượng mưa hôm nay: ${rainData.today.toFixed(2)}mm`);
            }
            if (monthlyRainfallElement) {
                monthlyRainfallElement.textContent = `${rainData.monthly.toFixed(2)} mm`;
                console.log(`[${new Date().toLocaleString()}] Lượng mưa tháng này: ${rainData.monthly.toFixed(2)}mm`);
            }
            
            data.rainfall = rainData.today;
            data.monthly_rainfall = rainData.monthly;
            console.log('Chi tiết dữ liệu lượng mưa:', {
                today: {
                    value: rainData.today.toFixed(2),
                    unit: 'mm',
                    timestamp: new Date().toLocaleString()
                },
                monthly: {
                    value: rainData.monthly.toFixed(2),
                    unit: 'mm',
                    month: new Date().getMonth() + 1,
                    year: new Date().getFullYear()
                }
            });
        });
    } catch (error) {
        console.error('Error updating sensor display:', error);
    }
}

// Cấu trúc thông báo
let notifications = [];
let notificationCount = 0;
const MAX_NOTIFICATIONS = 20;

function saveNotifications() {
    try {
        localStorage.setItem('notifications', JSON.stringify(notifications));
        localStorage.setItem('notificationCount', notificationCount.toString());
    } catch (error) {
        console.error('Error saving notifications:', error);
    }
}

function loadNotifications() {
    try {
        const savedNotifications = localStorage.getItem('notifications');
        const savedCount = localStorage.getItem('notificationCount');

        if (savedNotifications) {
            notifications = JSON.parse(savedNotifications);
        }

        if (savedCount) {
            notificationCount = parseInt(savedCount) || 0;
        }

        updateNotificationUI();
    } catch (error) {
        console.error('Error loading notifications:', error);
        notifications = [];
        notificationCount = 0;
    }
}

function isDuplicateNotification(message) {
    return notifications.some(notification =>
        notification.message === message
    );
}

function updateNotificationUI() {
    try {
        const notificationList = document.querySelector('.notification-list');
        const rightNotificationList = document.getElementById('right-notification-list');
        // Hiển thị thông báo chưa đọc ở chuông
        const unreadNotifications = notifications.filter(n => !n.read);
        // Hiển thị toàn bộ thông báo ở rightbar
        const allNotifications = [...notifications].reverse();
        const unreadContent = unreadNotifications.length ? unreadNotifications.map(notification => `
            <div class="notification-item ${notification.type || 'sensor'} p-2 border-b border-gray-200">
                <div class="text-sm">${notification.message}</div>
                <div class="text-xs text-black-500">${notification.timestamp}</div>
            </div>
        `).join('') : '<p class="text-center text-gray-500 py-2">Không có thông báo mới!</p>';
        const allContent = allNotifications.length ? allNotifications.map(notification => `
            <div class="notification-item ${notification.type || 'sensor'} p-2 border-b border-gray-200">
                <div class="text-sm">${notification.message}</div>
                <div class="text-xs text-black-500">${notification.timestamp}</div>
            </div>
        `).join('') : '<p class="text-center text-gray-500 py-2">Không có thông báo mới!</p>';

        if (notificationList) {
            notificationList.innerHTML = unreadContent;
            notificationList.scrollTop = notificationList.scrollHeight;
        }
        if (rightNotificationList) {
            rightNotificationList.innerHTML = allContent;
            rightNotificationList.scrollTop = 0;
        }
        // Cập nhật số lượng thông báo chưa đọc
        const notificationCountEl = document.getElementById('notification-count');
        if (notificationCountEl) {
            notificationCountEl.innerText = unreadNotifications.length;
        }
    } catch (error) {
        console.error('Error updating notification UI:', error);
    }
}

const deviceNameVi = {
    light: 'Đèn',
    roof: 'Mái che',
    pump: 'Máy bơm',
    fan: 'Quạt'
};

function updateNotifications(data) {
    try {
        console.log('updateNotifications called with:', data);
        if (!data) return;

        const timestamp = new Date().toLocaleString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });

        let messages = [];

        if (data.type === 'timer') {
            if (data.message) {
                messages.push(data.message); 
            } else {
                const deviceVi = deviceNameVi[data.device] || data.device;
                messages.push(`Hẹn giờ ${deviceVi} ${data.status ? 'bật' : 'tắt'} lúc ${data.time}`);
            }
        } else {
            // Lấy thời gian cảnh báo cuối từ localStorage
            const lastAlertTime = localStorage.getItem('lastAlertTime');
            const currentTime = Date.now();
            const cooldownPeriod = 2 * 60 * 1000; 
            // Kiểm tra thời gian cooldown
            let shouldCheck = true;
            if (lastAlertTime) {
                const timeSinceLastAlert = currentTime - parseInt(lastAlertTime);
                if (timeSinceLastAlert < cooldownPeriod) {
                    const remainingMinutes = Math.floor((cooldownPeriod - timeSinceLastAlert) / 1000 / 60);
                    const remainingSeconds = Math.floor(((cooldownPeriod - timeSinceLastAlert) % (60 * 1000)) / 1000);
                    console.log(`Skipping alerts - remaining cooldown: ${remainingMinutes} minutes ${remainingSeconds} seconds`);
                    shouldCheck = false;
                }
            }

            if (shouldCheck) {
                console.log('Checking all sensor conditions at:', new Date(currentTime).toLocaleString());

                const temperatureThreshold = parseFloat(localStorage.getItem('temperatureAlertThreshold')) || 26.0;
                if (data.temperature > temperatureThreshold) {
                    messages.push(`Nhiệt độ cao: ${data.temperature}°C (Vượt ngưỡng ${temperatureThreshold}°C)`);
                }

                if (data.humidity < 60) {
                    messages.push(`Độ ẩm thấp: ${data.humidity}% (Dưới ngưỡng 60%)`);
                }

                if (data.ph < 5.5 || data.ph > 7.5) {
                    messages.push(`pH không phù hợp: ${data.ph} (Ngoài khoảng 5.5-7.5)`);
                }

                if (messages.length > 0) {
                    localStorage.setItem('lastAlertTime', currentTime.toString());
                }
            }
        }
        // Thêm các thông báo mới vào danh sách
        for (const message of messages) {
            if (!isDuplicateNotification(message)) {
                const newNotification = {
                    message: message,
                    timestamp: timestamp,
                    type: data.type || 'sensor',
                    read: false 
                };
                notifications.push(newNotification);

                if (notifications.length > MAX_NOTIFICATIONS) {
                    notifications = notifications.slice(-MAX_NOTIFICATIONS);
                }
                notificationCount = Math.min(notificationCount + 1, MAX_NOTIFICATIONS);
            }
        }
        if (messages.length > 0) {
            saveNotifications();
            updateNotificationUI();
        }
    } catch (error) {
        console.error('Error updating notifications:', error);
    }
}
// Khởi tạo thông báo khi load trang 
document.addEventListener('DOMContentLoaded', () => {
    const startInput = document.getElementById('history-start-date');
    const endInput = document.getElementById('history-end-date');
    if (startInput && endInput) {
        startInput.addEventListener('focus', () => { isSelectingTime = true; });
        endInput.addEventListener('focus', () => { isSelectingTime = true; });
        startInput.addEventListener('blur', () => { setTimeout(() => { isSelectingTime = false; }, 500); });
        endInput.addEventListener('blur', () => { setTimeout(() => { isSelectingTime = false; }, 500); });
    }
    loadNotifications();
    // Xử lý sự kiện click cho icon thông báo
    const notificationIcon = document.getElementById('notification-icon');
    const notificationContent = document.getElementById('notification-content');

    if (notificationIcon && notificationContent) {
        notificationIcon.addEventListener('click', () => {
            const wasHidden = notificationContent.classList.contains('hidden');
            notificationContent.classList.toggle('hidden');
            if (!wasHidden && notificationContent.classList.contains('hidden')) {
                notifications.forEach(n => n.read = true);
                saveNotifications();
                updateNotificationUI();
            }
        });
        document.addEventListener('click', (event) => {
            if (!notificationIcon.contains(event.target) &&
                !notificationContent.contains(event.target)) {
                notificationContent.classList.add('hidden');
            }
        });
    }

});

setInterval(() => {
    if (
        lastSensorData &&
        typeof lastSensorData.temperature === 'number' &&
        typeof lastSensorData.humidity === 'number' &&
        typeof lastSensorData.ph === 'number'
    ) {
        updateNotifications(lastSensorData);
    }
}, 2 * 60 * 1000);
// Hàm cập nhật lịch sử cảm biến
const updateHistory = (history) => {
    const tableBody = document.getElementById('history-table');
    if (tableBody) {
        tableBody.innerHTML = history.map(row => {
            let date = new Date(row.timestamp);
            if (!isNaN(date.getTime())) {
                const hours = date.getHours().toString().padStart(2, '0');
                const minutes = date.getMinutes().toString().padStart(2, '0');
                const day = date.getDate().toString().padStart(2, '0');
                const month = (date.getMonth() + 1).toString().padStart(2, '0');
                row.timestamp = `${hours}:${minutes}(${day}/${month})`;
            }
            return `
                <tr>
                    <td>${row.timestamp}</td>
                    <td>${Number(row.temperature).toFixed(2)}</td>
                    <td>${Number(row.humidity).toFixed(2)}</td>
                    <td>${Number(row.rainfall).toFixed(2)}</td>
                    <td>${Number(row.nitrogen).toFixed(2)}</td>
                    <td>${Number(row.phosphorus).toFixed(2)}</td>
                    <td>${Number(row.potassium).toFixed(2)}</td>
                    <td>${Number(row.ph).toFixed(2)}</td>
                </tr>
            `;
        }).join('');
    }
};
// Hàm cập nhật thời gian hiện tại
const updateTime = () => {
    const now = new Date();
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');
        const seconds = String(now.getSeconds()).padStart(2, '0');
        timeElement.innerText = `${hours}:${minutes}:${seconds}`;
    }
};
setInterval(updateTime, 1000);
updateTime();
// Xử lý điều hướng menu
function navigate(page) {
    document.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
    const pageEl = document.getElementById(page);
    if (pageEl) {
        pageEl.classList.add('active');
        if (page === 'data-sensor' && Object.values(lastSensorData).some(value => value !== '-')) {
            updateSensorDisplay(lastSensorData);
        }
    }
}
// Kết nối WebSocket để nhận dữ liệu
const wsProtocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
const wsHost = window.location.host;
const ws = new WebSocket(`${wsProtocol}://${wsHost}/ws`);

ws.onopen = () => console.log('Connected to WebSocket server');
ws.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        handleWebSocketData(data);
    } catch (error) {
        console.error('Error parsing WebSocket data:', error);
    }
};
ws.onerror = (error) => console.error('WebSocket Error:', error);
ws.onclose = () => {
    console.log('Disconnected from WebSocket server');
    // Thử kết nối lại sau 5 giây
    setTimeout(() => {
        window.location.reload();
    }, 5000);
};

// Kiểm tra đăng nhập
function checkLogin() {
    if (!localStorage.getItem('isLoggedIn')) {
        window.location.href = 'login.html';
    }
}

// Xử lý đăng xuất
function handleLogout() {
    localStorage.removeItem('isLoggedIn');
    localStorage.removeItem('username');
    localStorage.removeItem('rememberMe');
    window.location.href = 'login.html';
}

document.addEventListener('DOMContentLoaded', function() {
    checkLogin();
    const logoutButton = document.querySelector('.logout-btn');
    if (logoutButton) {
        logoutButton.addEventListener('click', function(e) {
            e.preventDefault();
            handleLogout();
        });
    }

    function updateCurrentTime() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('vi-VN');
        document.getElementById('current-time').textContent = timeString;
    }

    setInterval(updateCurrentTime, 1000);
    updateCurrentTime();
});

// Biến theo dõi kết nối MQTT
let globalMQTTClient = null;
let globalMQTTConnected = false;

async function initGlobalMQTT() {
    try {
        console.log("Initializing global MQTT client...");

        const response = await fetch('/api/mqtt-config');
        if (!response.ok) {
            throw new Error('Failed to get MQTT config');
        }
        const config = await response.json();
        if (!config.success) {
            throw new Error('Invalid MQTT config');
        }
        const clientId = `web_client_${Date.now()}`;
        const host = config.host;
        const port = config.port;
        const userName = config.username;
        const password = config.password;

        globalMQTTClient = new Paho.MQTT.Client(host, port, clientId);

        globalMQTTClient.onConnectionLost = function(responseObject) {
            console.log('MQTT Connection lost:', responseObject.errorMessage);
            globalMQTTConnected = false;
            setTimeout(initGlobalMQTT, 5000);
        };
        globalMQTTClient.onMessageArrived = function(message) {
            console.log('MQTT Message arrived:', message.destinationName, message.payloadString);
            try {
                const topic = message.destinationName;
                const payload = JSON.parse(message.payloadString);
                if (topic.startsWith('iot/device/status/')) {
                    const device = topic.split('/').pop();
                    if (typeof updateDeviceStatus === 'function') {
                        updateDeviceStatus(device, payload.status);
                    }
                }
            } catch (error) {
                console.error('Error processing MQTT message:', error);
            }
        };
        
        const options = {
            useSSL: true,
            userName: userName,
            password: password,
            keepAliveInterval: 60,
            cleanSession: true,
            onSuccess: function() {
                console.log('Connected to MQTT broker successfully');
                globalMQTTConnected = true;
                try {
                    globalMQTTClient.subscribe('iot/device/status/#', {qos: 0});
                    globalMQTTClient.subscribe('iot/device/control/#', {qos: 0});
                    const testMessage = new Paho.MQTT.Message(JSON.stringify({
                        type: 'connection_test',
                        clientId: globalMQTTClient.clientId,
                        timestamp: new Date().toISOString()
                    }));
                    testMessage.destinationName = 'iot/test';
                    testMessage.qos = 0;
                    globalMQTTClient.send(testMessage);
                    console.log('Subscribed to MQTT topics and sent test message');
                    const event = new CustomEvent('mqttConnected');
                    window.dispatchEvent(event);
                } catch (error) {
                    console.error('Error after MQTT connection:', error);
                }
            },
            onFailure: function(error) {
                console.error('Failed to connect to MQTT broker:', error.errorMessage);
                globalMQTTConnected = false;
                setTimeout(initGlobalMQTT, 5000);
            },
            timeout: 30,
            mqttVersion: 3
        };
        globalMQTTClient.connect(options);
    } catch (error) {
        console.error("Error initializing MQTT:", error);
        setTimeout(initGlobalMQTT, 5000);
    }
}

if (typeof window !== 'undefined') {
document.addEventListener('DOMContentLoaded', function() {
        function waitForPahoAndInit() {
            if (typeof Paho !== 'undefined') {
                initGlobalMQTT();
    } else {
                setTimeout(waitForPahoAndInit, 500);
    }
        }
        waitForPahoAndInit();
    });
}

function elementExists(id) {
    return document.getElementById(id) !== null;
}
// Các hàm xử lý thông báo
function updateNotificationCount() {
    const countElement = document.getElementById('notification-count');
    if (countElement) {
        countElement.textContent = notifications.length;
    }
}

function updateNotificationList() {
    const notificationList = document.querySelector('.notification-list');
    const rightNotificationList = document.getElementById('right-notification-list');

    if (!notifications.length) {
        const emptyMessage = '<p class="text-center text-gray-500 py-2">Không có thông báo mới!</p>';
        if (notificationList) notificationList.innerHTML = emptyMessage;
        if (rightNotificationList) rightNotificationList.innerHTML = emptyMessage;
        return;
    }

    const notificationContent = notifications.map(notification => `
        <div class="notification-item p-2 border-b border-gray-200">
            <div class="text-sm">${notification.message}</div>
            <div class="text-xs text-gray-500">${notification.timestamp}</div>
        </div>
    `).join('');

    if (notificationList) {
        notificationList.innerHTML = notificationContent;
        notificationList.scrollTop = notificationList.scrollHeight;
    }

    if (rightNotificationList) {
        rightNotificationList.innerHTML = notificationContent;
        rightNotificationList.scrollTop = rightNotificationList.scrollHeight;
    }
}

// Hàm lấy dữ liệu lượng mưa
async function fetchRainfallData() {
    const API_KEY = 'b40cf9be255e9dce69c0bf304137fb2e';
    const CITY = 'Thu Duc';
    const UNITS = 'metric';
    const LANG = 'en';

    try {
        const response = await fetch(`https://api.openweathermap.org/data/2.5/forecast?q=${CITY}&appid=${API_KEY}&units=${UNITS}&lang=${LANG}`);
        const data = await response.json();

        if (response.status !== 200) {
            console.error('Lỗi lấy dữ liệu thời tiết:', data.message);
            return { today: 0, monthly: 0 };
        }

        const today = new Date();
        let todayRain = 0;
        let monthlyRain = 0;

        // Tính tổng lượng mưa trong ngày
        for (const forecast of data.list) {
            const forecastTime = new Date(forecast.dt * 1000);

            // Kiểm tra nếu là dự báo cho ngày hôm nay
            if (forecastTime.getDate() === today.getDate() &&
                forecastTime.getMonth() === today.getMonth() &&
                forecastTime.getFullYear() === today.getFullYear()) {

                const rain = forecast.rain ? forecast.rain['3h'] || 0 : 0;
                todayRain += rain;
            }

            // Kiểm tra nếu là dự báo trong tháng này
            if (forecastTime.getMonth() === today.getMonth() &&
                forecastTime.getFullYear() === today.getFullYear()) {

                const rain = forecast.rain ? forecast.rain['3h'] || 0 : 0;
                monthlyRain += rain;
            }
        }

        console.log(`Lượng mưa hôm nay: ${todayRain.toFixed(2)}mm`);
        console.log(`Lượng mưa tháng này: ${monthlyRain.toFixed(2)}mm`);

        return {
            today: todayRain,
            monthly: monthlyRain
        };
    } catch (error) {
        console.error('Lỗi khi lấy dữ liệu lượng mưa:', error);
        return { today: 0, monthly: 0 };
    }
}
// Cập nhật dữ liệu lượng mưa định kỳ
setInterval(async () => {
    try {
        const rainData = await fetchRainfallData();
        const rainfallElement = document.getElementById('rainfall');
        const monthlyRainfallElement = document.getElementById('monthly_rainfall');

        if (rainfallElement) {
            rainfallElement.textContent = `${rainData.today.toFixed(2)} mm`;
        }
        if (monthlyRainfallElement) {
            monthlyRainfallElement.textContent = `${rainData.monthly.toFixed(2)} mm`;
        }
    } catch (error) {
        console.error('Lỗi khi cập nhật dữ liệu lượng mưa:', error);
    }
}, 30 * 60 * 1000); // 30 phút

// Hàm tải lại bảng lịch sử
function renderHistoryTable(data) {
    const tableBody = document.getElementById('history-table');
    if (!tableBody) return;
    tableBody.innerHTML = '';
    if (!data || data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="8" class="text-center">Không có dữ liệu</td></tr>';
        return;
    }
    // Đảo ngược thứ tự dữ liệu
    const reversedData = [...data].reverse();
    reversedData.forEach(row => {
        const tr = document.createElement('tr');
        let date = new Date(row.timestamp);
        if (!isNaN(date.getTime())) {
            const hours = date.getHours().toString().padStart(2, '0');
            const minutes = date.getMinutes().toString().padStart(2, '0');
            const day = date.getDate().toString().padStart(2, '0');
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            row.timestamp = `${hours}:${minutes}(${day}/${month})`;
        }
        tr.innerHTML = `
            <td>${row.timestamp}</td>
            <td>${Number(row.temperature).toFixed(2)}</td>
            <td>${Number(row.humidity).toFixed(2)}</td>
            <td>${Number(row.rainfall).toFixed(2)}</td>
            <td>${Number(row.nitrogen).toFixed(2)}</td>
            <td>${Number(row.phosphorus).toFixed(2)}</td>
            <td>${Number(row.potassium).toFixed(2)}</td>
            <td>${Number(row.ph).toFixed(2)}</td>
        `;
        tableBody.appendChild(tr);
    });
}
// Hàm lọc dữ liệu lịch sử theo thời gian
function filterHistoryData() {
    const start = document.getElementById('history-start-date').value;
    const end = document.getElementById('history-end-date').value;
    if (!start || !end) {
        alert('Vui lòng chọn đầy đủ thời gian bắt đầu và kết thúc!');
        return;
    }
    const startTime = new Date(start).getTime();
    const endTime = new Date(end).getTime();
    if (startTime > endTime) {
        alert('Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc!');
        return;
    }
    // Lọc dữ liệu
    const filtered = globalHistoryData.filter(row => {
        const rowTime = new Date(row.timestamp).getTime();
        return rowTime >= startTime && rowTime <= endTime;
    });
    isHistoryTimeFiltered = true;
    renderHistoryTable(filtered);
}

function resetHistoryTable() {
    isHistoryTimeFiltered = false;
    // Hiển thị toàn bộ dữ liệu
    renderHistoryTable(globalHistoryData.slice(0, 10));

    const startDateInput = document.getElementById('history-start-date');
    if (startDateInput) startDateInput.value = '';

    const endDateInput = document.getElementById('history-end-date');
    if (endDateInput) endDateInput.value = '';
}

function updateHistoryTable(history) {
    globalHistoryData = history;
    renderHistoryTable(history.slice(0, 10));
}

// Gắn sự kiện cho nút lọc và reset
document.addEventListener('DOMContentLoaded', function() {
    const filterBtn = document.getElementById('history-filter-btn');
    if (filterBtn) filterBtn.addEventListener('click', filterHistoryData);

    const resetBtn = document.getElementById('history-reset-btn');
    if (resetBtn) resetBtn.addEventListener('click', resetHistoryTable);
});

function exportFilteredHistoryToExcel() {
    let exportData = [];
    if (isHistoryTimeFiltered && typeof renderHistoryTable === 'function') {
        // Lấy dữ liệu đang hiển thị trên bảng
        const tableBody = document.getElementById('history-table');
        if (tableBody) {
            exportData = Array.from(tableBody.querySelectorAll('tr')).map(tr => {
                const tds = tr.querySelectorAll('td');
                if (tds.length === 8) {
                    return {
                        'Thời gian': tds[0].innerText,
                        'Nhiệt độ (°C)': tds[1].innerText,
                        'Độ ẩm (%)': tds[2].innerText,
                        'Lượng mưa (mm)': tds[3].innerText,
                        'Nitrogen (mg/kg)': tds[4].innerText,
                        'Phosphorus (mg/kg)': tds[5].innerText,
                        'Potassium (mg/kg)': tds[6].innerText,
                        'pH': tds[7].innerText
                    };
                }
                return null;
            }).filter(Boolean);
        }
    } else {
        // Lọc dữ liệu của ngày hôm nay
        const today = new Date();
        const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 0, 0, 0, 0);
        const todayEnd = new Date(today.getFullYear(), today.getMonth(), today.getDate(), 23, 59, 59, 999);

        exportData = globalHistoryData
            .filter(row => {
                const rowTime = new Date(row.timestamp);
                return rowTime >= todayStart && rowTime <= todayEnd;
            })
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
            .map(row => ({
                'Thời gian': row.timestamp,
                'Nhiệt độ (°C)': Number(row.temperature).toFixed(2),
                'Độ ẩm (%)': Number(row.humidity).toFixed(2),
                'Lượng mưa (mm)': Number(row.rainfall).toFixed(2),
                'Nitrogen (mg/kg)': Number(row.nitrogen).toFixed(2),
                'Phosphorus (mg/kg)': Number(row.phosphorus).toFixed(2),
                'Potassium (mg/kg)': Number(row.potassium).toFixed(2),
                'pH': Number(row.ph).toFixed(2)
            }));
    }

    if (exportData.length === 0) {
        alert('Không có dữ liệu để xuất báo cáo!');
        return;
    }
    // Tạo worksheet và workbook
    const ws = XLSX.utils.json_to_sheet(exportData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Báo cáo lịch sử');
    // Xuất file
    XLSX.writeFile(wb, 'bao_cao_lich_su.xlsx');
}

// Gắn sự kiện cho nút xuất Excel
document.addEventListener('DOMContentLoaded', function() {
    const exportBtn = document.getElementById('export-excel-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', exportFilteredHistoryToExcel);
    }
});
// Hàm cập nhật góc xoay của nhãn trục x
function updateChartTicks() {
    const isMobile = window.innerWidth <= 768;
    const rotation = isMobile ? 45 : 0;

    Object.values(charts).forEach(chart => {
        if (chart) {
            chart.options.scales.x.ticks.maxRotation = rotation;
            chart.options.scales.x.ticks.minRotation = rotation;
            chart.update();
        }
    });
}
// Lắng nghe sự kiện thay đổi kích thước màn hình
window.addEventListener('resize', debounce(updateChartTicks, 200));