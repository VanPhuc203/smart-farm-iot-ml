// crop-prediction.js
// Xử lý form khuyến nghị
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('prediction-form');
    const resultDiv = document.getElementById('result');
    const predictionText = document.getElementById('prediction-text');
    const errorDiv = document.getElementById('error');
    const errorText = document.getElementById('error-text');
    const quickFillBtn = document.getElementById('quick-fill-btn');
    const plantImage = document.querySelector('.plant-image');
    const loadingSpinner = document.querySelector('.loading-spinner');

    const plantImages = {
        'rice': '../static/img/plants/rice.webp',
        'maize': '../static/img/plants/maize.jpg',
        'chickpea': '../static/img/plants/chickpea.jpg',
        'kidneybeans': '../static/img/plants/kidneybeans.webp',
        'pigeonpeas': '../static/img/plants/pigeonpeas.jpg',
        'mothbeans': '../static/img/plants/mothbeans.webp',
        'mungbean': '../static/img/plants/mungbean.jpg',
        'blackgram': '../static/img/plants/blackgram.webp',
        'lentil': '../static/img/plants/lentil.jpg',
        'pomegranate': '../static/img/plants/pomegranate.jpeg',
        'banana': '../static/img/plants/banana.jpg',
        'mango': '../static/img/plants/mango.jpg',
        'grapes': '../static/img/plants/grapes.jpeg',
        'watermelon': '../static/img/plants/watermelon.jpeg',
        'muskmelon': '../static/img/plants/muskmelon.jpg',
        'apple': '../static/img/plants/apple.jpeg',
        'orange': '../static/img/plants/orange.jpg',
        'papaya': '../static/img/plants/papaya.jpg',
        'coconut': '../static/img/plants/coconut.jpeg',
        'cotton': '../static/img/plants/cotton.jpg',
        'jute': '../static/img/plants/jute.jpg',
        'coffee': '../static/img/plants/coffee.jpeg'
    };

    const plantIdealParameters = {
        'rice': {
            'temperature': {'min': 20, 'max': 27},
            'humidity': {'min': 80, 'max': 85},
            'nitrogen': {'min': 60, 'max': 99},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 35, 'max': 45},
            'ph': {'min': 5.0, 'max': 7.8}
        },
        'maize': {
            'temperature': {'min': 18, 'max': 26},
            'humidity': {'min': 55, 'max': 74},
            'nitrogen': {'min': 60, 'max': 100},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 5.5, 'max': 7.0}
        },
        'chickpea': {
            'temperature': {'min': 17, 'max': 21},
            'humidity': {'min': 14, 'max': 20},
            'nitrogen': {'min': 20, 'max': 60},
            'phosphorus': {'min': 55, 'max': 80},
            'potassium': {'min': 75, 'max': 85},
            'ph': {'min': 6.0, 'max': 8.9}
        },
        'kidneybeans': {
            'temperature': {'min': 15, 'max': 24},
            'humidity': {'min': 18, 'max': 25},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 55, 'max': 80},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 5.5, 'max': 6.0}
        },
        'pigeonpeas': {
            'temperature': {'min': 18, 'max': 39},
            'humidity': {'min': 14, 'max': 35},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 55, 'max': 80},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 4.0, 'max': 8.8}
        },
        'mothbeans': {
            'temperature': {'min': 24, 'max': 32},
            'humidity': {'min': 25, 'max': 35},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 3.5, 'max': 9.0}
        },
        'mungbean': {
            'temperature': {'min': 27, 'max': 30},
            'humidity': {'min': 80, 'max': 90},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 6.2, 'max': 7.6}
        },
        'blackgram': {
            'temperature': {'min': 26, 'max': 32},
            'humidity': {'min': 60, 'max': 70},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 55, 'max': 80},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 4.9, 'max': 7.6}
        },
        'lentil': {
            'temperature': {'min': 18, 'max': 27},
            'humidity': {'min': 60, 'max': 70},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 55, 'max': 80},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 5.8, 'max': 7.8}
        },
        'pomegranate': {
            'temperature': {'min': 18, 'max': 24},
            'humidity': {'min': 85, 'max': 95},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 35, 'max': 45},
            'ph': {'min': 5.4, 'max': 7.8}
        },
        'banana': {
            'temperature': {'min': 25, 'max': 30},
            'humidity': {'min': 75, 'max': 85},
            'nitrogen': {'min': 80, 'max': 120},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 45, 'max': 55},
            'ph': {'min': 5.0, 'max': 7.0}
        },
        'mango': {
            'temperature': {'min': 27, 'max': 35},
            'humidity': {'min': 45, 'max': 55},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 15, 'max': 40},
            'potassium': {'min': 25, 'max': 35},
            'ph': {'min': 4.3, 'max': 7.6}
        },
        'grapes': {
            'temperature': {'min': 8, 'max': 32},
            'humidity': {'min': 80, 'max': 85},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 120, 'max': 145},
            'potassium': {'min': 195, 'max': 205},
            'ph': {'min': 5.5, 'max': 7.0}
        },
        'watermelon': {
            'temperature': {'min': 24, 'max': 27},
            'humidity': {'min': 80, 'max': 90},
            'nitrogen': {'min': 80, 'max': 120},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 5, 'max': 15},
            'ph': {'min': 6.0, 'max': 6.8}
        },
        'muskmelon': {
            'temperature': {'min': 27, 'max': 29},
            'humidity': {'min': 90, 'max': 95},
            'nitrogen': {'min': 80, 'max': 120},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 5, 'max': 15},
            'ph': {'min': 6.0, 'max': 6.8}
        },
        'apple': {
            'temperature': {'min': 21, 'max': 24},
            'humidity': {'min': 85, 'max': 95},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 120, 'max': 145},
            'potassium': {'min': 195, 'max': 205},
            'ph': {'min': 5.5, 'max': 7.0}
        },
        'orange': {
            'temperature': {'min': 10, 'max': 34},
            'humidity': {'min': 85, 'max': 95},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 5, 'max': 15},
            'ph': {'min': 4.0, 'max': 9.0}
        },
        'papaya': {
            'temperature': {'min': 23, 'max': 44},
            'humidity': {'min': 85, 'max': 95},
            'nitrogen': {'min': 40, 'max': 80},
            'phosphorus': {'min': 5, 'max': 60},
            'potassium': {'min': 45, 'max': 55},
            'ph': {'min': 4.3, 'max': 7.6}
        },
        'coconut': {
            'temperature': {'min': 25, 'max': 30},
            'humidity': {'min': 90, 'max': 100},
            'nitrogen': {'min': 0, 'max': 40},
            'phosphorus': {'min': 5, 'max': 30},
            'potassium': {'min': 25, 'max': 35},
            'ph': {'min': 5.5, 'max': 6.5}
        },
        'cotton': {
            'temperature': {'min': 22, 'max': 26},
            'humidity': {'min': 75, 'max': 85},
            'nitrogen': {'min': 100, 'max': 140},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 15, 'max': 25},
            'ph': {'min': 5.8, 'max': 8.0}
        },
        'jute': {
            'temperature': {'min': 23, 'max': 27},
            'humidity': {'min': 70, 'max': 90},
            'nitrogen': {'min': 60, 'max': 100},
            'phosphorus': {'min': 35, 'max': 60},
            'potassium': {'min': 35, 'max': 45},
            'ph': {'min': 6.0, 'max': 7.5}
        },
        'coffee': {
            'temperature': {'min': 23, 'max': 28},
            'humidity': {'min': 50, 'max': 70},
            'nitrogen': {'min': 80, 'max': 120},
            'phosphorus': {'min': 15, 'max': 40},
            'potassium': {'min': 25, 'max': 35},
            'ph': {'min': 6.0, 'max': 7.5}
        }
    };

    function getBaseUrl() {
        return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
            ? 'http://localhost:8000'
            : `${window.location.protocol}//${window.location.host}`;
    }

    function updatePlantImage(selectedPlant) {
        if (!plantImage || !loadingSpinner) {
            console.warn('Không tìm thấy các element cần thiết');
            return;
        }

        const plantNameEn = getEnglishPlantName(selectedPlant);
        console.log('Plant name EN:', plantNameEn); 
        const imagePath = plantImages[plantNameEn] || '../static/img/plants/default-plant.jpg';
        console.log('Image path:', imagePath); 

        plantImage.classList.add('loading');
        loadingSpinner.classList.add('active');

        const img = new Image();
        
        img.onload = function() {
            plantImage.src = imagePath;
            plantImage.alt = `Hình ảnh ${selectedPlant}`;

            setTimeout(() => {
                plantImage.classList.remove('loading');
                loadingSpinner.classList.remove('active');
            }, 300);
        };

        img.onerror = function() {
            console.warn(`Không thể tải ảnh cho ${selectedPlant}, sử dụng ảnh mặc định`);
            plantImage.src = '../static/img/plants/default-plant.jpg';
            plantImage.alt = 'Hình ảnh mặc định';            
            // Ẩn loading
            plantImage.classList.remove('loading');
            loadingSpinner.classList.remove('active');
        };

        img.src = imagePath;
    }

    function getEnglishPlantName(vietnameseName) {
        const match = vietnameseName.match(/: (.+)$/);
        if (!match) return 'default-plant';
        
        const plantNameVi = match[1].trim();
        console.log('Tên cây tiếng Việt:', plantNameVi); 

        const plantTranslations = {
            'Lúa': 'rice',
            'Ngô': 'maize',
            'Đậu gà': 'chickpea',
            'Đậu thận': 'kidneybeans',
            'Đậu săng': 'pigeonpeas',
            'Đậу bướm': 'mothbeans',
            'Đậу xanh': 'mungbean',
            'Đậу đen': 'blackgram',
            'Đậу lăng': 'lentil',
            'Lựu': 'pomegranate',
            'Chuối': 'banana',
            'Xoài': 'mango',
            'Nho': 'grapes',
            'Dưa hấu': 'watermelon',
            'Dưa lưới': 'muskmelon',
            'Táo': 'apple',
            'Cam': 'orange',
            'Đu đủ': 'papaya',
            'Dừa': 'coconut',
            'Bông': 'cotton',
            'Đay': 'jute',
            'Cà phê': 'coffee'
        };
        
        const englishName = plantTranslations[plantNameVi];
        console.log('Tên cây tiếng Anh:', englishName); 
        return englishName || 'default-plant';
    }

    quickFillBtn.addEventListener('click', async function() {
        try {
            const response = await fetch(`${getBaseUrl()}/quick-fill`);
            const data = await response.json();
            
            if (response.ok) {
                document.getElementById('temperature').value = Number(data.temperature).toFixed(2);
                document.getElementById('humidity').value = Number(data.humidity).toFixed(2);
                document.getElementById('total_rainfall').value = Number(data.monthly_rainfall).toFixed(2); // Đổi tên trường rainfall thành total_rainfall
                document.getElementById('N').value = Number(data.nitrogen).toFixed(2);
                document.getElementById('P').value = Number(data.phosphorus).toFixed(2);
                document.getElementById('K').value = Number(data.potassium).toFixed(2);
                document.getElementById('ph').value = Number(data.ph).toFixed(2);
                
                console.log('Quick fill data:', {
                    temperature: Number(data.temperature).toFixed(2),
                    humidity: Number(data.humidity).toFixed(2),
                    total_rainfall: Number(data.monthly_rainfall).toFixed(2), 
                    nitrogen: Number(data.nitrogen).toFixed(2),
                    phosphorus: Number(data.phosphorus).toFixed(2),
                    potassium: Number(data.potassium).toFixed(2),
                    ph: Number(data.ph).toFixed(2)
                });
            } else {
                errorText.textContent = data.error || 'Không thể lấy dữ liệu mới nhất';
                errorDiv.classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error in quick fill:', error);
            errorText.textContent = 'Không thể kết nối đến server';
            errorDiv.classList.remove('hidden');
        }
    });

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        resultDiv.classList.add('hidden');
        errorDiv.classList.add('hidden');

        const formData = new FormData(form);
        const data = {
            N: Number(parseFloat(formData.get('N')).toFixed(2)),
            P: Number(parseFloat(formData.get('P')).toFixed(2)),
            K: Number(parseFloat(formData.get('K')).toFixed(2)),
            temperature: Number(parseFloat(formData.get('temperature')).toFixed(2)),
            humidity: Number(parseFloat(formData.get('humidity')).toFixed(2)),
            ph: Number(parseFloat(formData.get('ph')).toFixed(2)),
            rainfall: Number(parseFloat(formData.get('total_rainfall')).toFixed(2))
        };

        try {
            const response = await fetch(`${getBaseUrl()}/predict`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok) {
                const plantNameEn = getEnglishPlantName(result.prediction_text);
                console.log('Plant name EN:', plantNameEn); 
                
                const idealParams = plantIdealParameters[plantNameEn];
                console.log('Ideal parameters:', idealParams); 

                let resultMessage = `<p class="text-lg font-bold mb-4">${result.prediction_text}</p>`;

                resultMessage += '<div class="overflow-x-auto mt-4">';
                resultMessage += '<table class="min-w-full bg-white border border-gray-300">';
                resultMessage += `
                    <thead>
                        <tr class="bg-gray-100">
                            <th class="px-4 py-2 border">Thông số</th>
                            <th class="px-4 py-2 border">Giá trị hiện tại</th>
                            <th class="px-4 py-2 border">Giá trị lý tưởng</th>
                            <th class="px-4 py-2 border">Trạng thái</th>
                        </tr>
                    </thead>
                    <tbody>
                `;

                const paramMapping = {
                    'temperature': { 
                        label: 'Nhiệt độ',
                        unit: '°C',
                        current: data.temperature,
                        ideal: idealParams?.temperature
                    },
                    'humidity': { 
                        label: 'Độ ẩm',
                        unit: '%',
                        current: data.humidity,
                        ideal: idealParams?.humidity
                    },
                    'nitrogen': { 
                        label: 'Nitrogen',
                        unit: 'mg/kg',
                        current: data.N,
                        ideal: idealParams?.nitrogen
                    },
                    'phosphorus': { 
                        label: 'Phosphorus',
                        unit: 'mg/kg',
                        current: data.P,
                        ideal: idealParams?.phosphorus
                    },
                    'potassium': { 
                        label: 'Potassium',
                        unit: 'mg/kg',
                        current: data.K,
                        ideal: idealParams?.potassium
                    },
                    'ph': { 
                        label: 'pH',
                        unit: '',
                        current: data.ph,
                        ideal: idealParams?.ph
                    }
                };

                for (const [key, param] of Object.entries(paramMapping)) {
                    let status = '';
                    let statusClass = '';
                    let idealRange = 'N/A';

                    if (param.ideal) {
                        idealRange = `${param.ideal.min} - ${param.ideal.max}`;
                        
                        if (param.current < param.ideal.min) {
                            status = '⬆️ Thấp';
                            statusClass = 'text-yellow-600';
                        } else if (param.current > param.ideal.max) {
                            status = '⬇️ Cao';
                            statusClass = 'text-red-600';
                        } else {
                            status = '✅ Tốt';
                            statusClass = 'text-green-600';
                        }
                    }

                    resultMessage += `
                        <tr>
                            <td class="px-4 py-2 border">${param.label} ${param.unit}</td>
                            <td class="px-4 py-2 border">${param.current}</td>
                            <td class="px-4 py-2 border">${idealRange}</td>
                            <td class="px-4 py-2 border ${statusClass}">${status}</td>
                        </tr>
                    `;
                }

                resultMessage += '</tbody></table></div>';

                if (result.warnings && result.warnings.length > 0) {
                    resultMessage += '<div class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 mb-4 mt-4">';
                    resultMessage += '<p class="font-bold mb-2">⚠️ Cảnh báo:</p>';
                    resultMessage += '<ul class="list-disc list-inside">';
                    result.warnings.forEach(warning => {
                        resultMessage += `<li>${warning}</li>`;
                    });
                    resultMessage += '</ul></div>';
                }

                if (result.suggestions && result.suggestions.length > 0) {
                    resultMessage += '<div class="bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 mb-4">';
                    resultMessage += '<p class="font-bold mb-2">💡 Đề xuất:</p>';
                    resultMessage += '<ul class="list-disc list-inside">';
                    result.suggestions.forEach(suggestion => {
                        resultMessage += `<li>${suggestion}</li>`;
                    });
                    resultMessage += '</ul></div>';
                }

                predictionText.innerHTML = resultMessage;
                resultDiv.classList.remove('hidden');
                errorDiv.classList.add('hidden');

                updatePlantImage(result.prediction_text);
            } else {
                errorText.textContent = result.error || 'Có lỗi xảy ra khi khuyến nghị cây trồng';
                errorDiv.classList.remove('hidden');
                resultDiv.classList.add('hidden');
            }
        } catch (error) {
            console.error('Error:', error);
            errorText.textContent = 'Không thể kết nối đến server. Vui lòng thử lại sau.';
            errorDiv.classList.remove('hidden');
            resultDiv.classList.add('hidden');
        }
    });
});

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString('vi-VN');
    document.getElementById('current-time').textContent = timeString;
}

setInterval(updateCurrentTime, 1000);
updateCurrentTime();