// device-control.js
// Khởi tạo client MQTT
function initializeMQTT() {
    try {
        // Lấy cấu hình MQTT từ server
        fetch('/api/mqtt-config')
            .then(response => response.json())
            .then(config => {
                if (!config.success) {
                    throw new Error('Không thể lấy cấu hình MQTT');
                }

                // Tạo client MQTT mới với WebSocket transport
                client = new Paho.MQTT.Client(
                    config.host,
                    config.port,
                    `iot_client_${Date.now()}`
                );

                // Cấu hình các callback
                client.onConnectionLost = function(responseObject) {
                    console.log('MQTT Connection lost:', responseObject.errorMessage);
                    isConnected = false;
                    updateConnectionStatus(false);
                    const delay = Math.min(1000 * Math.pow(2, client._reconnectAttempts || 0), 30000);
                    client._reconnectAttempts = (client._reconnectAttempts || 0) + 1;
                    console.log(`Reconnecting in ${delay/1000} seconds...`);
                    setTimeout(initializeMQTT, delay);
                };

                client.onMessageArrived = onMessageArrived;

                // Cấu hình kết nối
                const options = {
                    useSSL: true,
                    userName: config.username,
                    password: config.password,
                    keepAliveInterval: 60,
                    cleanSession: true,
                    onSuccess: function() {
                        console.log('Connected to MQTT broker successfully');
                        isConnected = true;
                        client._reconnectAttempts = 0;
                        updateConnectionStatus(true);

                        setTimeout(() => {
                            if (client && client.isConnected()) {
                                client.subscribe('iot/device/status/#', {qos: 1});
                                client.subscribe('iot/device/control/#', {qos: 1});

                                devices.forEach(device => {
                                    requestDeviceStatus(device);
                                });

                                console.log('Subscribed to topics and requested device states');
                            } else {
                                console.error('Client not connected when trying to subscribe');
                                setTimeout(initializeMQTT, 5000);
                            }
                        }, 1000);
                    },
                    onFailure: function(error) {
                        console.error("❌ Lỗi kết nối MQTT:", error);
                        console.error("Chi tiết lỗi:", {
                            errorCode: error.errorCode,
                            errorMessage: error.errorMessage,
                            host: error.host,
                            port: error.port
                        });
                        isConnected = false;
                        updateConnectionStatus(false);
                        const delay = Math.min(1000 * Math.pow(2, client._reconnectAttempts || 0), 30000);
                        client._reconnectAttempts = (client._reconnectAttempts || 0) + 1;
                        console.log(`Reconnecting in ${delay/1000} seconds...`);
                        setTimeout(initializeMQTT, delay);
                    },
                    timeout: 30,
                    mqttVersion: 3
                };

                client.connect(options);
            })
            .catch(error => {
                console.error('❌ Lỗi khi lấy cấu hình MQTT:', error);
                const delay = Math.min(1000 * Math.pow(2, client?._reconnectAttempts || 0), 30000);
                if (client) client._reconnectAttempts = (client._reconnectAttempts || 0) + 1;
                console.log(`Reconnecting in ${delay/1000} seconds...`);
                setTimeout(initializeMQTT, delay);
            });
    } catch (error) {
        console.error('❌ Lỗi khi khởi tạo MQTT:', error);
        const delay = Math.min(1000 * Math.pow(2, client?._reconnectAttempts || 0), 30000);
        if (client) client._reconnectAttempts = (client._reconnectAttempts || 0) + 1;
        console.log(`Reconnecting in ${delay/1000} seconds...`);
        setTimeout(initializeMQTT, delay);
    }
}

function connectMQTT() {
    if (!client) {
        console.error('MQTT client not initialized');
        return;
    }
    if (client.isConnected && client.isConnected()) {
        console.log('MQTT client is already connected');
        return;
    }
    if (client._connectTimeout) {
        console.log('MQTT client is connecting, please wait...');
        return;
    }
    try {
        console.log('Connecting to MQTT broker with options:', connectionOptions);
        client.connect(connectionOptions);
    } catch (error) {
        console.error('Connection error:', error);
        isConnected = false;
        setTimeout(connectMQTT, 5000);
    }
}

function onConnect() {
    console.log('Connected to MQTT broker successfully');
    isConnected = true;

    setTimeout(() => {
        if (client && client.isConnected()) {
            client.subscribe('iot/device/status/#', {qos: 1});
            client.subscribe('iot/device/control/#', {qos: 1});

            devices.forEach(device => {
                requestDeviceStatus(device);
            });

            console.log('Subscribed to topics and requested device states');
        } else {
            console.error('Client not connected when trying to subscribe');
            setTimeout(connectMQTT, 5000);
        }
    }, 1000);
}

function onFailure(error) {
    console.error("❌ Lỗi kết nối MQTT:", error);
    console.error("Chi tiết lỗi:", {
        errorCode: error.errorCode,
        errorMessage: error.errorMessage,
        host: error.host,
        port: error.port
    });
    setTimeout(initializeMQTT, 5000);
}

function onConnectionLost(responseObject) {
    if (responseObject.errorCode !== 0) {
        console.error("❌ Mất kết nối MQTT:", responseObject.errorMessage);
        updateConnectionStatus(false);
        setTimeout(initializeMQTT, 5000);
    }
}

function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('mqtt-status');
    if (statusElement) {
        statusElement.textContent = connected ? '✅ Đã kết nối' : '❌ Mất kết nối';
        statusElement.className = connected ? 'text-green-500' : 'text-red-500';
    }
}

function onMessageArrived(message) {
    console.log('Message arrived:', message.destinationName, message.payloadString);
    try {
        const topic = message.destinationName;
        const payload = JSON.parse(message.payloadString);

        if (topic.startsWith('iot/device/status/')) {
            const device = topic.split('/')[3];
            if (device && devices.includes(device)) {
                if (payload.type === 'request_status') {
                    console.log(`Bỏ qua message request_status cho ${device}`);
                    return;
                }
                const newStatus = payload.status;
                if (typeof newStatus !== 'undefined') {
                    console.log(`Received status update for ${device}: ${newStatus}`);
                    deviceSettings[device].status = newStatus;
                    updateDeviceUI(device);

                    const toggleElement = document.getElementById(`${device}-onoff`);
                    if (toggleElement) {
                        if (newStatus) {
                            toggleElement.classList.add('active');
                        } else {
                            toggleElement.classList.remove('active');
                        }
                    }
                }
            }
        }
    } catch (error) {
        console.error('Error processing message:', error);
    }
}

function controlDevice(device, status) {
    if (!client || !isConnected) {
        console.error('MQTT client not connected');
        alert('Không thể kết nối đến MQTT broker. Vui lòng thử lại sau.');
        return;
    }

    try {
        console.log(`Sending control command for ${device}: ${status}`);

        const message = new Paho.MQTT.Message(JSON.stringify({
            status: status,
            timestamp: new Date().toISOString()
        }));
        message.destinationName = `iot/device/control/${device}`;
        message.qos = 1;

        client.send(message);
    } catch (error) {
        console.error('Error controlling device:', error);
        alert('Có lỗi xảy ra khi điều khiển thiết bị');
    }
}

const inputStates = {
    light: { isEditing: false, timeoutId: null },
    roof: { isEditing: false, timeoutId: null },
    pump: { isEditing: false, timeoutId: null },
    fan: { isEditing: false, timeoutId: null }
};

function initializeTimerInputs(device) {
    // Danh sách tất cả các ô nhập liệu liên quan đến timer của thiết bị này
    const inputs = [
        document.getElementById(`${device}-on-time`),
        document.getElementById(`${device}-off-time`),
        document.getElementById(`${device}-on-date`),
        document.getElementById(`${device}-off-date`)
    ];

    // Hàm khi người dùng bấm vào ô nhập liệu
    const handleFocus = () => {
        // Xóa timeout cũ nếu có
        if (inputStates[device].timeoutId) {
            clearTimeout(inputStates[device].timeoutId);
            inputStates[device].timeoutId = null;
        }
        // Đánh dấu là ĐANG CHỈNH SỬA -> Chặn mọi cập nhật từ server
        inputStates[device].isEditing = true;
        console.log(`[LOCK] Locked updates for ${device} (User editing)`);
    };

    // Hàm khi người dùng bấm ra ngoài (dừng nhập)
    const handleBlur = () => {
        // Đợi 2 giây sau mới cho phép cập nhật lại (để tránh bị nháy khi chuyển ô)
        inputStates[device].timeoutId = setTimeout(() => {
            inputStates[device].isEditing = false;
            console.log(`[UNLOCK] Unlocked updates for ${device}`);
        }, 2000); 
    };

    // Gán sự kiện cho từng ô input
    inputs.forEach(input => {
        if (input) {
            input.addEventListener('focus', handleFocus); // Khi nhấp vào
            input.addEventListener('click', handleFocus); // Hoặc khi click vào
            input.addEventListener('blur', handleBlur);   // Khi nhấp ra ngoài
            input.addEventListener('change', handleFocus); // Khi thay đổi giá trị
        }
    });
}

function updateDeviceUI(device) {
    try {
        console.log(`Updating UI for device ${device}:`, deviceSettings[device]);

        const imgElement = document.getElementById(`${device}-image`);
        if (imgElement) {
            let newSrc;
            if (device === 'roof') {
                newSrc = `../static/img/roof-${deviceSettings[device].status ? 'open' : 'closed'}.png`;
            } else {
                newSrc = `../static/img/${device}-${deviceSettings[device].status ? 'on' : 'off'}.png`;
            }
            imgElement.src = newSrc;
        }

        const toggleElement = document.getElementById(`${device}-onoff`);
        if (toggleElement) {
            if (deviceSettings[device].status) {
                toggleElement.classList.add('active');
            } else {
                toggleElement.classList.remove('active');
            }
        }

        const timerToggle = document.getElementById(`${device}-timer-toggle`);
        if (timerToggle) {
            if (deviceSettings[device].enabled) {
                timerToggle.classList.add('active');
            } else if (!deviceSettings[device].daily) {
                timerToggle.classList.remove('active');
                updateTimerUI(device, null, false);
            }
        }
    } catch (error) {
        console.error(`Error updating UI for ${device}:`, error);
    }
}

function updateTimerUI(device, timer, forceUpdate = false) {
    const onDateInput = document.getElementById(`${device}-on-date`);
    const onTimeInput = document.getElementById(`${device}-on-time`);
    const offDateInput = document.getElementById(`${device}-off-date`);
    const offTimeInput = document.getElementById(`${device}-off-time`);
    const dailyCheckbox = document.getElementById(`${device}-daily`);

    if (!forceUpdate && inputStates[device].isEditing) {
        console.log(`Skipping UI update for ${device} because user is editing`);
        return;
    }

    if (!timer || !timer.enabled) {
        deviceSettings[device].enabled = false;
        const timerToggle = document.getElementById(`${device}-timer-toggle`);
        if (timerToggle) timerToggle.classList.remove('active');
        if (onDateInput) onDateInput.value = '';
        if (onTimeInput) onTimeInput.value = '';
        if (offDateInput) offDateInput.value = '';
        if (offTimeInput) offTimeInput.value = '';
        if (dailyCheckbox) dailyCheckbox.checked = false;
        return;
    }

    deviceSettings[device].enabled = true;
    const timerToggle = document.getElementById(`${device}-timer-toggle`);
    if (timerToggle) timerToggle.classList.add('active');

    const onDateTime = new Date(timer.on_datetime);
    const offDateTime = new Date(timer.off_datetime);
    const onDate = onDateTime.toISOString().split('T')[0];
    const onTime = onDateTime.toTimeString().slice(0, 5);
    const offDate = offDateTime.toISOString().split('T')[0];
    const offTime = offDateTime.toTimeString().slice(0, 5);

    if (onDateInput) onDateInput.value = onDate;
    if (onTimeInput) onTimeInput.value = onTime;
    if (offDateInput) offDateInput.value = offDate;
    if (offTimeInput) offTimeInput.value = offTime;
    if (dailyCheckbox) dailyCheckbox.checked = timer.daily || false;

    if (timer.daily) {
        if (onDateInput) onDateInput.disabled = true;
        if (offDateInput) offDateInput.disabled = true;
    } else {
        if (onDateInput) onDateInput.disabled = false;
        if (offDateInput) offDateInput.disabled = false;
    }

    console.log(`Updated timer UI for ${device}:`, {
        enabled: timer.enabled,
        onDate,
        onTime,
        offDate,
        offTime,
        daily: timer.daily
    });
}

let isConnected = false;
let client = null;
const devices = ['light', 'roof', 'pump', 'fan'];
const deviceSettings = {
    light: { enabled: false, onTime: '', offTime: '', onDate: '', offDate: '', daily: false, status: false },
    roof: { enabled: false, onTime: '', offTime: '', onDate: '', offDate: '', daily: false, status: false },
    pump: { enabled: false, onTime: '', offTime: '', onDate: '', offDate: '', daily: false, status: false },
    fan: { enabled: false, onTime: '', offTime: '', onDate: '', offDate: '', daily: false, status: false }
};
const deviceTimers = {
    light: { on: null, off: null },
    roof: { on: null, off: null },
    pump: { on: null, off: null },
    fan: { on: null, off: null }
};

document.addEventListener('DOMContentLoaded', async function() {
    initializeMQTT();

   // Thêm interval kiểm tra trạng thái timer
    setInterval(async () => {
        // Nếu mất kết nối MQTT thì thử kết nối lại
        if (!isConnected) {
            console.log('MQTT disconnected, trying to reconnect...');
            initializeMQTT();
            return; // Dừng luôn vòng lặp
        }

        const devices = ['light', 'roof', 'pump', 'fan'];
        for (const device of devices) {
            // --- CHỐT CHẶN QUAN TRỌNG NHẤT ---
            // Nếu người dùng đang nhập liệu cho thiết bị này -> BỎ QUA NGAY
            if (inputStates[device] && inputStates[device].isEditing) {
                // console.log(`Skipping poll for ${device} because user is editing`);
                continue; 
            }
            // ----------------------------------

            try {
                const response = await fetch(`/api/get-timer/${device}`);
                const data = await response.json();

                // Logic xử lý dữ liệu (đã được sửa tham số false)
                if (data.success && data.timer) {
                    const now = new Date();
                    const offDateTime = new Date(data.timer.off_datetime);
                    const isDaily = data.timer.daily || false;
                    const isExpired = offDateTime < now;

                    if (isExpired && !isDaily && deviceSettings[device].enabled) {
                        deviceSettings[device].enabled = false;
                        updateDeviceUI(device);
                        updateTimerUI(device, null, false); // false: không ép cập nhật
                    } else if (isDaily && isExpired) {
                        // Logic daily... (giữ nguyên logic của bạn)
                        const nextDay = new Date();
                        nextDay.setDate(nextDay.getDate() + 1);
                        deviceSettings[device].onDate = nextDay.toISOString().split('T')[0];
                        deviceSettings[device].offDate = nextDay.toISOString().split('T')[0];
                        updateDeviceUI(device);
                        updateTimerUI(device, data.timer, false); // false
                    } else if (deviceSettings[device].enabled) {
                        updateTimerUI(device, data.timer, false); // false
                    }
                } else if (deviceSettings[device].enabled) {
                    // Server không có timer, tắt local đi
                    deviceSettings[device].enabled = false;
                    updateDeviceUI(device);
                    updateTimerUI(device, null, false); // false
                }
            } catch (error) {
                console.error(`Error checking timer status for ${device}:`, error);
            }
        }
    }, 5000);

    // Load timer khi trang được tải
    try {
        console.log('Loading timers from server...');
        const devices = ['light', 'roof', 'pump', 'fan'];
        for (const device of devices) {
            try {
                console.log(`Fetching timer for ${device}...`);
                const response = await fetch(`/api/get-timer/${device}`);
                const data = await response.json();
                console.log(`Timer data for ${device}:`, data);

                if (data.success && data.timer) {
                    const now = new Date();
                    const offDateTime = new Date(data.timer.off_datetime);
                    const isDaily = data.timer.daily || false;
                    const isExpired = offDateTime < now;

                    if (isExpired && !isDaily) {
                        deviceSettings[device] = {
                            ...deviceSettings[device],
                            enabled: false,
                            onTime: '',
                            offTime: '',
                            onDate: '',
                            offDate: '',
                            daily: false
                        };
                        updateTimerUI(device, null, true);
                    } else {
                        deviceSettings[device] = {
                            ...deviceSettings[device],
                            enabled: true,
                            onTime: new Date(data.timer.on_datetime).toTimeString().slice(0, 5),
                            offTime: new Date(data.timer.off_datetime).toTimeString().slice(0, 5),
                            onDate: new Date(data.timer.on_datetime).toISOString().split('T')[0],
                            offDate: new Date(data.timer.off_datetime).toISOString().split('T')[0],
                            daily: isDaily
                        };
                        updateTimerUI(device, data.timer, true);
                    }
                } else {
                    console.log(`No active timer found for ${device}`);
                    deviceSettings[device] = {
                        ...deviceSettings[device],
                        enabled: false,
                        onTime: '',
                        offTime: '',
                        onDate: '',
                        offDate: '',
                        daily: false
                    };
                    updateTimerUI(device, null, true);
                }
            } catch (error) {
                console.error(`Error loading timer for ${device}:`, error);
                deviceSettings[device] = {
                    ...deviceSettings[device],
                    enabled: false,
                    onTime: '',
                    offTime: '',
                    onDate: '',
                    offDate: '',
                    daily: false
                };
                updateTimerUI(device, null, true);
            }
        }
    } catch (error) {
        console.error('Error loading timers:', error);
    }

    // Các sự kiện khác
    window.addEventListener('deviceTimerTriggered', function(event) {
        const { device, action } = event.detail;
        console.log(`Nhận sự kiện timer từ common.js: ${device}, action: ${action}`);

        if (action === 'on') {
            deviceSettings[device].status = true;
        } else if (action === 'off') {
            deviceSettings[device].status = false;
        }
        updateDeviceUI(device);
    });

    window.addEventListener('deviceTimerCompleted', async function(event) {
        const { device } = event.detail;
        console.log(`Nhận sự kiện timer hoàn thành từ common.js: ${device}`);

        try {
            const response = await fetch(`/api/get-timer/${device}`);
            const data = await response.json();
            console.log(`Timer data after completion for ${device}:`, data);

            if (data.success && data.timer) {
                const now = new Date();
                const offDateTime = new Date(data.timer.off_datetime);
                const isDaily = data.timer.daily || false;
                const isExpired = offDateTime < now;

                if (isExpired && !isDaily) {
                    deviceSettings[device].enabled = false;
                    updateDeviceUI(device);
                    updateTimerUI(device, null, true);
                } else if (isDaily) {
                    console.log(`Timer for ${device} completed but in daily mode, keeping UI unchanged.`);
                    const nextDay = new Date();
                    nextDay.setDate(nextDay.getDate() + 1);
                    deviceSettings[device].onDate = nextDay.toISOString().split('T')[0];
                    deviceSettings[device].offDate = nextDay.toISOString().split('T')[0];
                    updateDeviceUI(device);
                    updateTimerUI(device, data.timer, true);
                } else {
                    updateDeviceUI(device);
                    updateTimerUI(device, data.timer, true);
                }
            } else {
                deviceSettings[device].enabled = false;
                updateDeviceUI(device);
                updateTimerUI(device, null, true);
            }
        } catch (error) {
            console.error(`Error fetching timer status for ${device} after completion:`, error);
            deviceSettings[device].enabled = false;
            updateDeviceUI(device);
            updateTimerUI(device, null, true);
        }
    });

    window.addEventListener('deviceTimerRescheduled', function(event) {
        const { device, nextOnTime, nextOffTime } = event.detail;
        console.log(`Nhận sự kiện timer được lên lịch lại từ common.js: ${device}`);

        deviceSettings[device].onTime = nextOnTime.toTimeString().slice(0, 5);
        deviceSettings[device].offTime = nextOffTime.toTimeString().slice(0, 5);
        deviceSettings[device].onDate = nextOnTime.toISOString().split('T')[0];
        deviceSettings[device].offDate = nextOffTime.toISOString().split('T')[0];

        updateDeviceUI(device);
    });

    document.querySelectorAll('.device-onoff').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const device = this.dataset.device;
            controlDevice(device, !deviceSettings[device].status);
        });
    });

    document.querySelectorAll('.timer-toggle').forEach(toggle => {
        toggle.addEventListener('click', function() {
            const device = this.dataset.device;
            const onDateInput = document.getElementById(`${device}-on-date`);
            const onTimeInput = document.getElementById(`${device}-on-time`);
            const offDateInput = document.getElementById(`${device}-off-date`);
            const offTimeInput = document.getElementById(`${device}-off-time`);
            const dailyInput = document.getElementById(`${device}-daily`);

            if (!onDateInput || !onTimeInput || !offDateInput || !offTimeInput || !dailyInput) {
                showTimerError("Không tìm thấy trường ngày/giờ cho thiết bị này!");
                return;
            }

            const onDate = onDateInput.value;
            const onTime = onTimeInput.value;
            const offDate = offDateInput.value;
            const offTime = offTimeInput.value;
            const daily = dailyInput.checked;

            if (!onTime || !offTime) {
                showTimerError("Vui lòng nhập đầy đủ thời gian bật và tắt");
                return;
            }

            if (this.classList.contains('active')) {
                clearTimer(device);
            } else {
                setTimer(device, onDate, onTime, offDate, offTime, daily);
            }
        });
    });

    document.querySelectorAll('.daily-toggle').forEach(function(checkbox) {
        checkbox.addEventListener('change', function() {
            const row = this.closest('tr');
            if (!row) return;
            const dateInputs = row.querySelectorAll('.date-input');
            if (this.checked) {
                const today = new Date().toISOString().split('T')[0];
                dateInputs.forEach(input => {
                    input.value = today;
                    input.disabled = true;
                });
            } else {
                dateInputs.forEach(input => {
                    input.disabled = false;
                });
            }
        });
    });

    devices.forEach(device => {
        initializeTimerInputs(device);
    });
});

setInterval(() => {
    if (!isConnected) {
        console.log('MQTT disconnected, trying to reconnect...');
        initializeMQTT();
    }
}, 5000);

function requestDeviceStatus(device) {
    if (!client || !isConnected) return;
    try {
        const message = new Paho.MQTT.Message(JSON.stringify({
            type: 'request_status',
            timestamp: new Date().toISOString()
        }));
        message.destinationName = `iot/device/status_request/${device}`;
        message.qos = 1;
        client.send(message);
        console.log(`Requested status for device: ${device}`);
    } catch (error) {
        console.error(`Error requesting status for ${device}:`, error);
    }
}

function validateTimerInput(onDate, onTime, offDate, offTime, daily) {
    if (!onTime || !offTime) {
        return { valid: false, message: "Vui lòng nhập đầy đủ thời gian bật và tắt" };
    }

    const now = new Date();
    const onDateTime = new Date(`${onDate}T${onTime}`);
    const offDateTime = new Date(`${offDate}T${offTime}`);

    if (onDateTime < now) {
        return { valid: false, message: "Không thể chọn thời gian bật trong quá khứ" };
    }
    if (offDateTime < now) {
        return { valid: false, message: "Không thể chọn thời gian tắt trong quá khứ" };
    }
    if (offDate < onDate) {
        return { valid: false, message: "Ngày tắt phải bằng hoặc sau ngày bật" };
    }
    if (onDate === offDate && onTime >= offTime) {
        return { valid: false, message: "Nếu cùng ngày, thời gian tắt phải sau thời gian bật" };
    }
    return { valid: true };
}

const deviceNames = {
    'light': 'Đèn',
    'roof': 'Mái che',
    'pump': 'Máy bơm',
    'fan': 'Quạt'
};

function showTimerLoading() {
    document.getElementById('timer-loading').classList.remove('hidden');
    document.getElementById('timer-success').classList.add('hidden');
    document.getElementById('timer-error').classList.add('hidden');
}
function showTimerSuccess(message) {
    document.getElementById('timer-loading').classList.add('hidden');
    document.getElementById('timer-success').classList.remove('hidden');
    document.getElementById('timer-error').classList.add('hidden');
    document.getElementById('timer-success-message').textContent = message;
}
function showTimerError(message) {
    document.getElementById('timer-loading').classList.add('hidden');
    document.getElementById('timer-success').classList.add('hidden');
    document.getElementById('timer-error').classList.remove('hidden');
    document.getElementById('timer-error-message').textContent = message;
}

async function setTimer(device, onDate, onTime, offDate, offTime, daily) {
    showTimerLoading();

    const validation = validateTimerInput(onDate, onTime, offDate, offTime, daily);
    if (!validation.valid) {
        showTimerError(validation.message);
        return;
    }

    try {
        console.log('Setting timer with data:', { device, onDate, onTime, offDate, offTime, daily });

        const response = await fetch('/api/set-timer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device, onDate, onTime, offDate, offTime, daily })
        });

        const data = await response.json();
        console.log('Set timer response:', data);

        if (data.success) {
            const deviceName = deviceNames[device] || device;
            const successMessage = `Đã cài đặt hẹn giờ cho ${deviceName} thành công`;
            const successElement = document.getElementById('timer-success-message');
            if (successElement) {
                successElement.textContent = successMessage;
                document.getElementById('timer-loading').classList.add('hidden');
                document.getElementById('timer-success').classList.remove('hidden');
                document.getElementById('timer-error').classList.add('hidden');
            }
            if (typeof updateNotifications === 'function') {
                const notifyMsg = `Hẹn giờ ${deviceName} BẬT lúc ${onTime} ${onDate}, TẮT lúc ${offTime} ${offDate}`;
                updateNotifications({
                    type: 'timer',
                    device: device,
                    status: true,
                    time: `${onTime} ${onDate}`,
                    message: notifyMsg
                });
            }
            setTimeout(async () => {
                try {
                    const res = await fetch(`/api/get-timer/${device}`);
                    const timerData = await res.json();
                    if (timerData.success && timerData.timer) {
                        updateTimerUI(device, timerData.timer, true);
                    } else {
                        updateTimerUI(device, null, true);
                    }
                } catch (err) {
                    console.error('Error fetching timer after set:', err);
                }
            }, 1000);
        } else {
            const errorMessage = data.message || 'Cài đặt hẹn giờ thất bại';
            const errorElement = document.getElementById('timer-error-message');
            if (errorElement) {
                errorElement.textContent = errorMessage;
                document.getElementById('timer-loading').classList.add('hidden');
                document.getElementById('timer-success').classList.add('hidden');
                document.getElementById('timer-error').classList.remove('hidden');
            }
        }
    } catch (error) {
        console.error('Timer error:', error);
        showTimerError('Lỗi kết nối đến server');
    }
}

async function clearTimer(device) {
    showTimerLoading();
    try {
        console.log(`Clearing timer for ${device}...`);
        const response = await fetch('/api/clear-timer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device })
        });

        const data = await response.json();
        console.log('Clear timer response:', data);

        if (data.success) {
            document.getElementById(`${device}-timer-toggle`).classList.remove('active');
            showTimerSuccess('Đã xóa hẹn giờ thành công');
            updateTimerUI(device, null, true);
        } else {
            showTimerError(data.message || 'Xóa hẹn giờ thất bại');
        }
    } catch (error) {
        console.error('Clear timer error:', error);
        showTimerError('Lỗi kết nối đến server');
    }
}

// document.addEventListener('DOMContentLoaded', async function() {
//     try {
//         console.log('Loading timers from server...');
//         const devices = ['light', 'roof', 'pump', 'fan'];
//         for (const device of devices) {
//             try {
//                 console.log(`Fetching timer for ${device}...`);
//                 const response = await fetch(`/api/get-timer/${device}`);
//                 const data = await response.json();
//                 console.log(`Timer data for ${device}:`, data);

//                 if (data.success && data.timer) {
//                     const now = new Date();
//                     const offDateTime = new Date(data.timer.off_datetime);
//                     const isDaily = data.timer.daily || false;
//                     const isExpired = offDateTime < now;

//                     if (isExpired && !isDaily) {
//                         deviceSettings[device] = {
//                             ...deviceSettings[device],
//                             enabled: false,
//                             onTime: '',
//                             offTime: '',
//                             onDate: '',
//                             offDate: '',
//                             daily: false
//                         };
//                         updateTimerUI(device, null, true);
//                     } else {
//                         deviceSettings[device] = {
//                             ...deviceSettings[device],
//                             enabled: true,
//                             onTime: new Date(data.timer.on_datetime).toTimeString().slice(0, 5),
//                             offTime: new Date(data.timer.off_datetime).toTimeString().slice(0, 5),
//                             onDate: new Date(data.timer.on_datetime).toISOString().split('T')[0],
//                             offDate: new Date(data.timer.off_datetime).toISOString().split('T')[0],
//                             daily: isDaily
//                         };
//                         updateTimerUI(device, data.timer, true);
//                     }
//                 } else {
//                     console.log(`No active timer found for ${device}`);
//                     deviceSettings[device] = {
//                         ...deviceSettings[device],
//                         enabled: false,
//                         onTime: '',
//                         offTime: '',
//                         onDate: '',
//                         offDate: '',
//                         daily: false
//                     };
//                     updateTimerUI(device, null, true);
//                 }
//             } catch (error) {
//                 console.error(`Error loading timer for ${device}:`, error);
//                 deviceSettings[device] = {
//                     ...deviceSettings[device],
//                     enabled: false,
//                     onTime: '',
//                     offTime: '',
//                     onDate: '',
//                     offDate: '',
//                     daily: false
//                 };
//                 updateTimerUI(device, null, true);
//             }
//         }
//     } catch (error) {
//         console.error('Error loading timers:', error);
//     }
// });